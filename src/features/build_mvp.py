"""Copy existing validated CSVs into the Phase 2A package and emit contracts.

Run: .venv/bin/python -B -m src.features.build_mvp
No downloads, package changes, spatial processing, or new scientific indicators.
"""

import argparse
import csv
import json
import shutil
from pathlib import Path

from src.features.phase2a_contracts import DATASETS, FEATURE_DIR, INVENTORY_PATH, row_schema
from src.validation.validate_mvp import (
    INTEGER, NUMBER, ROOT, markdown_report, protected_paths, require, sha256,
    validate_package, validate_table, verify_inventory, write_json, write_text,
)


def ensure_inventory(root):
    path = root / INVENTORY_PATH
    if not path.exists():
        write_json(path, {
            "description": "Pre-build SHA-256 baseline of every existing data file, dependency file, .gitignore, and environment document. Excludes generated Phase 2A artifacts.",
            "files": [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": sha256(p)}
                      for p in protected_paths(root) if p.is_file()],
        })
    return verify_inventory(root)


def profile_inputs(root, inventory):
    """Record inspected headers, inferred CSV types, nulls, ranges and row counts."""
    profiles = []
    for item in inventory["files"]:
        if not item["path"].endswith(".csv"):
            continue
        profile = {"path": item["path"], "baseline_sha256": item["sha256"]}
        try:
            with (root / item["path"]).open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream, strict=True)
                columns = reader.fieldnames
                rows = list(reader)
            profile.update(row_count=len(rows), columns=[])
            for field in columns:
                values = [r[field] for r in rows if r[field] not in ("", "NULL")]
                kind = "string"
                if field != "mukey" and values:
                    if all(v in ("True", "False") for v in values):
                        kind = "boolean"
                    elif all(INTEGER.fullmatch(v) for v in values):
                        kind = "integer"
                    elif all(NUMBER.fullmatch(v) for v in values):
                        kind = "number"
                metric = {"name": field, "inferred_csv_type": kind if values else "all-null",
                          "missing_count": len(rows) - len(values), "distinct_non_null_count": len(set(values))}
                if values:
                    ordered = [float(v) for v in values] if kind in ("integer", "number") else values
                    metric.update(min=min(ordered), max=max(ordered))
                profile["columns"].append(metric)
        except (OSError, ValueError, KeyError, TypeError, csv.Error) as error:
            profile["error"] = str(error)
        profiles.append(profile)
    return {"scope": "All original local CSVs, including daily and non-selected existing summaries; no regeneration.",
            "null_tokens": ["", "NULL"], "identifier_type_override": {"mukey": "string"}, "inputs": profiles}


def dictionary(entries, unavailable):
    by_name = {entry["dataset_name"]: entry for entry in entries}
    lines = ["# Phase 2A Feature Dictionary", "",
             "Generated from the reviewed contracts in `src/features/phase2a_contracts.py`. All delivered data values are unchanged source values; this MVP adds no indicators.", "",
             "JSON schemas describe decoded CSV rows. Read `mukey` as a string; decode empty cells and literal `NULL` as missing only in declared nullable fields; decode `True`/`False` as booleans. Every column is required in the CSV, including nullable columns. A unit of `—` means not applicable or not separately verified; no unit is inferred for an identifier.", "",
             "Natural keys are unique within each table's declared Story County or source spatial scope. County GEOID `19169` is contract metadata, not an added CSV column. Never join different grains by row order.", ""]
    for spec in DATASETS:
        name = spec["dataset_name"]
        if name not in by_name:
            reason = next(item["reason"] for item in unavailable if item["dataset_name"] == name)
            lines += [f"## {name}", "", f"Unavailable: {reason}", ""]
            continue
        entry = by_name[name]
        lines += [f"## {name}", "", f"- File: `{spec['path']}` ({entry['row_count']} rows).",
                  f"- Source: `{spec['source_path']}`; byte-for-byte copy.",
                  f"- Key: `{', '.join(spec['primary_key'])}`.", f"- Temporal grain: {spec['temporal_grain']}.",
                  f"- Spatial grain: {spec['spatial_grain']}.",
                  f"- Coverage: `{json.dumps(spec['validation']['coverage'])}`.",
                  f"- Contract: `{spec['schema_path']}`.", "",
                  "| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |",
                  "|---|---|---|---|---:|---|"]
        for field, prop in spec["columns"].items():
            types = prop["type"] if isinstance(prop["type"], list) else [prop["type"]]
            dtype = next(t for t in types if t != "null")
            lines.append(f"| `{field}` | {dtype} | {prop['x-unit'] or '—'} | {'yes' if 'null' in types else 'no'} | {spec['validation']['expected_missing_counts'][field]} | {prop['description']} |")
        lines += [""]
        lines.extend(f"- {warning}" for warning in spec["warnings"])
        lines += [""]
    lines += ["## Denominators and time support", "",
              "Annual valid area: 148,572.90 ha in 2021–2023; 148,573.80 ha in 2024–2025. Each annual table partitions its own year's valid area. Exclude CDL 0 and 255.", "",
              "Transition common-valid area: 148,572.90 ha for 2021→2022 and 2022→2023; 148,539.33 ha for 2023→2024; 148,573.80 ha for 2024→2025. Each pair partitions only area valid in both years.", "",
              "Every source `area_pct` is preserved. QA recomputes `100 × area_ha / denominator` using an absolute tolerance of 0.000050001 percentage points. Do not replace denominators with a fixed county area or use relative percent tolerance.", "",
              "MODIS monthly means pool valid pixel observations (valid-count weighted), while medians and standard deviations use the original pooled pixels. Monthly statistics are preserved; the validator can reproduce means and counts from composites, but cannot reconstruct pooled medians/std from summaries alone.", "",
              "NASA POWER monthly radiation totals have units MJ/m² over the represented month, and precipitation totals have units mm over that month; daily means retain MJ/m²/day and mm/day. The source daily parameter units and existing monthly aggregation definitions establish these units.", "",
              "MERRA-2 keeps native monthly-mean rates and energy fluxes from the selected-variable CSV. Existing duration-converted analysis, seasonal, and annual products remain in their original directory and are outside the MVP consumption manifest.", ""]
    return "\n".join(lines)


