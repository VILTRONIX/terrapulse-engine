"""Reviewed Phase 2A CSV contracts. No spatial extraction or new indicators."""

from copy import deepcopy

FEATURE_DIR = "data/processed/features"
INVENTORY_PATH = "reports/phase2a_source_inventory.json"
PCT_TOLERANCE = "0.000050001"  # percentage points, not a relative tolerance
ANNUAL_DENOMINATORS = {2021: "148572.90", 2022: "148572.90", 2023: "148572.90",
                       2024: "148573.80", 2025: "148573.80"}
TRANSITION_DENOMINATORS = {(2021, 2022): "148572.90", (2022, 2023): "148572.90",
                           (2023, 2024): "148539.33", (2024, 2025): "148573.80"}
POWER_POINTS = {"DG001": (41.8914, -93.3975), "DG002": (41.8989, -93.5283),
                "DG003": (42.0172, -93.3144), "DG004": (42.0222, -93.4527)}


def column(dtype, description, unit=None, nullable=False, **constraints):
    result = {"type": [dtype, "null"] if nullable else dtype,
              "description": description, "x-unit": unit}
    result.update(constraints)
    return result


YEAR = column("integer", "Calendar year.", minimum=2021, maximum=2025)
AREA = column("number", "Area of this crop class or transition.", "ha", minimum=0)
PERCENT = column("number", "100 × area_ha / the row's applicable denominator; source rounded to four decimals.",
                 "%", minimum=0, maximum=100)
CODE = column("integer", "USDA CDL class code; 999 means aggregated Other only in the grouped table.", minimum=1)
SOURCE = column("string", "Unchanged source provenance label.", minLength=1)
DATE = column("string", "Source observation date (ISO calendar date).", format="date", pattern=r"^\d{4}-\d{2}-\d{2}$")


def vegetation_columns():
    fields = {}
    for vi in ("ndvi", "evi"):
        for stat in ("mean", "median", "std"):
            fields[f"{vi}_{stat}"] = column(
                "number", f"{vi.upper()} {stat} over quality-passing county pixel observations; already scaled.",
                "dimensionless", nullable=True, **({"minimum": 0} if stat == "std" else {}))
        fields[f"{vi}_valid_pixel_count"] = column("integer", "Quality-passing pixel observations contributing to this index.",
                                                     "pixel observations", minimum=0)
        fields[f"{vi}_valid_pixel_percentage"] = column("number", "100 × valid pixel observations / total pixel observations.",
                                                          "%", minimum=0, maximum=100)
    return fields


