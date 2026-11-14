"""Prepare/validate the isolated daily supplement; never rebuild Phase 2A.

Offline preparation: .venv/bin/python -B -m src.features.prepare_power_daily_context
Offline validation: add --validate-only. Download only if the cached source is
absent: add --download. Existing downloads are never silently overwritten.
"""

import argparse
import calendar
import csv
import hashlib
import io
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/processed/features/supplemental"
PARAMETERS = ["T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS10M",
              "ALLSKY_SFC_SW_DWN", "PRECTOTCORR", "PS", "T2MDEW"]
UNITS = dict(zip(PARAMETERS, ["C", "C", "C", "%", "m/s", "MJ/m^2/day", "mm/day", "kPa", "C"]))
REQUEST = {"parameters": ",".join(PARAMETERS), "community": "AG", "latitude": "42.0375",
           "longitude": "-93.4661", "start": "20210101", "end": "20251231", "format": "CSV", "time-standard": "UTC"}
URL = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urlencode(REQUEST)
COORDS = {"latitude": 42.0375, "longitude": -93.4661}
FIELDS = ["date", "latitude", "longitude", "YEAR", "DOY", *PARAMETERS]
RAW = "source/power_daily_point_response.csv"
RETRIEVAL = "source/retrieval.json"
BASELINE = "source/existing_workspace_sha256.json"
CSV = "power_daily_context.csv"
META = "power_daily_context_metadata.json"
AUDIT = "power_daily_context_audit.md"
# Conservative plausibility screens, not NASA valid-range metadata or agronomic thresholds.
RANGES = {p: [-100, 70] for p in ("T2M_MAX", "T2M_MIN", "T2M", "T2MDEW")}
RANGES.update(RH2M=[0, 100], WS10M=[0, 100], ALLSKY_SFC_SW_DWN=[0, 60], PRECTOTCORR=[0, 1000], PS=[50, 110])
DOCS = {"nasa_daily_api": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
        "fao56_meteorology": "https://www.fao.org/4/x0490e/x0490e07.htm"}