def build(root):
    inventory, inventory_errors = ensure_inventory(root)
    write_json(root / "reports/phase2a_input_audit.json", profile_inputs(root, inventory))
    baseline = {item["path"]: item for item in inventory["files"]}
    entries, unavailable = [], []
    for spec in DATASETS:
        name = spec["dataset_name"]
        source, output, schema = (root / spec[field] for field in ("source_path", "path", "schema_path"))
        try:
            require(source.is_file(), f"Input CSV missing: {spec['source_path']}")
            reference = baseline[spec["source_path"]]
            if sha256(source) != reference["sha256"]:
                raise ValueError("Source differs from the preserved pre-build baseline")
            records, _ = validate_table(source, spec)
            output.parent.mkdir(parents=True, exist_ok=True)
            if not output.exists() or output.read_bytes() != source.read_bytes():
                shutil.copyfile(source, output)
            write_json(schema, row_schema(spec))
            entry = {field: spec[field] for field in (
                "dataset_name", "path", "schema_path", "source_path", "primary_key", "temporal_grain", "spatial_grain", "optional")}
            entry.update(row_count=len(records), source_sha256=sha256(source), output_sha256=sha256(output),
                         schema_sha256=sha256(schema), coverage=spec["validation"]["coverage"],
                         nullable_fields=[field for field, prop in spec["columns"].items()
                                          if isinstance(prop["type"], list) and "null" in prop["type"]],
                         provenance=spec["provenance"])
            entries.append(entry)
            print(f"Built {name}: {len(records)} rows", flush=True)
        except (OSError, ValueError, KeyError, TypeError, csv.Error) as error:
            unavailable.append({"dataset_name": name, "optional": spec["optional"], "reason": str(error)})
            # Remove only known generated artifacts so an older output cannot look current.
            output.unlink(missing_ok=True)
            schema.unlink(missing_ok=True)
            print(f"Unavailable {name}: {error}", flush=True)
    manifest = {
        "phase": "2A", "contract_version": "1.0.0",
        "county_scope": {"name": "Story County, Iowa", "geoid": "19169"},
        "processing": "Existing validated CSVs copied byte for byte; source values, order, dates, units, precision, and null tokens preserved.",
        "source_inventory_path": INVENTORY_PATH, "source_inventory_sha256": sha256(root / INVENTORY_PATH),
        "datasets": entries, "unavailable_datasets": unavailable,
    }
    write_json(root / FEATURE_DIR / "feature_manifest.json", manifest)
    write_text(root / "docs/feature_dictionary.md", dictionary(entries, unavailable))
    result = validate_package(root)
    write_json(root / "reports/mvp_validation_results.json", result)
    write_text(root / "reports/mvp_validation_report.md", markdown_report(result))
    print(f"Phase 2A validation: {result['status']}", flush=True)
    for error in result["errors"]:
        print(f"ERROR: {error}", flush=True)
    # inventory_errors are also reported by validate_package, including unrelated sources.
    return int(bool(result["errors"] or inventory_errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    return build(args.root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
