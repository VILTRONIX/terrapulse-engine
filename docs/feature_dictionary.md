# Phase 2A Feature Dictionary

Generated from the reviewed contracts in `src/features/phase2a_contracts.py`. All delivered data values are unchanged source values; this MVP adds no indicators.

JSON schemas describe decoded CSV rows. Read `mukey` as a string; decode empty cells and literal `NULL` as missing only in declared nullable fields; decode `True`/`False` as booleans. Every column is required in the CSV, including nullable columns. A unit of `—` means not applicable or not separately verified; no unit is inferred for an identifier.

Natural keys are unique within each table's declared Story County or source spatial scope. County GEOID `19169` is contract metadata, not an added CSV column. Never join different grains by row order.

## nasa_power_monthly_features

- File: `data/processed/features/nasa_power_monthly_features.csv` (432 rows).
- Source: `data/processed/nasa_power/power_monthly_by_location.csv`; byte-for-byte copy.
- Key: `location_id, year, month`.
- Temporal grain: Calendar month at each representative point.
- Spatial grain: Four separate NASA POWER representative points; not a county average.
- Coverage: `{"start": "2017-01", "end": "2025-12", "months_per_point": 108}`.
- Contract: `src/schemas/nasa_power_monthly_features.schema.json`.

| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |
|---|---|---|---|---:|---|
| `location_id` | string | — | no | 0 | Selected NASA POWER representative point identifier. |
| `latitude` | number | degrees_north | no | 0 | Source point latitude, north positive. |
| `longitude` | number | degrees_east | no | 0 | Source point longitude, east positive. |
| `year` | integer | — | no | 0 | Calendar year. |
| `month` | integer | — | no | 0 | Calendar month number. |
| `month_start` | string | — | no | 0 | First calendar date of the represented month. |
| `month_end` | string | — | no | 0 | Last calendar date of the represented month. |
| `days_expected` | integer | days | no | 0 | Calendar days expected in the month. |
| `days_present` | integer | days | no | 0 | Source daily records present in the month. |
| `complete` | boolean | — | no | 0 | True when days_present equals days_expected. |
| `T2M_mean` | number | C | no | 0 | Monthly arithmetic mean of daily 2 m temperature. |
| `T2M_MAX_mean` | number | C | no | 0 | Monthly arithmetic mean of daily maximum 2 m temperature. |
| `T2M_MIN_mean` | number | C | no | 0 | Monthly arithmetic mean of daily minimum 2 m temperature. |
| `PRECTOTCORR_total` | number | mm | no | 0 | Sum of daily corrected precipitation amounts over the calendar month. |
| `PRECTOTCORR_daily_mean` | number | mm/day | no | 0 | Arithmetic mean of daily corrected precipitation. |
| `ALLSKY_SFC_SW_DWN_total` | number | MJ/m^2 | no | 0 | Sum of daily all-sky surface shortwave irradiation over the month. |
| `ALLSKY_SFC_SW_DWN_daily_mean` | number | MJ/m^2/day | no | 0 | Arithmetic mean of daily all-sky surface shortwave irradiation. |
| `RH2M_mean` | number | % | no | 0 | Monthly arithmetic mean of daily relative humidity at 2 m. |

- Selected points remain separate; monthly features reuse existing audited daily aggregates. Daily data is retained in its original location.

## modis_monthly_features

- File: `data/processed/features/modis_monthly_features.csv` (108 rows).
- Source: `data/processed/modis/modis_monthly_story_county_summary.csv`; byte-for-byte copy.
- Key: `month`.
- Temporal grain: Calendar month of available 16-day observations.
- Spatial grain: Exact Story County pixel-center mask; pooled quality-passing pixel observations.
- Coverage: `{"start": "2017-01", "end": "2025-12"}`.
- Contract: `src/schemas/modis_monthly_features.schema.json`.

| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |
|---|---|---|---|---:|---|
| `month` | string | — | no | 0 | Calendar month label of the contributing 16-day observation dates. |
| `observation_count` | integer | observations | no | 0 | Number of contributing 16-day source observations. |
| `total_pixel_observations` | integer | pixel observations | no | 0 | 37,193 county pixel centers × observation_count. |
| `ndvi_mean` | number | dimensionless | yes | 2 | NDVI mean over quality-passing county pixel observations; already scaled. |
| `ndvi_median` | number | dimensionless | yes | 2 | NDVI median over quality-passing county pixel observations; already scaled. |
| `ndvi_std` | number | dimensionless | yes | 2 | NDVI std over quality-passing county pixel observations; already scaled. |
| `ndvi_valid_pixel_count` | integer | pixel observations | no | 0 | Quality-passing pixel observations contributing to this index. |
| `ndvi_valid_pixel_percentage` | number | % | no | 0 | 100 × valid pixel observations / total pixel observations. |
| `evi_mean` | number | dimensionless | yes | 2 | EVI mean over quality-passing county pixel observations; already scaled. |
| `evi_median` | number | dimensionless | yes | 2 | EVI median over quality-passing county pixel observations; already scaled. |
| `evi_std` | number | dimensionless | yes | 2 | EVI std over quality-passing county pixel observations; already scaled. |
| `evi_valid_pixel_count` | integer | pixel observations | no | 0 | Quality-passing pixel observations contributing to this index. |
| `evi_valid_pixel_percentage` | number | % | no | 0 | 100 × valid pixel observations / total pixel observations. |