ET0 = {
    "status": "Conditionally supports a future FAO-56 daily ET0 implementation; no ET0 calculated.",
    "available": ["Daily Tmin/Tmax/Tmean in C, RHmean in %, WS10M in m/s, incoming solar radiation in MJ/m^2/day, pressure in kPa, date and latitude.",
                  "Optional T2MDEW is returned in C, explicitly labelled Dew/Frost Point, with no missing cells.",
                  "Header reports MERRA-2 grid-average elevation 310.22 m; this is not surveyed point elevation."],
    "required_decisions_and_assumptions": [
        "Convert 10 m wind to 2 m wind using FAO-56 Eq. 47 and its reference-surface assumptions; do not use WS10M directly as u2.",
        "Incoming shortwave Rs is not net radiation Rn. Derive net shortwave with reference-grass albedo 0.23 and estimate net longwave with documented FAO-56 assumptions.",
        "Clear-sky radiation needs an elevation choice. Surveyed point elevation is absent; explicitly approve the supplied coarse grid-average elevation or supply a validated point elevation in a separate task. Do not silently reinterpret it.",
        "RHmax/RHmin are absent. Evaluate a daily mean dew/frost-point vapour-pressure method (including freezing conventions and nonlinear daily averaging) or the less preferred RHmean method; do not invent RH extrema.",
        "Use validated PS in kPa for the psychrometric constant; no pressure unit conversion is needed.",
        "Document daily soil heat flux G≈0, extraterrestrial radiation from latitude/day-of-year, reference grass assumptions and consistency of UTC daily aggregates with FAO daily procedures.",
        "Reanalysis and satellite point-request values retain native spatial support, not field measurements; validate future ET0 implementation and missing-data handling before use."],
    "not_provided": ["ET0", "ETc", "irrigation requirements", "crop water savings"],
    "reference": DOCS["fao56_meteorology"],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def preserve_sources():
    baseline = json.loads((OUT / BASELINE).read_text())
    for relative, expected in baseline.items():
        path = ROOT / relative
        require(path.is_file() and digest(path) == expected, f"Pre-existing file changed or missing: {relative}")
    return len(baseline)


def download():
    require(not (OUT / RAW).exists() and not (OUT / RETRIEVAL).exists(), "Cached source exists; reuse it. No overwrite permitted.")
    (OUT / "source").mkdir(parents=True, exist_ok=True)
    with urlopen(Request(URL, headers={"User-Agent": "TerraPulse-Daily-Supplement/1.0"}), timeout=180) as response:
        raw = response.read()
        retrieval = {"source_url": URL, "final_url": response.url,
                     "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "http_status": response.status,
                     "response_headers": dict(response.headers), "request_parameters": REQUEST,
                     "sha256": hashlib.sha256(raw).hexdigest()}
    require(b"-END HEADER-" in raw, "Response is not a NASA POWER metadata CSV")
    (OUT / RAW).write_bytes(raw)
    write_json(OUT / RETRIEVAL, retrieval)


def prepare_records():
    retrieval = json.loads((OUT / RETRIEVAL).read_text())
    require(retrieval["source_url"] == URL and retrieval["request_parameters"] == REQUEST, "Request identity differs")
    require(retrieval["http_status"] == 200, "HTTP retrieval was not successful")
    require(datetime.fromisoformat(retrieval["retrieved_at_utc"]).utcoffset() == timedelta(0), "Retrieval timestamp must be UTC")
    require(digest(OUT / RAW) == retrieval["sha256"], "Raw source checksum differs")
    header, body = (OUT / RAW).read_text(encoding="utf-8-sig").split("-END HEADER-", 1)
    require("01/01/2021 through 12/31/2025 in UTC" in header, "Source dates/time standard differ")
    coordinate_match = re.search(r"Location: latitude\s+([-\d.]+)\s+longitude\s+([-\d.]+)", header)
    require(coordinate_match is not None, "Returned coordinates absent")
    returned = dict(zip(("latitude", "longitude"), map(float, coordinate_match.groups())))
    require(returned == COORDS, f"Returned coordinates differ: {returned}")
    fill_match = re.search(r"sources availability range:\s*([-\d.]+)", header)
    require(fill_match is not None, "Fill-value metadata absent")
    fill = float(fill_match[1])
    parameters = {}
    for line in header.splitlines():
        match = re.fullmatch(r"([A-Z0-9_]+)\s+(.+?)\s+\(([^()]*)\)\s*", line)
        if match:
            parameters[match[1]] = {"description": match[2], "unit": match[3]}
    require({p: parameters[p]["unit"] for p in PARAMETERS} == UNITS, "Returned parameter units differ from reviewed units")
    elevation = re.search(r"elevation from MERRA-2: (.+?)=\s*([-\d.]+) meters", header)
    require(elevation is not None, "Source elevation metadata absent")
    reader = csv.DictReader(io.StringIO(body.lstrip()), strict=True)
    require(reader.fieldnames == ["YEAR", "DOY", *PARAMETERS], "Source columns differ")
    records, numeric = [], {p: [] for p in PARAMETERS}
    missing, fills, invalid = ({p: 0 for p in PARAMETERS} for _ in range(3))
    for index, row in enumerate(reader, 1):
        require(None not in row and all(v is not None for v in row.values()), f"Malformed CSV row {index}")
        year, doy = int(row["YEAR"]), int(row["DOY"])
        require(1 <= doy <= (366 if calendar.isleap(year) else 365), f"Invalid DOY row {index}")
        day = date(year, 1, 1) + timedelta(days=doy - 1)
        record = {"date": day.isoformat(), "latitude": str(returned["latitude"]), "longitude": str(returned["longitude"]), **row}
        values = {}
        for p in PARAMETERS:
            value = row[p]
            if value.strip() in ("", "NULL", "NaN", "nan"):
                missing[p] += 1
                continue
            number = float(value)
            if number == fill or number == -999:
                fills[p] += 1
                continue
            require(math.isfinite(number), f"Non-finite {p} on {day}")
            numeric[p].append(number)
            values[p] = number
            if not RANGES[p][0] <= number <= RANGES[p][1]:
                invalid[p] += 1
        if all(p in values for p in ("T2M_MIN", "T2M", "T2M_MAX")):
            require(values["T2M_MIN"] <= values["T2M"] <= values["T2M_MAX"], f"Temperature ordering invalid on {day}")
        records.append(record)
    expected = [(date(2021, 1, 1) + timedelta(days=i)).isoformat() for i in range(1826)]
    dates = [r["date"] for r in records]
    validation = {"actual_records": len(records), "expected_records": 1826,
                  "missing_dates": sorted(set(expected) - set(dates)), "unexpected_dates": sorted(set(dates) - set(expected)),
                  "duplicate_date_count": len(dates) - len(set(dates)), "chronologically_complete": dates == expected,
                  "missing_values": missing, "fill_values": fills, "out_of_screen_range_values": invalid,
                  "observed_ranges": {p: {"min": min(v) if v else None, "max": max(v) if v else None} for p, v in numeric.items()},
                  "screen_ranges": RANGES, "range_policy": "Broad plausibility screens for Iowa, not NASA valid-range metadata; fail and investigate, never clip.",
                  "returned_units_match": True, "requested_and_returned_coordinates_match": True,
                  "source_checksum_matches": True, "all_preexisting_files_unchanged": True,
                  "protected_preexisting_file_count": preserve_sources()}
    passed = dates == expected and all(not sum(counts.values()) for counts in (missing, fills, invalid))
    validation["status"] = "PASS" if passed else "FAIL"
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    metadata = {
        "dataset_name": "power_daily_context", "source": "NASA POWER Daily Point API", "community": "AG",
        "source_url": URL, "retrieval": retrieval, "raw_source_path": RAW,
        "existing_data_reused": False, "new_api_download_necessary": True,
        "input_inspection_path": "input_inspection.json", "requested_coordinates": COORDS, "returned_coordinates": returned,
        "coordinate_units": {"latitude": "degrees_north", "longitude": "degrees_east"},
        "source_grid_cell_center_coordinates": None,
        "coordinate_note": "The CSV header echoes the request point; it does not disclose the contributing grid-cell centers. Matching coordinates do not imply field-scale observations.",
        "source_grid_average_elevation": {"meters": float(elevation[2]), "spatial_support": elevation[1].strip(), "surveyed_point_elevation": False},
        "spatial_interpretation": "One representative point requested at 42.0375, -93.4661, retaining POWER native source resolution; not a county-wide spatial average. No averaging/substitution of the four existing points.",
        "time_standard": "UTC", "date_coverage": {"start": "2021-01-01", "end": "2025-12-31", "inclusive": True},
        "temporal_grain": "Daily UTC", "primary_key": ["date"], "columns": FIELDS,
        "parameter_metadata": parameters, "optional_T2MDEW": {"available": True, "unit": parameters["T2MDEW"]["unit"], "description": parameters["T2MDEW"]["description"]},
        "missing_value_policy": {"imputation": "none", "source_fill_value": fill, "csv_encoding": "Source numeric strings, blanks and fill markers are preserved verbatim; Backend must treat fill as missing, never as weather observations."},
        "transformation": "Add ISO date from YEAR/DOY and returned header coordinates; retain parameter strings/order without conversion, rounding, aggregation or imputation.",
        "validation": validation, "et0_readiness": ET0, "references": DOCS,
        "checksums": {"algorithm": "SHA-256", "source_csv": digest(OUT / RAW), "output_csv": hashlib.sha256(stream.getvalue().encode()).hexdigest(),
                      "input_inspection": digest(OUT / "input_inspection.json"), "source_preservation_baseline": digest(OUT / BASELINE)},
    }
    return stream.getvalue().encode(), metadata


def audit(metadata):
    v = metadata["validation"]
    lines = ["# NASA POWER Daily Weather Supplement Audit", "", f"**Validation: {v['status']}**", "",
             "Existing daily data was inspected but not reused: four distinct points each have 1,826 dates in 2021–2025, but none is the requested point; WS10M and PS are absent. Fourteen original weather exports were inspected read-only and have the same parameter/location gaps. Details and original headers/checksums are in `input_inspection.json`.", "",
             "One new NASA POWER Daily Point CSV request was necessary. No alternate datasets were downloaded. The endpoint URL was not included in the task text; the official documented endpoint was used.", "",
             f"Source URL: {URL}", "", f"Retrieved at (UTC): {metadata['retrieval']['retrieved_at_utc']}", "",
             "Requested and header-returned coordinates: latitude 42.0375, longitude -93.4661. They are stored separately in metadata. Actual contributing grid centers are not supplied by the CSV. This is a native-resolution point request, not a county spatial average or field measurement.", "",
             f"Records: **{v['actual_records']}**; inclusive coverage 2021-01-01 through 2025-12-31, UTC. Missing dates: {len(v['missing_dates'])}; duplicate dates: {v['duplicate_date_count']}; unexpected dates: {len(v['unexpected_dates'])}.", "",
             "| Parameter | NASA header unit | Minimum | Maximum | Missing | Fill | Outside screen |", "|---|---|---:|---:|---:|---:|---:|"]
    for p in PARAMETERS:
        lines.append(f"| {p} | {UNITS[p]} | {v['observed_ranges'][p]['min']} | {v['observed_ranges'][p]['max']} | {v['missing_values'][p]} | {v['fill_values'][p]} | {v['out_of_screen_range_values'][p]} |")
    lines += ["", "Ranges are broad plausibility screens documented in metadata, not NASA product valid-range limits. Numeric finiteness, Tmin ≤ Tmean ≤ Tmax, YEAR/DOY validity, complete chronological calendar, parameter units, coordinates, retrieval identity/time and checksums are checked. No values are clipped or imputed. Optional T2MDEW was supported and is labelled Dew/Frost Point at 2 Meters (C).", "",
              f"Preservation: all {v['protected_preexisting_file_count']} pre-existing workspace files match the pre-download baseline, including Phase 2A tables, schemas, manifest and reports. The four existing POWER point identities remain unchanged.", "",
              "## Backend consumption", "", "Use `power_daily_context.csv` with `power_daily_context_metadata.json`. Key: date within this fixed single-point dataset. All columns are required; YEAR/DOY are integers, date is ISO text, coordinates and weather values are numeric. Source missing/fill markers remain missing under the documented policy. This supplement has no registration in the unchanged Phase 2A manifest.", "",
              "## FAO-56 ET0 readiness", "", ET0["status"], ""]
    lines.extend(f"- {item}" for item in ET0["available"] + ET0["required_decisions_and_assumptions"])
    lines += ["", "ET0 is conditional on those explicit method/elevation decisions. No missing inputs are fabricated. No ET0, ETc, irrigation demand or crop water savings are calculated.", "",
              f"Method references: [NASA POWER Daily API]({DOCS['nasa_daily_api']}), [FAO-56 Chapter 3]({DOCS['fao56_meteorology']}).", "",
              "## Checksums", "", f"- Raw source CSV: `{metadata['checksums']['source_csv']}`", f"- Backend CSV: `{metadata['checksums']['output_csv']}`", "- `checksums.sha256` also records metadata, this audit, inspection, retrieval record and preservation baseline checksums (avoiding self-referential hashes).", "",
              "## Reproduction", "", "Run from the repository root; offline by default:", "", "```bash", ".venv/bin/python -B -m src.features.prepare_power_daily_context", ".venv/bin/python -B -m src.features.prepare_power_daily_context --validate-only", "```", "",
              "The cached source is reused without network requests. `--download` is permitted only when both cached response and retrieval record are absent; it requests only the same exact NASA POWER point/time window. Do not remove the source preservation baseline or inspection record. This script does not call the Phase 2A builder or validator and never writes their files.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    require(not (args.download and args.validate_only), "Choose download/preparation or offline validation")
    if args.download:
        preserve_sources()
        download()
    data, metadata = prepare_records()
    if args.validate_only:
        require((OUT / CSV).read_bytes() == data, "Output differs from raw-source records")
        require(json.loads((OUT / META).read_text()) == metadata, "Metadata differs from recomputed provenance/validation")
        require((OUT / AUDIT).read_text() == audit(metadata), "Audit differs from validation results")
        for line in (OUT / "checksums.sha256").read_text().splitlines():
            expected, relative = line.split("  ", 1)
            require(digest(OUT / relative) == expected, f"Checksum differs: {relative}")
    else:
        (OUT / CSV).write_bytes(data)
        write_json(OUT / META, metadata)
        (OUT / AUDIT).write_text(audit(metadata), encoding="utf-8")
        paths = [CSV, META, AUDIT, RAW, RETRIEVAL, BASELINE, "input_inspection.json"]
        (OUT / "checksums.sha256").write_text("".join(f"{digest(OUT / p)}  {p}\n" for p in paths), encoding="utf-8")
    print(f"Daily supplement: {metadata['validation']['status']}; {metadata['validation']['actual_records']} records")
    print(f"CSV SHA-256: {metadata['checksums']['output_csv']}")
    return int(metadata["validation"]["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
