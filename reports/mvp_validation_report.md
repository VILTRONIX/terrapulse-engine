# Phase 2A MVP Validation Report

**Status: PASS**

Reproduce with `.venv/bin/python -B -m src.validation.validate_mvp` from the repository root.

Validation uses only the existing Python environment and standard library. It reads CSVs and file bytes; no raster pixels or polygon overlays are processed.

## Package checks

Checks: required ordered columns, strict types, finite numerics and declared ranges, duplicate/non-null natural keys, exact date/year coverage, expected null counts, per-year/per-pair denominators, percentage arithmetic, source/output byte equality, manifest paths/metadata, JSON Schema contracts and SHA-256 hashes.

Protected original files checked against the pre-build baseline: **56**. This includes all original data, five rasters, the GeoPackage, boundary, dependencies, .gitignore and environment documents.

The schemas describe decoded JSON records. CSV null tokens are empty cells and `NULL`; `True`/`False` decode to booleans; `mukey` stays a string. The validator implements the contract keywords used here without adding a JSON Schema dependency.

## Dataset results

| Dataset | Status | Actual rows | Missing cells |
|---|---|---:|---:|
| nasa_power_monthly_features | PASS | 432 | 0 |
| modis_monthly_features | PASS | 108 | 12 |
| modis_16day_features | PASS | 207 | 108 |
| crop_annual_features | PASS | 15 | 0 |
| crop_class_annual_features | PASS | 156 | 0 |
| crop_transition_features | PASS | 36 | 0 |
| soil_mapunit_features | PASS | 86 | 138 |
| merra2_monthly_context_features | PASS | 422 | 0 |

## Cross-dataset checks

- Grouped annual crop areas match the detailed class table for every year and grouped class.
- Every common-valid transition denominator is bounded by both annual valid denominators.
- MODIS monthly counts and NDVI/EVI weighted means match all 207 source composites; pooled medians/std are preserved, not reconstructed.

## Crop denominator and rounding checks

Approved maximum absolute percentage error: **0.000050001 percentage points**. Existing percentages remain unchanged. Displayed percentage sums can differ slightly from 100 because individual source values are rounded.

| Dataset | Period | Denominator (ha) | Area sum (ha) | Percentage sum | Maximum error (percentage points) |
|---|---|---:|---:|---:|---:|
| crop_annual_features | 2021 | 148572.90 | 148572.9 | 100.0000 | 0.00002614171225034982826612 |
| crop_annual_features | 2022 | 148572.90 | 148572.90 | 100.0000 | 0.00003546016803872038575003 |
| crop_annual_features | 2023 | 148572.90 | 148572.90 | 100.0000 | 0.00002864169710626904368159 |
| crop_annual_features | 2024 | 148573.80 | 148573.80 | 100.0000 | 0.00004904229413261288329436 |
| crop_annual_features | 2025 | 148573.80 | 148573.80 | 100.0000 | 0.00001930676875734483468822 |
| crop_class_annual_features | 2021 | 148572.90 | 148572.90 | 100.0001 | 0.0000491916089677188773995796 |
| crop_class_annual_features | 2022 | 148572.90 | 148572.90 | 99.9999 | 0.0000469345351675843979622125 |
| crop_class_annual_features | 2023 | 148572.90 | 148572.90 | 99.9998 | 0.000048987466758742677836940653 |
| crop_class_annual_features | 2024 | 148573.80 | 148573.80 | 100.0002 | 0.00004904229413261288329436 |
| crop_class_annual_features | 2025 | 148573.80 | 148573.80 | 99.9999 | 0.0000470372299826752765292400 |
| crop_transition_features | (2021, 2022) | 148572.90 | 148572.90 | 99.9999 | 0.00004062611687595786310962 |
| crop_transition_features | (2022, 2023) | 148572.90 | 148572.90 | 100.0000 | 0.000048766968942519126974031 |
| crop_transition_features | (2023, 2024) | 148539.33 | 148539.33 | 100.0000 | 0.00004433710586953637127621 |
| crop_transition_features | (2024, 2025) | 148573.80 | 148573.80 | 100.0000 | 0.00003781878096945760288826 |

