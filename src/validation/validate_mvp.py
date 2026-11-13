"""Validate the complete Phase 2A package with the Python standard library.

Run from the repository root: .venv/bin/python -B -m src.validation.validate_mvp
Exit status is nonzero for any unresolved package failure. No inputs are written.
"""

import argparse
import calendar
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from src.features.phase2a_contracts import (
    ANNUAL_DENOMINATORS, DATASETS, FEATURE_DIR, INVENTORY_PATH, POWER_POINTS,
    PCT_TOLERANCE, TRANSITION_DENOMINATORS, row_schema,
)

ROOT = Path(__file__).resolve().parents[2]
INTEGER = re.compile(r"-?(?:0|[1-9]\d*)\Z")
NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text(path, content):
    """Avoid rewriting unchanged artifacts; replace completed files atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_json(path, value):
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def local_path(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute(), "Expected a relative repository path")
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), f"Path escapes repository: {relative}")
    return path


def protected_paths(root):
    paths = [p for p in (root / "data").rglob("*") if p.is_file()
             and not p.is_relative_to(root / FEATURE_DIR)]
    paths.extend(root / p for p in [
        "requirements-phase2.txt", "requirements-phase2-lock.txt", ".gitignore",
        "docs/phase2_environment_audit.md", "docs/phase2_environment_setup.md"])
    return sorted(paths)


def verify_inventory(root):
    inventory = json.loads((root / INVENTORY_PATH).read_text(encoding="utf-8"))
    errors = []
    seen = set()
    for item in inventory["files"]:
        relative = item["path"]
        require(relative not in seen, f"Duplicate inventory path: {relative}")
        seen.add(relative)
        path = local_path(root, relative)
        if not path.is_file():
            errors.append(f"Protected source missing: {relative}")
        elif path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            errors.append(f"Protected source changed: {relative}")
    actual = {p.relative_to(root).as_posix() for p in protected_paths(root) if p.is_file()}
    errors.extend(f"Unregistered source file: {p}" for p in sorted(actual - seen))
    return inventory, errors


def decode_cell(value, prop):
    types = prop["type"] if isinstance(prop["type"], list) else [prop["type"]]
    if value in ("", "NULL"):
        require("null" in types, "Null in a non-nullable field")
        return None
    kind = next(t for t in types if t != "null")
    if kind == "integer":
        require(INTEGER.fullmatch(value), f"Invalid integer: {value!r}")
        result = int(value)
    elif kind == "number":
        require(NUMBER.fullmatch(value), f"Invalid number: {value!r}")
        result = float(value)
        require(math.isfinite(result), f"Non-finite number: {value!r}")
    elif kind == "boolean":
        require(value in ("True", "False"), f"Invalid boolean: {value!r}")
        result = value == "True"
    elif kind == "string":
        result = value
        if "pattern" in prop:
            require(re.fullmatch(prop["pattern"], value), f"String does not match {prop['pattern']}: {value!r}")
        if prop.get("format") == "date":
            date.fromisoformat(value)
        require(len(value) >= prop.get("minLength", 0), "String too short")
    else:
        raise ValueError(f"Unsupported contract type: {kind}")
    if "enum" in prop:
        require(result in prop["enum"], f"Unexpected category/value: {value!r}")
    if "const" in prop:
        require(result == prop["const"], f"Expected {prop['const']}, got {value!r}")
    for bound, compare in (("minimum", lambda a, b: a >= b), ("maximum", lambda a, b: a <= b),
                           ("exclusiveMinimum", lambda a, b: a > b)):
        if bound in prop:
            require(compare(result, prop[bound]), f"{value!r} violates {bound}={prop[bound]}")
    return result


def read_records(path, spec):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        require(reader.fieldnames == list(spec["columns"]),
                f"Required ordered columns differ: expected {list(spec['columns'])}, got {reader.fieldnames}")
        raw = list(reader)
    records = []
    for index, row in enumerate(raw, start=2):
        require(None not in row and all(value is not None for value in row.values()),
                f"Malformed CSV field count at row {index}")
        parsed = {}
        for field, prop in spec["columns"].items():
            try:
                parsed[field] = decode_cell(row[field], prop)
            except (ValueError, TypeError, OverflowError) as error:
                raise ValueError(f"Row {index}, {field}: {error}") from error
        records.append(parsed)
    return records


def months(start, end):
    first_year, first_month = map(int, start.split("-"))
    last_year, last_month = map(int, end.split("-"))
    return [f"{value // 12:04d}-{value % 12 + 1:02d}"
            for value in range(first_year * 12 + first_month - 1, last_year * 12 + last_month)]


def close(left, right, tolerance=1e-8):
    return math.isclose(left, right, rel_tol=0, abs_tol=tolerance)


def check_denominators(name, records):
    transition = name == "crop_transition_features"
    denominator = "common_valid_area_ha" if transition else "valid_denominator_ha"
    expected = TRANSITION_DENOMINATORS if transition else ANNUAL_DENOMINATORS
    groups = defaultdict(list)
    for row in records:
        key = (row["year_1"], row["year_2"]) if transition else row["year"]
        groups[key].append(row)
    require(set(groups) == set(expected), "Missing or unexpected crop years/year pairs")
    metrics = []
    for key, rows in sorted(groups.items()):
        target = Decimal(expected[key])
        require(all(Decimal(str(r[denominator])) == target for r in rows),
                f"Incorrect or inconsistent {denominator} for {key}")
        area = sum((Decimal(str(r["area_ha"])) for r in rows), Decimal(0))
        require(abs(area - target) <= Decimal("0.000001"), f"Areas do not sum to denominator for {key}")
        errors = [abs(Decimal(str(r["area_pct"])) - Decimal(str(r["area_ha"])) / target * 100) for r in rows]
        require(max(errors) <= Decimal(PCT_TOLERANCE),
                f"Percentage error exceeds {PCT_TOLERANCE} percentage points for {key}: {max(errors)}")
        metrics.append({"period": str(key), "denominator_ha": str(target), "area_sum_ha": str(area),
                        "area_pct_sum": sum(r["area_pct"] for r in rows),
                        "maximum_percentage_error_points": str(max(errors))})
    return metrics


def check_domain(spec, records):
    name = spec["dataset_name"]
    coverage = spec["validation"]["coverage"]
    metrics = {}
    if name == "nasa_power_monthly_features":
        expected = {(point, month) for point in POWER_POINTS for month in months(coverage["start"], coverage["end"])}
        require({(r["location_id"], r["month_start"][:7]) for r in records} == expected,
                "NASA POWER point/month coverage differs")
        for r in records:
            start = date(r["year"], r["month"], 1)
            days = calendar.monthrange(r["year"], r["month"])[1]
            require(r["month_start"] == start.isoformat() and r["month_end"] == date(r["year"], r["month"], days).isoformat(),
                    "NASA POWER dates do not match year/month")
            require(r["days_expected"] == days and r["days_present"] == days and r["complete"], "Incomplete NASA POWER month")
            lat, lon = POWER_POINTS[r["location_id"]]
            require(close(r["latitude"], lat) and close(r["longitude"], lon), "NASA POWER coordinate mismatch")
            require(r["T2M_MIN_mean"] <= r["T2M_mean"] <= r["T2M_MAX_mean"], "Temperature ordering is invalid")
            require(all(r[f] != -999 for f in spec["columns"] if isinstance(r[f], (float, int))), "NASA POWER -999 sentinel")
            for parameter in ("PRECTOTCORR", "ALLSKY_SFC_SW_DWN"):
                require(close(r[f"{parameter}_total"], r[f"{parameter}_daily_mean"] * days), "Monthly total/daily-mean mismatch")
        metrics["months_per_point"] = 108
    elif name.startswith("modis_"):
        monthly = name == "modis_monthly_features"
        if monthly:
            require({r["month"] for r in records} == set(months(coverage["start"], coverage["end"])), "Missing MODIS month")
            require(Counter(r["observation_count"] for r in records) == {1: 9, 2: 99}, "MODIS monthly observation counts differ")
        else:
            expected = {(date(year, 1, 1) + timedelta(days=16 * i)).isoformat() for year in range(2017, 2026) for i in range(23)}
            require({r["date"] for r in records} == expected, "MODIS 16-day date coverage differs")
        for r in records:
            total = r["total_pixel_observations"] if monthly else r["total_pixel_count"]
            if monthly:
                require(total == 37193 * r["observation_count"], "MODIS monthly pixel denominator differs")
            else:
                require(r["quality_valid_pixel_count"] <= r["base_valid_pixel_count"] <= total, "MODIS quality/base count ordering differs")
                for suffix, field in (("before_filter", "base_valid_pixel_count"), ("after_filter", "quality_valid_pixel_count")):
                    distribution = json.loads(r[f"vi_usefulness_distribution_{suffix}"])
                    require(isinstance(distribution, dict), "VI usefulness distribution must be an object")
                    require(all(k.isdigit() and 0 <= int(k) <= 15 and type(v) is int and v >= 0 for k, v in distribution.items()),
                            "Invalid VI usefulness code/count")
                    require(sum(distribution.values()) == r[field], "VI usefulness counts disagree with quality/base counts")
            for vi in ("ndvi", "evi"):
                count = r[f"{vi}_valid_pixel_count"]
                require(count <= total, "MODIS valid count exceeds denominator")
                require(close(r[f"{vi}_valid_pixel_percentage"], 100 * count / total), "MODIS valid percentage differs")
                if not monthly:
                    require(count == r["quality_valid_pixel_count"], "MODIS index/quality valid count differs")
                require(all((r[f"{vi}_{stat}"] is None) == (count == 0) for stat in ("mean", "median", "std")),
                        "MODIS null statistics do not match zero valid count")
        zero = [r["month" if monthly else "date"] for r in records if r["ndvi_valid_pixel_count"] == 0]
        if monthly:
            require(set(zero) == {"2019-02", "2021-01"}, "MODIS zero-quality months differ")
        metrics["zero_quality_periods"] = zero
    elif name.startswith("crop_"):
        metrics["denominator_checks"] = check_denominators(name, records)
        if name == "crop_annual_features":
            require({(r["year"], r["crop_code"]) for r in records} == {(y, c) for y in range(2021, 2026) for c in (1, 5, 999)},
                    "Grouped annual crop keys differ")
            require(all(r["crop_name"] == {1: "Corn", 5: "Soybeans", 999: "Other"}[r["crop_code"]] for r in records), "Grouped crop labels differ")
        elif name == "crop_class_annual_features":
            require(all(r["crop_code"] not in (0, 255, 999) for r in records), "Detailed class contains excluded/background/grouped code")
            require(all(close(r["area_ha"], r["pixel_count"] * 0.09) for r in records), "CDL class area != pixel_count × 0.09 ha")
        else:
            labels = [f"{a} -> {b}" for a in ("Corn", "Soybeans", "Other") for b in ("Corn", "Soybeans", "Other")]
            require({(r["year_1"], r["year_2"], r["transition_type"]) for r in records} ==
                    {(a, b, label) for a, b in TRANSITION_DENOMINATORS for label in labels}, "Transition pairs/types differ")
            require(all(r["year_2"] == r["year_1"] + 1 for r in records), "Transition years are not consecutive")
    elif name == "soil_mapunit_features":
        require(all(r["root_zone_aws_0_150cm_mm"] is None for r in records), "Root-zone AWS must remain unavailable; no imputation")
        require(all(isinstance(r["mukey"], str) for r in records), "mukey must remain a string identifier")
    elif name == "merra2_monthly_context_features":
        expected = {(month + "-01", 42.0, lon) for month in months(coverage["start"], coverage["end"]) for lon in (-93.75, -93.125)}
        require({(r["date"], r["latitude"], r["longitude"]) for r in records} == expected, "MERRA-2 monthly cell coverage differs")
        metrics["months_per_cell"] = 211
    return metrics


def validate_table(path, spec):
    records = read_records(path, spec)
    require(len(records) == spec["validation"]["expected_row_count"], f"Unexpected row count: {len(records)}")
    key = spec["primary_key"]
    keys = [tuple(row[field] for field in key) for row in records]
    require(all(all(value is not None for value in k) for k in keys), "Null natural key")
    require(len(keys) == len(set(keys)), f"Duplicate natural key: {key}")
    missing = {field: sum(row[field] is None for row in records) for field in spec["columns"]}
    require(missing == spec["validation"]["expected_missing_counts"], f"Missing-value counts differ: {missing}")
    metrics = check_domain(spec, records)
    return records, {"row_count": len(records), "missing_counts": missing, **metrics}


def cross_dataset_checks(tables):
    results = []
    annual = tables.get("crop_annual_features")
    detailed = tables.get("crop_class_annual_features")
    if annual is not None and detailed is not None:
        for row in annual:
            area = sum(r["area_ha"] for r in detailed if r["year"] == row["year"] and
                       (r["crop_code"] == row["crop_code"] if row["crop_code"] in (1, 5) else r["crop_code"] not in (1, 5)))
            require(close(area, row["area_ha"], 1e-6), "Grouped crop areas disagree with detailed CDL classes")
        results.append("Grouped annual crop areas match the detailed class table for every year and grouped class.")
    transitions = tables.get("crop_transition_features")
    if annual is not None and transitions is not None:
        denominators = {r["year"]: r["valid_denominator_ha"] for r in annual}
        require(all(r["common_valid_area_ha"] <= min(denominators[r["year_1"]], denominators[r["year_2"]]) for r in transitions),
                "Common-valid transition area exceeds an annual valid area")
        results.append("Every common-valid transition denominator is bounded by both annual valid denominators.")
    monthly, composites = tables.get("modis_monthly_features"), tables.get("modis_16day_features")
    if monthly is not None and composites is not None:
        for row in monthly:
            observations = [r for r in composites if r["date"][:7] == row["month"]]
            require(len(observations) == row["observation_count"], "MODIS monthly observation accounting differs")
            require(sum(r["total_pixel_count"] for r in observations) == row["total_pixel_observations"], "MODIS monthly pixel accounting differs")
            for vi in ("ndvi", "evi"):
                count = sum(r[f"{vi}_valid_pixel_count"] for r in observations)
                require(count == row[f"{vi}_valid_pixel_count"], "MODIS monthly valid-count sum differs")
                if count:
                    weighted = sum(r[f"{vi}_mean"] * r[f"{vi}_valid_pixel_count"] for r in observations if r[f"{vi}_mean"] is not None) / count
                    require(close(weighted, row[f"{vi}_mean"], 1e-10), "MODIS monthly mean is not valid-pixel weighted")
        results.append("MODIS monthly counts and NDVI/EVI weighted means match all 207 source composites; pooled medians/std are preserved, not reconstructed.")
    return results


def validate_package(root):
    result = {"status": "PASS", "errors": [], "warnings": [], "datasets": [], "cross_dataset_checks": []}
    tables = {}
    try:
        inventory, errors = verify_inventory(root)
        result["protected_file_count"] = len(inventory["files"])
        result["errors"].extend(errors)
        manifest_path = root / FEATURE_DIR / "feature_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        require(manifest["phase"] == "2A" and manifest["contract_version"] == "1.0.0", "Manifest phase/version differs")
        require(manifest["county_scope"] == {"name": "Story County, Iowa", "geoid": "19169"}, "Manifest county scope differs")
        require(manifest["source_inventory_path"] == INVENTORY_PATH, "Manifest inventory path differs")
        require(manifest["source_inventory_sha256"] == sha256(root / INVENTORY_PATH), "Source inventory fingerprint differs")
        entries = manifest["datasets"]
        require(len({e["dataset_name"] for e in entries}) == len(entries), "Duplicate manifest dataset")
        by_name = {e["dataset_name"]: e for e in entries}
        unavailable = {e["dataset_name"]: e for e in manifest["unavailable_datasets"]}
        require(len(unavailable) == len(manifest["unavailable_datasets"]), "Duplicate unavailable dataset")
        known = {s["dataset_name"] for s in DATASETS}
        require(set(by_name).isdisjoint(unavailable) and set(by_name) | set(unavailable) == known,
                "Manifest must account for every known dataset exactly once")
        for spec in DATASETS:
            name = spec["dataset_name"]
            item = {"dataset_name": name, "status": "PASS"}
            try:
                if name not in by_name:
                    reason = unavailable[name]["reason"]
                    require(bool(reason), "Unavailable dataset needs a reason")
                    if not spec["optional"]:
                        raise ValueError(f"Required dataset unavailable: {reason}")
                    item.update(status="OMITTED", reason=reason)
                    result["warnings"].append(f"Optional {name} omitted: {reason}")
                    continue
                entry = by_name[name]
                for field in ("path", "schema_path", "source_path", "primary_key", "temporal_grain", "spatial_grain", "optional"):
                    require(entry[field] == spec[field], f"Manifest {field} differs from reviewed contract")
                output = local_path(root, entry["path"])
                source = local_path(root, entry["source_path"])
                schema = local_path(root, entry["schema_path"])
                require(json.loads(schema.read_text(encoding="utf-8")) == row_schema(spec), "JSON schema differs from reviewed contract")
                require(entry["schema_sha256"] == sha256(schema), "Schema hash differs")
                require(entry["source_sha256"] == sha256(source), "Source hash differs")
                require(entry["output_sha256"] == sha256(output), "Output hash differs")
                require(source.read_bytes() == output.read_bytes(), "Source-to-output records differ (byte preservation failed)")
                records, metrics = validate_table(output, spec)
                require(entry["row_count"] == len(records), "Manifest row count differs")
                require(entry["coverage"] == spec["validation"]["coverage"], "Manifest coverage differs")
                require(entry["provenance"] == spec["provenance"], "Manifest provenance differs")
                for evidence in spec["provenance"]["evidence_paths"]:
                    require(local_path(root, evidence).is_file(), f"Provenance evidence missing: {evidence}")
                require(entry["nullable_fields"] == [c for c, p in spec["columns"].items() if isinstance(p["type"], list) and "null" in p["type"]],
                        "Manifest nullable fields differ")
                item.update(metrics)
                tables[name] = records
                result["warnings"].extend(f"{name}: {warning}" for warning in spec["warnings"])
            except (OSError, ValueError, KeyError, TypeError, csv.Error, OverflowError) as error:
                item.update(status="FAIL", error=str(error))
                result["errors"].append(f"{name}: {error}")
            finally:
                result["datasets"].append(item)
        try:
            result["cross_dataset_checks"] = cross_dataset_checks(tables)
        except (ValueError, KeyError, TypeError) as error:
            result["errors"].append(f"Cross-dataset validation: {error}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        result["errors"].append(f"Package metadata/inventory: {error}")
    if result["errors"]:
        result["status"] = "FAIL"
    return result


def markdown_report(result):
    lines = ["# Phase 2A MVP Validation Report", "", f"**Status: {result['status']}**", "",
             "Reproduce with `.venv/bin/python -B -m src.validation.validate_mvp` from the repository root.", "",
             "Validation uses only the existing Python environment and standard library. It reads CSVs and file bytes; no raster pixels or polygon overlays are processed.", "",
             "## Package checks", "",
             "Checks: required ordered columns, strict types, finite numerics and declared ranges, duplicate/non-null natural keys, exact date/year coverage, expected null counts, per-year/per-pair denominators, percentage arithmetic, source/output byte equality, manifest paths/metadata, JSON Schema contracts and SHA-256 hashes.", "",
             f"Protected original files checked against the pre-build baseline: **{result.get('protected_file_count', 0)}**. This includes all original data, five rasters, the GeoPackage, boundary, dependencies, .gitignore and environment documents.", "",
             "The schemas describe decoded JSON records. CSV null tokens are empty cells and `NULL`; `True`/`False` decode to booleans; `mukey` stays a string. The validator implements the contract keywords used here without adding a JSON Schema dependency.", "",
             "## Dataset results", "", "| Dataset | Status | Actual rows | Missing cells |", "|---|---|---:|---:|"]
    for item in result["datasets"]:
        lines.append(f"| {item['dataset_name']} | {item['status']} | {item.get('row_count', '—')} | {sum(item.get('missing_counts', {}).values()) if 'missing_counts' in item else '—'} |")
    lines += ["", "## Cross-dataset checks", ""]
    lines.extend(f"- {message}" for message in result["cross_dataset_checks"])
    lines += ["", "## Crop denominator and rounding checks", "",
              f"Approved maximum absolute percentage error: **{PCT_TOLERANCE} percentage points**. Existing percentages remain unchanged. Displayed percentage sums can differ slightly from 100 because individual source values are rounded.", "",
              "| Dataset | Period | Denominator (ha) | Area sum (ha) | Percentage sum | Maximum error (percentage points) |",
              "|---|---|---:|---:|---:|---:|"]
    for item in result["datasets"]:
        for metric in item.get("denominator_checks", []):
            lines.append(f"| {item['dataset_name']} | {metric['period']} | {metric['denominator_ha']} | {metric['area_sum_ha']} | {metric['area_pct_sum']:.4f} | {metric['maximum_percentage_error_points']} |")
    lines += ["", "## Preserved missing values", ""]
    for item in result["datasets"]:
        nonzero = {k: v for k, v in item.get("missing_counts", {}).items() if v}
        if nonzero:
            lines.append(f"- {item['dataset_name']}: " + "; ".join(f"`{k}` = {v}" for k, v in nonzero.items()) + ".")
    lines += ["", "## Warnings and limitations", ""]
    lines.extend(f"- {warning}" for warning in dict.fromkeys(result["warnings"]))
    lines += ["", "Local audits provide upstream raw-data and spatial-method evidence. This run validates the delivered tables and preservation of local inputs; it does not independently repeat raw NetCDF extraction, pixel-level masking, or USDA spatial extraction.", "",
              "## Unresolved failures", ""]
    lines.extend(f"- {error}" for error in result["errors"])
    if not result["errors"]:
        lines.append("None. All seven required tables and the included optional table pass the checks above." if all(item["status"] == "PASS" for item in result["datasets"]) else "None for the required package; see documented optional omissions.")
    lines += ["", "Phase 2A ends at this handoff. Phase 2B spatial features, recommendations, APIs and UI are deferred.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root; defaults to the location of this module")
    args = parser.parse_args()
    result = validate_package(args.root.resolve())
    write_json(args.root / "reports/mvp_validation_results.json", result)
    write_text(args.root / "reports/mvp_validation_report.md", markdown_report(result))
    print(f"Phase 2A validation: {result['status']}")
    for item in result["datasets"]:
        print(f"  {item['dataset_name']}: {item['status']} ({item.get('row_count', 'unavailable')} rows)")
    for error in result["errors"]:
        print(f"ERROR: {error}")
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