- Use exact Story County pixel-center summaries only (37,193 pixels), not historical AOI/bounding-box summaries.
- Monthly statistics pool valid pixel observations; means are weighted by valid pixel counts. Months 2019-02 and 2021-01 have no valid statistics.
- Eighteen 16-day dates have no quality-passing pixels. December 2025 ends at the available 2025-12-19 observation; no interpolation.
- MODIS vegetation indices describe county greenness, not crop-specific stress or field observations.

## modis_16day_features

- File: `data/processed/features/modis_16day_features.csv` (207 rows).
- Source: `data/processed/modis/modis_16day_story_county_summary.csv`; byte-for-byte copy.
- Key: `date`.
- Temporal grain: Source 16-day composite observation date.
- Spatial grain: Exact Story County pixel-center mask; 37,193 county pixel centers.
- Coverage: `{"start": "2017-01-01", "end": "2025-12-19", "observations_per_year": 23}`.
- Contract: `src/schemas/modis_16day_features.schema.json`.

| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |
|---|---|---|---|---:|---|
| `date` | string | — | no | 0 | Source observation date (ISO calendar date). |
| `ndvi_mean` | number | dimensionless | yes | 18 | NDVI mean over quality-passing county pixel observations; already scaled. |
| `ndvi_median` | number | dimensionless | yes | 18 | NDVI median over quality-passing county pixel observations; already scaled. |
| `ndvi_std` | number | dimensionless | yes | 18 | NDVI std over quality-passing county pixel observations; already scaled. |
| `ndvi_valid_pixel_count` | integer | pixel observations | no | 0 | Quality-passing pixel observations contributing to this index. |
| `ndvi_valid_pixel_percentage` | number | % | no | 0 | 100 × valid pixel observations / total pixel observations. |
| `evi_mean` | number | dimensionless | yes | 18 | EVI mean over quality-passing county pixel observations; already scaled. |
| `evi_median` | number | dimensionless | yes | 18 | EVI median over quality-passing county pixel observations; already scaled. |
| `evi_std` | number | dimensionless | yes | 18 | EVI std over quality-passing county pixel observations; already scaled. |
| `evi_valid_pixel_count` | integer | pixel observations | no | 0 | Quality-passing pixel observations contributing to this index. |
| `evi_valid_pixel_percentage` | number | % | no | 0 | 100 × valid pixel observations / total pixel observations. |
| `total_pixel_count` | integer | pixels | no | 0 | Pixel centers strictly within the Story County polygon. |
| `base_valid_pixel_count` | integer | pixels | no | 0 | Valid NDVI/EVI pixel pairs before quality filtering. |
| `quality_valid_pixel_count` | integer | pixels | no | 0 | Base-valid pixel pairs passing reliability=0 and MODLAND QA=0. |
| `vi_usefulness_distribution_before_filter` | string | — | no | 0 | JSON object mapping VI usefulness codes (bits 2–5) to base-valid pixel counts; no usefulness threshold applied. |
| `vi_usefulness_distribution_after_filter` | string | — | no | 0 | JSON object mapping VI usefulness codes to quality-passing pixel counts. |

- Use exact Story County pixel-center summaries only (37,193 pixels), not historical AOI/bounding-box summaries.
- Monthly statistics pool valid pixel observations; means are weighted by valid pixel counts. Months 2019-02 and 2021-01 have no valid statistics.
- Eighteen 16-day dates have no quality-passing pixels. December 2025 ends at the available 2025-12-19 observation; no interpolation.
- MODIS vegetation indices describe county greenness, not crop-specific stress or field observations.

## crop_annual_features

- File: `data/processed/features/crop_annual_features.csv` (15 rows).
- Source: `data/source_packages/member4_v3/tables/crop_area_by_year.csv`; byte-for-byte copy.
- Key: `year, crop_code`.
- Temporal grain: Calendar year × grouped crop class (Corn/Soybeans/Other).
- Spatial grain: Story County annual valid CDL mask; county totals.
- Coverage: `{"start_year": 2021, "end_year": 2025}`.
- Contract: `src/schemas/crop_annual_features.schema.json`.

| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |
|---|---|---|---|---:|---|
| `year` | integer | — | no | 0 | Calendar year. |
| `crop_code` | integer | — | no | 0 | USDA CDL class code; 999 means aggregated Other only in the grouped table. |
| `crop_name` | string | — | no | 0 | Source crop/land-cover label; CDL_Class_* placeholders are preserved. |
| `area_ha` | number | ha | no | 0 | Area of this crop class or transition. |
| `area_pct` | number | % | no | 0 | 100 × area_ha / the row's applicable denominator; source rounded to four decimals. |
| `valid_denominator_ha` | number | ha | no | 0 | Year-specific valid county area excluding CDL 0 and 255. |
| `source` | string | — | no | 0 | Unchanged source provenance label. |

- Annual valid area is year-specific. Code 999 aggregates all classes other than Corn (1) and Soybeans (5); not a native CDL class.

## crop_class_annual_features

- File: `data/processed/features/crop_class_annual_features.csv` (156 rows).
- Source: `data/source_packages/member4_v3/tables/crop_class_area_by_year.csv`; byte-for-byte copy.
- Key: `year, crop_code`.
- Temporal grain: Calendar year × original CDL crop/land-cover class.
- Spatial grain: Story County annual valid CDL mask; county totals.
- Coverage: `{"start_year": 2021, "end_year": 2025}`.
- Contract: `src/schemas/crop_class_annual_features.schema.json`.

| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |
|---|---|---|---|---:|---|
| `year` | integer | — | no | 0 | Calendar year. |
| `crop_code` | integer | — | no | 0 | USDA CDL class code; 999 means aggregated Other only in the grouped table. |
| `crop_name` | string | — | no | 0 | Source crop/land-cover label; CDL_Class_* placeholders are preserved. |
| `pixel_count` | integer | pixels | no | 0 | Valid classified 30 × 30 m pixels in this class; one pixel = 0.09 ha. |
| `area_ha` | number | ha | no | 0 | Area of this crop class or transition. |
| `area_pct` | number | % | no | 0 | 100 × area_ha / the row's applicable denominator; source rounded to four decimals. |
| `valid_denominator_ha` | number | ha | no | 0 | Year-specific valid county area excluding CDL 0 and 255. |
| `source` | string | — | no | 0 | Unchanged source provenance label. |

- Preserve source CDL_Class_* label placeholders; not all class names are resolved. CDL 0 and 255 are excluded; source 2024–2025 products are harmonized to 30 m.

## crop_transition_features

- File: `data/processed/features/crop_transition_features.csv` (36 rows).
- Source: `data/source_packages/member4_v3/tables/crop_transitions.csv`; byte-for-byte copy.
- Key: `year_1, year_2, transition_type`.
- Temporal grain: Consecutive year pair × directed grouped transition.
- Spatial grain: Story County common-valid CDL mask for each year pair; county totals.
- Coverage: `{"year_pairs": [[2021, 2022], [2022, 2023], [2023, 2024], [2024, 2025]]}`.
- Contract: `src/schemas/crop_transition_features.schema.json`.

| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |
|---|---|---|---|---:|---|
| `year_1` | integer | — | no | 0 | Calendar year. |
| `year_2` | integer | — | no | 0 | Calendar year. |
| `transition_type` | string | — | no | 0 | Directed grouped transition label (Corn/Soybeans/Other -> Corn/Soybeans/Other). |
| `area_ha` | number | ha | no | 0 | Area of this crop class or transition. |
| `area_pct` | number | % | no | 0 | 100 × area_ha / the row's applicable denominator; source rounded to four decimals. |
| `common_valid_area_ha` | number | ha | no | 0 | Pair-specific county area valid in both consecutive years, excluding CDL 0 and 255. |

- Each year pair has its own common-valid denominator; county totals do not locate transitions or establish farm management history.

## soil_mapunit_features

- File: `data/processed/features/soil_mapunit_features.csv` (86 rows).
- Source: `data/source_packages/member4_v3/soil/soil_summary.csv`; byte-for-byte copy.
- Key: `mukey`.
- Temporal grain: Static source soil attribute lookup; no observation year assigned.
- Spatial grain: USDA SSURGO IA169 soil map unit (mukey), not individual polygon.
- Coverage: `{"kind": "static"}`.
- Contract: `src/schemas/soil_mapunit_features.schema.json`.

| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |
|---|---|---|---|---:|---|
| `mukey` | string | — | no | 0 | Stable USDA SSURGO map-unit join key; load as a string. |
| `musym` | string | — | no | 0 | Map-unit symbol. |
| `muname` | string | — | no | 0 | Official map-unit name. |
| `dominant_texture` | string | — | yes | 9 | Dominant surface-horizon (0 cm) soil texture. |
| `awc_weighted_cm_per_cm` | number | cm/cm | yes | 9 | Component-weighted surface-horizon available water capacity; not root-zone storage or current moisture. |
| `organic_matter_weighted_pct` | number | % | yes | 9 | Component-weighted surface-horizon organic matter. |
| `dominant_drainage_class` | string | — | yes | 9 | Dominant soil drainage class. |
| `dominant_hydrologic_group` | string | — | yes | 9 | Dominant hydrologic soil group. |
| `slope_weighted_pct` | number | % | yes | 7 | Component-weighted representative slope (percent rise; may exceed 100). |
| `total_component_pct_accounted` | integer | % | no | 0 | Source component coverage percentage; retained as a quality/context field. |
| `source` | string | — | no | 0 | Unchanged source provenance label. |
| `root_zone_aws_0_150cm_mm` | number | mm | yes | 86 | NRCS muaggatt.aws0_150wta, 0–150 cm root-zone available water storage; unavailable for all 86 records; never impute. |

- Root-zone AWS is NULL for all 86 map units and must never be imputed.
- Texture, surface AWC, organic matter, drainage, and hydrologic group each have nine NULLs; slope has seven NULLs.
- Map units are soil survey units, not farm/field ownership boundaries. No map-unit crop statistics or geometry is delivered.

## merra2_monthly_context_features

- File: `data/processed/features/merra2_monthly_context_features.csv` (422 rows).
- Source: `data/processed/merra2/merra2_selected_monthly.csv`; byte-for-byte copy.
- Key: `date, latitude, longitude`.
- Temporal grain: Source monthly mean × native grid cell.
- Spatial grain: Separate coarse MERRA-2 native cells; one latitude row and two longitudes.
- Coverage: `{"start": "2008-06", "end": "2025-12", "months_per_cell": 211}`.
- Contract: `src/schemas/merra2_monthly_context_features.schema.json`.

| Column | Decoded type | Unit | Nullable | Preserved missing rows | Definition |
|---|---|---|---|---:|---|
| `date` | string | — | no | 0 | First-of-month label for the source monthly mean; local audit reports original NetCDF timestamp at 00:30, absent from CSV. |
| `latitude` | number | degrees_north | no | 0 | Native coarse-grid latitude, north positive. |
| `longitude` | number | degrees_east | no | 0 | Native coarse-grid longitude, east positive; keep both cells separate. |
| `SPEED` | number | m s-1 | no | 0 | Monthly mean surface wind speed; height not separately verified as 10 m. |
| `EVAP` | number | kg m-2 s-1 | no | 0 | Monthly mean evaporation_from_turbulence; signs preserved; not crop water demand, ETc, or irrigation requirement. |
| `EFLUX` | number | W m-2 | no | 0 | Monthly mean total_latent_energy_flux; source signs retained without reassignment. |
| `HFLUX` | number | W m-2 | no | 0 | Monthly mean sensible_heat_flux_from_turbulence; source signs retained without reassignment. |

- Optional supporting context only; never a primary decision-driving source.
- Two coarse cells at latitude 42.0 and longitudes -93.75/-93.125 remain separate; not a county-wide average or field-scale surface.
- EVAP is not crop water demand, ETc, or irrigation requirement. EFLUX/HFLUX are not direct crop-stress measurements.
- TSH is absent; Var_TSH is excluded, never a temperature substitute. PRECCON/PRECSNO remain deferred.
- Coverage begins June 2008, so 2008 is partial. Signs and native flux-rate units are preserved; no flux conversions are added.

## Denominators and time support

Annual valid area: 148,572.90 ha in 2021–2023; 148,573.80 ha in 2024–2025. Each annual table partitions its own year's valid area. Exclude CDL 0 and 255.

Transition common-valid area: 148,572.90 ha for 2021→2022 and 2022→2023; 148,539.33 ha for 2023→2024; 148,573.80 ha for 2024→2025. Each pair partitions only area valid in both years.

Every source `area_pct` is preserved. QA recomputes `100 × area_ha / denominator` using an absolute tolerance of 0.000050001 percentage points. Do not replace denominators with a fixed county area or use relative percent tolerance.

MODIS monthly means pool valid pixel observations (valid-count weighted), while medians and standard deviations use the original pooled pixels. Monthly statistics are preserved; the validator can reproduce means and counts from composites, but cannot reconstruct pooled medians/std from summaries alone.

NASA POWER monthly radiation totals have units MJ/m² over the represented month, and precipitation totals have units mm over that month; daily means retain MJ/m²/day and mm/day. The source daily parameter units and existing monthly aggregation definitions establish these units.

MERRA-2 keeps native monthly-mean rates and energy fluxes from the selected-variable CSV. Existing duration-converted analysis, seasonal, and annual products remain in their original directory and are outside the MVP consumption manifest.