## Preserved missing values

- modis_monthly_features: `ndvi_mean` = 2; `ndvi_median` = 2; `ndvi_std` = 2; `evi_mean` = 2; `evi_median` = 2; `evi_std` = 2.
- modis_16day_features: `ndvi_mean` = 18; `ndvi_median` = 18; `ndvi_std` = 18; `evi_mean` = 18; `evi_median` = 18; `evi_std` = 18.
- soil_mapunit_features: `dominant_texture` = 9; `awc_weighted_cm_per_cm` = 9; `organic_matter_weighted_pct` = 9; `dominant_drainage_class` = 9; `dominant_hydrologic_group` = 9; `slope_weighted_pct` = 7; `root_zone_aws_0_150cm_mm` = 86.

## Warnings and limitations

- nasa_power_monthly_features: Selected points remain separate; monthly features reuse existing audited daily aggregates. Daily data is retained in its original location.
- modis_monthly_features: Use exact Story County pixel-center summaries only (37,193 pixels), not historical AOI/bounding-box summaries.
- modis_monthly_features: Monthly statistics pool valid pixel observations; means are weighted by valid pixel counts. Months 2019-02 and 2021-01 have no valid statistics.
- modis_monthly_features: Eighteen 16-day dates have no quality-passing pixels. December 2025 ends at the available 2025-12-19 observation; no interpolation.
- modis_monthly_features: MODIS vegetation indices describe county greenness, not crop-specific stress or field observations.
- modis_16day_features: Use exact Story County pixel-center summaries only (37,193 pixels), not historical AOI/bounding-box summaries.
- modis_16day_features: Monthly statistics pool valid pixel observations; means are weighted by valid pixel counts. Months 2019-02 and 2021-01 have no valid statistics.
- modis_16day_features: Eighteen 16-day dates have no quality-passing pixels. December 2025 ends at the available 2025-12-19 observation; no interpolation.
- modis_16day_features: MODIS vegetation indices describe county greenness, not crop-specific stress or field observations.
- crop_annual_features: Annual valid area is year-specific. Code 999 aggregates all classes other than Corn (1) and Soybeans (5); not a native CDL class.
- crop_class_annual_features: Preserve source CDL_Class_* label placeholders; not all class names are resolved. CDL 0 and 255 are excluded; source 2024–2025 products are harmonized to 30 m.
- crop_transition_features: Each year pair has its own common-valid denominator; county totals do not locate transitions or establish farm management history.
- soil_mapunit_features: Root-zone AWS is NULL for all 86 map units and must never be imputed.
- soil_mapunit_features: Texture, surface AWC, organic matter, drainage, and hydrologic group each have nine NULLs; slope has seven NULLs.
- soil_mapunit_features: Map units are soil survey units, not farm/field ownership boundaries. No map-unit crop statistics or geometry is delivered.
- merra2_monthly_context_features: Optional supporting context only; never a primary decision-driving source.
- merra2_monthly_context_features: Two coarse cells at latitude 42.0 and longitudes -93.75/-93.125 remain separate; not a county-wide average or field-scale surface.
- merra2_monthly_context_features: EVAP is not crop water demand, ETc, or irrigation requirement. EFLUX/HFLUX are not direct crop-stress measurements.
- merra2_monthly_context_features: TSH is absent; Var_TSH is excluded, never a temperature substitute. PRECCON/PRECSNO remain deferred.
- merra2_monthly_context_features: Coverage begins June 2008, so 2008 is partial. Signs and native flux-rate units are preserved; no flux conversions are added.

Local audits provide upstream raw-data and spatial-method evidence. This run validates the delivered tables and preservation of local inputs; it does not independently repeat raw NetCDF extraction, pixel-level masking, or USDA spatial extraction.

## Unresolved failures

None. All seven required tables and the included optional table pass the checks above.

Phase 2A ends at this handoff. Phase 2B spatial features, recommendations, APIs and UI are deferred.