POWER_COLUMNS = {
    "location_id": column("string", "Selected NASA POWER representative point identifier.", enum=list(POWER_POINTS)),
    "latitude": column("number", "Source point latitude, north positive.", "degrees_north", minimum=-90, maximum=90),
    "longitude": column("number", "Source point longitude, east positive.", "degrees_east", minimum=-180, maximum=180),
    "year": column("integer", "Calendar year.", minimum=2017, maximum=2025),
    "month": column("integer", "Calendar month number.", minimum=1, maximum=12),
    "month_start": column("string", "First calendar date of the represented month.", format="date", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    "month_end": column("string", "Last calendar date of the represented month.", format="date", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    "days_expected": column("integer", "Calendar days expected in the month.", "days", minimum=28, maximum=31),
    "days_present": column("integer", "Source daily records present in the month.", "days", minimum=0, maximum=31),
    "complete": column("boolean", "True when days_present equals days_expected."),
    "T2M_mean": column("number", "Monthly arithmetic mean of daily 2 m temperature.", "C"),
    "T2M_MAX_mean": column("number", "Monthly arithmetic mean of daily maximum 2 m temperature.", "C"),
    "T2M_MIN_mean": column("number", "Monthly arithmetic mean of daily minimum 2 m temperature.", "C"),
    "PRECTOTCORR_total": column("number", "Sum of daily corrected precipitation amounts over the calendar month.", "mm", minimum=0),
    "PRECTOTCORR_daily_mean": column("number", "Arithmetic mean of daily corrected precipitation.", "mm/day", minimum=0),
    "ALLSKY_SFC_SW_DWN_total": column("number", "Sum of daily all-sky surface shortwave irradiation over the month.", "MJ/m^2", minimum=0),
    "ALLSKY_SFC_SW_DWN_daily_mean": column("number", "Arithmetic mean of daily all-sky surface shortwave irradiation.", "MJ/m^2/day", minimum=0),
    "RH2M_mean": column("number", "Monthly arithmetic mean of daily relative humidity at 2 m.", "%", minimum=0, maximum=100),
}
MODIS_MONTHLY_COLUMNS = {
    "month": column("string", "Calendar month label of the contributing 16-day observation dates.", pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    "observation_count": column("integer", "Number of contributing 16-day source observations.", "observations", minimum=1, maximum=2),
    "total_pixel_observations": column("integer", "37,193 county pixel centers × observation_count.", "pixel observations", minimum=1),
    **vegetation_columns(),
}
MODIS_16DAY_COLUMNS = {"date": DATE, **vegetation_columns(),
    "total_pixel_count": column("integer", "Pixel centers strictly within the Story County polygon.", "pixels", const=37193),
    "base_valid_pixel_count": column("integer", "Valid NDVI/EVI pixel pairs before quality filtering.", "pixels", minimum=0, maximum=37193),
    "quality_valid_pixel_count": column("integer", "Base-valid pixel pairs passing reliability=0 and MODLAND QA=0.", "pixels", minimum=0, maximum=37193),
    "vi_usefulness_distribution_before_filter": column("string", "JSON object mapping VI usefulness codes (bits 2–5) to base-valid pixel counts; no usefulness threshold applied.", **{"x-content": "json-count-object"}),
    "vi_usefulness_distribution_after_filter": column("string", "JSON object mapping VI usefulness codes to quality-passing pixel counts.", **{"x-content": "json-count-object"}),
}
CROP_COLUMNS = {"year": YEAR, "crop_code": CODE,
                "crop_name": column("string", "Source crop/land-cover label; CDL_Class_* placeholders are preserved.", minLength=1),
                "area_ha": AREA, "area_pct": PERCENT,
                "valid_denominator_ha": column("number", "Year-specific valid county area excluding CDL 0 and 255.", "ha", exclusiveMinimum=0),
                "source": SOURCE}
CLASS_COLUMNS = {}
for field, definition in CROP_COLUMNS.items():
    CLASS_COLUMNS[field] = definition
    if field == "crop_name":
        CLASS_COLUMNS["pixel_count"] = column("integer", "Valid classified 30 × 30 m pixels in this class; one pixel = 0.09 ha.", "pixels", minimum=0)
SOIL_COLUMNS = {
    "mukey": column("string", "Stable USDA SSURGO map-unit join key; load as a string.", pattern=r"^\d+$"),
    "musym": column("string", "Map-unit symbol.", minLength=1),
    "muname": column("string", "Official map-unit name.", minLength=1),
    "dominant_texture": column("string", "Dominant surface-horizon (0 cm) soil texture.", nullable=True),
    "awc_weighted_cm_per_cm": column("number", "Component-weighted surface-horizon available water capacity; not root-zone storage or current moisture.", "cm/cm", nullable=True, minimum=0),
    "organic_matter_weighted_pct": column("number", "Component-weighted surface-horizon organic matter.", "%", nullable=True, minimum=0, maximum=100),
    "dominant_drainage_class": column("string", "Dominant soil drainage class.", nullable=True),
    "dominant_hydrologic_group": column("string", "Dominant hydrologic soil group.", nullable=True),
    "slope_weighted_pct": column("number", "Component-weighted representative slope (percent rise; may exceed 100).", "%", nullable=True, minimum=0),
    "total_component_pct_accounted": column("integer", "Source component coverage percentage; retained as a quality/context field.", "%", minimum=0, maximum=100),
    "source": SOURCE,
    "root_zone_aws_0_150cm_mm": column("number", "NRCS muaggatt.aws0_150wta, 0–150 cm root-zone available water storage; unavailable for all 86 records; never impute.", "mm", nullable=True, minimum=0),
}
MERRA_COLUMNS = {
    "date": column("string", "First-of-month label for the source monthly mean; local audit reports original NetCDF timestamp at 00:30, absent from CSV.", format="date", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    "latitude": column("number", "Native coarse-grid latitude, north positive.", "degrees_north", const=42.0),
    "longitude": column("number", "Native coarse-grid longitude, east positive; keep both cells separate.", "degrees_east", enum=[-93.75, -93.125]),
    "SPEED": column("number", "Monthly mean surface wind speed; height not separately verified as 10 m.", "m s-1", minimum=0),
    "EVAP": column("number", "Monthly mean evaporation_from_turbulence; signs preserved; not crop water demand, ETc, or irrigation requirement.", "kg m-2 s-1"),
    "EFLUX": column("number", "Monthly mean total_latent_energy_flux; source signs retained without reassignment.", "W m-2"),
    "HFLUX": column("number", "Monthly mean sensible_heat_flux_from_turbulence; source signs retained without reassignment.", "W m-2"),
}

MODIS_WARNINGS = [
    "Use exact Story County pixel-center summaries only (37,193 pixels), not historical AOI/bounding-box summaries.",
    "Monthly statistics pool valid pixel observations; means are weighted by valid pixel counts. Months 2019-02 and 2021-01 have no valid statistics.",
    "Eighteen 16-day dates have no quality-passing pixels. December 2025 ends at the available 2025-12-19 observation; no interpolation.",
    "MODIS vegetation indices describe county greenness, not crop-specific stress or field observations.",
]
SOIL_WARNINGS = [
    "Root-zone AWS is NULL for all 86 map units and must never be imputed.",
    "Texture, surface AWC, organic matter, drainage, and hydrologic group each have nine NULLs; slope has seven NULLs.",
    "Map units are soil survey units, not farm/field ownership boundaries. No map-unit crop statistics or geometry is delivered.",
]
MERRA_WARNINGS = [
    "Optional supporting context only; never a primary decision-driving source.",
    "Two coarse cells at latitude 42.0 and longitudes -93.75/-93.125 remain separate; not a county-wide average or field-scale surface.",
    "EVAP is not crop water demand, ETc, or irrigation requirement. EFLUX/HFLUX are not direct crop-stress measurements.",
    "TSH is absent; Var_TSH is excluded, never a temperature substitute. PRECCON/PRECSNO remain deferred.",
    "Coverage begins June 2008, so 2008 is partial. Signs and native flux-rate units are preserved; no flux conversions are added.",
]


def dataset(name, source, columns, key, temporal, spatial, rows, coverage, audits, warnings=(), optional=False):
    return {
        "dataset_name": name, "path": f"{FEATURE_DIR}/{name}.csv",
        "schema_path": f"src/schemas/{name}.schema.json", "source_path": source,
        "primary_key": key, "temporal_grain": temporal, "spatial_grain": spatial,
        "county_scope": {"name": "Story County, Iowa", "geoid": "19169"},
        "optional": optional, "columns": columns,
        "provenance": {"source_path": source, "evidence_paths": audits,
                       "transformation": "Byte-for-byte copy of an existing validated CSV; no aggregation, imputation, conversion, or rounding."},
        "validation": {"expected_row_count": rows, "coverage": coverage,
                       "expected_missing_counts": {field: 0 for field in columns},
                       "requirements": ["Exact ordered source columns and declared CSV types.",
                                        "Unique, non-null natural key within the declared spatial scope.",
                                        "Finite numeric values, declared ranges, exact coverage and missing counts.",
                                        "Source and output records identical, including order, precision and null markers.",
                                        "Source/output/schema SHA-256 values and manifest metadata agree.",
                                        "Dataset-specific calendar, denominator, quality and unit-consistency checks."]},
        "warnings": list(warnings),
    }


DATASETS = [
    dataset("nasa_power_monthly_features", "data/processed/nasa_power/power_monthly_by_location.csv",
            POWER_COLUMNS, ["location_id", "year", "month"], "Calendar month at each representative point",
            "Four separate NASA POWER representative points; not a county average", 432,
            {"start": "2017-01", "end": "2025-12", "months_per_point": 108},
            ["data/processed/nasa_power/power_monthly_summary.md", "data/processed/nasa_power/power_daily_final_audit.md",
             "data/processed/nasa_power/power_selected_files.csv"],
            ["Selected points remain separate; monthly features reuse existing audited daily aggregates. Daily data is retained in its original location."]),
    dataset("modis_monthly_features", "data/processed/modis/modis_monthly_story_county_summary.csv",
            MODIS_MONTHLY_COLUMNS, ["month"], "Calendar month of available 16-day observations",
            "Exact Story County pixel-center mask; pooled quality-passing pixel observations", 108,
            {"start": "2017-01", "end": "2025-12"},
            ["data/processed/modis/story_county_mask_report.md", "data/processed/modis/modis_spatial_boundary_verification.md",
             "data/processed/modis/modis_final_monthly_coverage.md"], MODIS_WARNINGS),
    dataset("modis_16day_features", "data/processed/modis/modis_16day_story_county_summary.csv",
            MODIS_16DAY_COLUMNS, ["date"], "Source 16-day composite observation date",
            "Exact Story County pixel-center mask; 37,193 county pixel centers", 207,
            {"start": "2017-01-01", "end": "2025-12-19", "observations_per_year": 23},
            ["data/processed/modis/story_county_mask_report.md", "data/processed/modis/modis_spatial_boundary_verification.md",
             "data/processed/modis/modis_final_quality_audit.md"], MODIS_WARNINGS),
    dataset("crop_annual_features", "data/source_packages/member4_v3/tables/crop_area_by_year.csv",
            CROP_COLUMNS, ["year", "crop_code"], "Calendar year × grouped crop class (Corn/Soybeans/Other)",
            "Story County annual valid CDL mask; county totals", 15, {"start_year": 2021, "end_year": 2025},
            ["data/source_packages/member4_v3/data_dictionary.md", "data/source_packages/member4_v3/reports/validation_report.md"],
            ["Annual valid area is year-specific. Code 999 aggregates all classes other than Corn (1) and Soybeans (5); not a native CDL class."]),
    dataset("crop_class_annual_features", "data/source_packages/member4_v3/tables/crop_class_area_by_year.csv",
            CLASS_COLUMNS, ["year", "crop_code"], "Calendar year × original CDL crop/land-cover class",
            "Story County annual valid CDL mask; county totals", 156, {"start_year": 2021, "end_year": 2025},
            ["data/source_packages/member4_v3/source_manifest.md", "data/source_packages/member4_v3/reports/phase2_input_audit.md"],
            ["Preserve source CDL_Class_* label placeholders; not all class names are resolved. CDL 0 and 255 are excluded; source 2024–2025 products are harmonized to 30 m."]),
    dataset("crop_transition_features", "data/source_packages/member4_v3/tables/crop_transitions.csv",
            {"year_1": YEAR, "year_2": YEAR,
             "transition_type": column("string", "Directed grouped transition label (Corn/Soybeans/Other -> Corn/Soybeans/Other).", minLength=1),
             "area_ha": AREA, "area_pct": PERCENT,
             "common_valid_area_ha": column("number", "Pair-specific county area valid in both consecutive years, excluding CDL 0 and 255.", "ha", exclusiveMinimum=0)},
            ["year_1", "year_2", "transition_type"], "Consecutive year pair × directed grouped transition",
            "Story County common-valid CDL mask for each year pair; county totals", 36,
            {"year_pairs": [[a, b] for a, b in TRANSITION_DENOMINATORS]},
            ["data/source_packages/member4_v3/data_dictionary.md", "data/source_packages/member4_v3/reports/validation_report.md"],
            ["Each year pair has its own common-valid denominator; county totals do not locate transitions or establish farm management history."]),
    dataset("soil_mapunit_features", "data/source_packages/member4_v3/soil/soil_summary.csv",
            SOIL_COLUMNS, ["mukey"], "Static source soil attribute lookup; no observation year assigned",
            "USDA SSURGO IA169 soil map unit (mukey), not individual polygon", 86, {"kind": "static"},
            ["data/source_packages/member4_v3/data_dictionary.md", "data/source_packages/member4_v3/reports/phase2_input_audit.md"], SOIL_WARNINGS),
    dataset("merra2_monthly_context_features", "data/processed/merra2/merra2_selected_monthly.csv",
            MERRA_COLUMNS, ["date", "latitude", "longitude"], "Source monthly mean × native grid cell",
            "Separate coarse MERRA-2 native cells; one latitude row and two longitudes", 422,
            {"start": "2008-06", "end": "2025-12", "months_per_cell": 211},
            ["data/processed/merra2/merra_extraction_report.md", "data/processed/merra2/merra2_final_readiness_audit.md",
             "data/processed/merra2/merra2_analysis_report.md"], MERRA_WARNINGS, optional=True),
]

for spec in DATASETS:
    name = spec["dataset_name"]
    if name.startswith("modis"):
        for field in spec["columns"]:
            if field.endswith(("_mean", "_median", "_std")):
                spec["validation"]["expected_missing_counts"][field] = 2 if "monthly" in name else 18
    if name == "soil_mapunit_features":
        for field in ("dominant_texture", "awc_weighted_cm_per_cm", "organic_matter_weighted_pct",
                      "dominant_drainage_class", "dominant_hydrologic_group"):
            spec["validation"]["expected_missing_counts"][field] = 9
        spec["validation"]["expected_missing_counts"]["slope_weighted_pct"] = 7
        spec["validation"]["expected_missing_counts"]["root_zone_aws_0_150cm_mm"] = 86
    if name.startswith("crop_"):
        spec["validation"]["percentage_tolerance_percentage_points"] = PCT_TOLERANCE
        spec["validation"]["denominator_ha_by_period"] = (
            {f"{a}->{b}": value for (a, b), value in TRANSITION_DENOMINATORS.items()}
            if name == "crop_transition_features"
            else {str(year): value for year, value in ANNUAL_DENOMINATORS.items()}
        )
        spec["validation"]["requirements"].append(
            "Per-year/per-pair denominators match documented values, area sums equal denominators, and every percentage recalculates within 0.000050001 percentage points.")


def row_schema(spec):
    """A standard JSON Schema for decoded CSV records plus explicit CSV metadata."""
    metadata = deepcopy({k: v for k, v in spec.items() if k != "columns"})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": spec["dataset_name"], "type": "object", "additionalProperties": False,
        "required": list(spec["columns"]), "properties": deepcopy(spec["columns"]),
        "x-dataset": metadata,
        "x-csv": {"encoding": "utf-8", "delimiter": ",", "ordered_columns": list(spec["columns"]),
                  "null_tokens": ["", "NULL"], "boolean_tokens": {"True": True, "False": False},
                  "decode_before_json_schema_validation": True,
                  "note": "NULL and empty cells decode to JSON null only in nullable fields. Identifiers such as mukey stay strings. Units=null means not applicable or not separately verified."},
    }
