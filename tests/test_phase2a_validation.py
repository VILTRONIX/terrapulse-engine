"""Regression checks for meaningful Phase 2A data-contract failure modes.

Temporary CSVs and isolated package copies are used; original sources are read only.
"""

import contextlib
import csv
import io
import json
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from src.features.build_mvp import build
from src.features.phase2a_contracts import DATASETS, FEATURE_DIR, INVENTORY_PATH
from src.validation.validate_mvp import (
    ROOT, check_denominators, cross_dataset_checks, decode_cell, protected_paths,
    read_records, sha256, validate_package, validate_table,
)

SPECS = {spec["dataset_name"]: spec for spec in DATASETS}


class TableValidationTests(unittest.TestCase):
    def validate_mutation(self, name, mutate):
        spec = SPECS[name]
        with (ROOT / spec["source_path"]).open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            fields = reader.fieldnames
        mutate(rows, fields)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutated.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            return validate_table(path, spec)

    def test_rejects_missing_required_column(self):
        with self.assertRaisesRegex(ValueError, "Required ordered columns differ"):
            self.validate_mutation("crop_annual_features", lambda rows, fields: fields.remove("source"))

    def test_rejects_duplicate_natural_key(self):
        def mutate(rows, fields):
            rows[1]["crop_code"] = rows[0]["crop_code"]
        with self.assertRaisesRegex(ValueError, "Duplicate natural key"):
            self.validate_mutation("crop_annual_features", mutate)

    def test_rejects_invalid_and_nonfinite_numeric_cells(self):
        for value in ("NaN", "nan", "inf", "-Infinity", "1e999", "12 mm", "1_000"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode_cell(value, {"type": "number"})
        for value in ("1.0", "True", "1e2"):
            with self.subTest(integer=value), self.assertRaises(ValueError):
                decode_cell(value, {"type": "integer"})

    def test_rejects_non_nullable_null_and_invalid_calendar_date(self):
        with self.assertRaisesRegex(ValueError, "non-nullable"):
            decode_cell("NULL", {"type": "number"})
        with self.assertRaises(ValueError):
            decode_cell("2025-02-29", SPECS["modis_16day_features"]["columns"]["date"])
        with self.assertRaises(ValueError):
            decode_cell("true", {"type": "boolean"})

    def test_rejects_missing_date_coverage_without_duplicate(self):
        with self.assertRaisesRegex(ValueError, "16-day date coverage differs"):
            self.validate_mutation("modis_16day_features", lambda rows, fields: rows[0].update(date="2017-01-02"))

    def test_rejects_fixed_annual_denominator(self):
        def mutate(rows, fields):
            for row in rows:
                row["valid_denominator_ha"] = "148572.90"
        with self.assertRaisesRegex(ValueError, "denominator_ha for 2024"):
            self.validate_mutation("crop_annual_features", mutate)

    def test_rejects_fixed_transition_denominator(self):
        def mutate(rows, fields):
            for row in rows:
                row["common_valid_area_ha"] = "148572.90"
        with self.assertRaisesRegex(ValueError, "common_valid_area_ha for \\(2023, 2024\\)"):
            self.validate_mutation("crop_transition_features", mutate)

    def test_percentage_tolerance_is_absolute_and_at_approved_boundary(self):
        spec = SPECS["crop_annual_features"]
        rows = read_records(ROOT / spec["source_path"], spec)
        exact = Decimal(str(rows[0]["area_ha"])) / Decimal(str(rows[0]["valid_denominator_ha"])) * 100
        rows[0]["area_pct"] = float(exact + Decimal("0.000050000"))
        check_denominators(spec["dataset_name"], rows)
        rows[0]["area_pct"] = float(exact + Decimal("0.000050002"))
        with self.assertRaisesRegex(ValueError, "Percentage error exceeds"):
            check_denominators(spec["dataset_name"], rows)

    def test_rejects_soil_water_storage_imputation(self):
        with self.assertRaisesRegex(ValueError, "Missing-value counts differ"):
            self.validate_mutation("soil_mapunit_features", lambda rows, fields: rows[0].update(root_zone_aws_0_150cm_mm="100"))
        prop = SPECS["soil_mapunit_features"]["columns"]["mukey"]
        self.assertEqual(decode_cell("001234", prop), "001234")

    def test_rejects_modis_unweighted_monthly_mean(self):
        monthly = read_records(ROOT / SPECS["modis_monthly_features"]["source_path"], SPECS["modis_monthly_features"])
        composites = read_records(ROOT / SPECS["modis_16day_features"]["source_path"], SPECS["modis_16day_features"])
        first = [r["ndvi_mean"] for r in composites if r["date"][:7] == monthly[0]["month"]]
        monthly[0]["ndvi_mean"] = sum(first) / len(first)
        with self.assertRaisesRegex(ValueError, "not valid-pixel weighted"):
            cross_dataset_checks({"modis_monthly_features": monthly, "modis_16day_features": composites})


def copy_inputs(destination, omit=()):
    for source in protected_paths(ROOT):
        relative = source.relative_to(ROOT)
        if relative.as_posix() in omit:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def quiet_build(root):
    with contextlib.redirect_stdout(io.StringIO()):
        return build(root)


class PackageValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name)
        copy_inputs(cls.root)
        if quiet_build(cls.root):
            raise AssertionError("Isolated baseline package did not build")

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_build_is_deterministic(self):
        paths = [p for directory in (FEATURE_DIR, "src/schemas", "reports", "docs")
                 for p in (self.root / directory).rglob("*") if p.is_file()]
        before = {p: sha256(p) for p in paths}
        self.assertEqual(quiet_build(self.root), 0)
        self.assertEqual({p: sha256(p) for p in paths}, before)
        self.assertEqual(validate_package(self.root)["status"], "PASS")

    def test_rejects_source_to_output_value_tampering(self):
        path = self.root / SPECS["crop_annual_features"]["path"]
        original = path.read_bytes()
        try:
            path.write_bytes(original.replace(b"57873.6", b"57873.7", 1))
            result = validate_package(self.root)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("Output hash differs" in e for e in result["errors"]))
        finally:
            path.write_bytes(original)

    def test_rejects_schema_and_manifest_drift(self):
        spec = SPECS["soil_mapunit_features"]
        schema_path = self.root / spec["schema_path"]
        original = schema_path.read_bytes()
        try:
            schema = json.loads(original)
            schema["properties"]["mukey"]["type"] = "integer"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            result = validate_package(self.root)
            self.assertTrue(any("JSON schema differs" in e for e in result["errors"]))
        finally:
            schema_path.write_bytes(original)
        manifest_path = self.root / FEATURE_DIR / "feature_manifest.json"
        original = manifest_path.read_bytes()
        try:
            manifest = json.loads(original)
            manifest["datasets"][0]["path"] = "missing.csv"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = validate_package(self.root)
            self.assertTrue(any("Manifest path differs" in e for e in result["errors"]))
        finally:
            manifest_path.write_bytes(original)

    def test_rejects_changed_protected_source_even_if_not_consumed(self):
        path = self.root / "data/processed/merra2/merra2_annual_summary.csv"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n")
            result = validate_package(self.root)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("Protected source changed" in e for e in result["errors"]))
        finally:
            path.write_bytes(original)

    def test_missing_required_input_continues_and_removes_stale_output(self):
        spec = SPECS["soil_mapunit_features"]
        source = self.root / spec["source_path"]
        original = source.read_bytes()
        try:
            source.unlink()
            self.assertEqual(quiet_build(self.root), 1)
            manifest = json.loads((self.root / FEATURE_DIR / "feature_manifest.json").read_text())
            self.assertEqual(len(manifest["datasets"]), 7)
            self.assertEqual(manifest["unavailable_datasets"][0]["dataset_name"], spec["dataset_name"])
            self.assertFalse((self.root / spec["path"]).exists())
            self.assertFalse((self.root / spec["schema_path"]).exists())
            self.assertTrue((self.root / SPECS["crop_annual_features"]["path"]).is_file())
        finally:
            source.write_bytes(original)
            self.assertEqual(quiet_build(self.root), 0)

    def test_optional_missing_before_first_build_keeps_required_package_ready(self):
        optional = SPECS["merra2_monthly_context_features"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_inputs(root, omit=[optional["source_path"]])
            self.assertFalse((root / INVENTORY_PATH).exists())
            self.assertEqual(quiet_build(root), 0)
            result = validate_package(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(sum(item["status"] == "PASS" for item in result["datasets"]), 7)
            self.assertEqual(sum(item["status"] == "OMITTED" for item in result["datasets"]), 1)
            manifest = json.loads((root / FEATURE_DIR / "feature_manifest.json").read_text())
            self.assertTrue(all((root / entry["path"]).is_file() for entry in manifest["datasets"]))


if __name__ == "__main__":
    unittest.main()
