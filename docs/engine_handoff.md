# TerraPulse Engine — Phase 2A Backend Handoff

Phase 2A provides eight validated feature CSVs: seven required tables and optional MERRA-2 context. They contain unchanged values from existing local products. The Engine supplies traceable data and contracts for Story County, Iowa (GEOID `19169`). Application development belongs to the Backend and Frontend teams.

Start with [feature_manifest.json](../data/processed/features/feature_manifest.json). Consume only its `datasets` entries. Each entry contains actual row count, file/schema/source paths, SHA-256 fingerprints, natural key, grains, coverage, nullable fields and provenance. A missing or invalid input is listed in `unavailable_datasets`; it never receives a manifest consumption path. Missing required datasets produce a failing validation exit status while the remaining valid datasets are still built. An optional omission alone does not fail an otherwise complete package.

## Files to consume

All files below are under `data/processed/features/`. Natural keys apply within each table's declared source/county scope. County scope is contract metadata; it has not been added as a CSV column.

| CSV | Actual rows | Natural key | Grain and coverage |
|---|---:|---|---|
| `nasa_power_monthly_features.csv` | 432 | `location_id, year, month` | Four separate representative points × calendar month; Jan 2017–Dec 2025, 108 months per point |
| `modis_monthly_features.csv` | 108 | `month` | Exact Story County pixel-center mask × month of available composite observations; Jan 2017–Dec 2025 |
| `modis_16day_features.csv` | 207 | `date` | Exact Story County pixel-center mask × source composite date; Jan 1, 2017–Dec 19, 2025 |
| `crop_annual_features.csv` | 15 | `year, crop_code` | Story County × year × grouped Corn/Soybeans/Other; 2021–2025 |
| `crop_class_annual_features.csv` | 156 | `year, crop_code` | Story County × year × native CDL class; 2021–2025 |
| `crop_transition_features.csv` | 36 | `year_1, year_2, transition_type` | Story County × consecutive year pair × directed grouped transition; 2021→2022 through 2024→2025, nine types per pair |
| `soil_mapunit_features.csv` | 86 | `mukey` | Static SSURGO IA169 map-unit attribute lookup; no observation year assigned |
| `merra2_monthly_context_features.csv` | 422 | `date, latitude, longitude` | Optional separate coarse native cells × monthly mean; Jun 2008–Dec 2025, 211 months per cell |

Each table has a matching `src/schemas/<dataset_name>.schema.json`. These are JSON Schema Draft 2020-12 contracts for **decoded records**; they include ordered CSV columns, primitive types, units, null policy, provenance, coverage and validation requirements. [feature_dictionary.md](feature_dictionary.md) explains every delivered column and unit. Keep schemas, manifest and CSVs together when handing off a snapshot.

## Loading rules

CSV encoding is UTF-8. Preserve identifiers, timestamps, source labels, numeric precision and record order. Interpret empty cells and literal `NULL` as missing in declared nullable fields. `True` and `False` are the boolean spellings in the source CSV. In particular, load `mukey` as a string even though all current keys contain digits. Do not send the literal string `NULL` as a numeric soil value.

For pandas consumers, this preserves the soil join key and null policy:

```python
import pandas as pd

soil = pd.read_csv(
    "data/processed/features/soil_mapunit_features.csv",
    dtype={"mukey": "string"},
    keep_default_na=False,
    na_values=["", "NULL"],
)
```

The source GeoPackage can be joined using `mukey`; it contains 39,591 polygons but only 86 distinct map units. This MVP delivers the attribute lookup without spatial crop extraction. Soil polygons are survey units, not farm boundaries.

POWER locations remain four separate points. MODIS tables are county summaries. Crop tables are county summaries with annual or common-valid masks. MERRA-2 retains two coarse cells. Joining these on time alone can multiply records and does not create matching spatial support. Keep these tables separate unless the consuming team explicitly defines a scientifically valid comparison.

## Definitions and scientific limits

- NASA POWER: existing monthly temperature means (`C`), relative humidity (`%`), corrected precipitation total (`mm`) and daily mean (`mm/day`), shortwave irradiation total (`MJ/m^2`) and daily mean (`MJ/m^2/day`). These reuse the audited monthly table; the 13,148 daily rows remain in the original source directory for future work.
- MODIS: scaled, dimensionless NDVI/EVI mean, median and standard deviation, with valid pixel counts, percentages and QA context. The exact mask includes 37,193 pixel centers strictly inside Story County. QA requires Pixel Reliability = 0 and MODLAND QA bits 0–1 = 0; VI usefulness is retained without an added threshold. Monthly means pool valid pixel observations. Monthly and 16-day data stay separate; never apply the 0.0001 scale factor again.
- Crops: class areas (`ha`), shares (`%`), valid annual area (`ha`) and detailed class pixel counts. A 30 m pixel corresponds to 0.09 ha. Grouped class `999` means Other, while detailed native codes and source `CDL_Class_*` placeholder names remain unchanged. The local manifest documents 2024–2025 source harmonization to the 30 m grid.
- Transitions: county aggregate areas (`ha`) and shares (`%`) relative to each pair's common-valid area (`ha`). They do not locate changed pixels or establish farm rotation practices.
- Soil: component-weighted surface AWC (`cm/cm`), surface organic matter (`%`), slope (`%`), component coverage (`%`), texture, drainage and hydrologic group. Root-zone AWS (`mm`, 0–150 cm) is unavailable for all 86 records and must never be imputed. Surface AWC cannot replace missing root-zone storage or current moisture.
- MERRA-2: monthly means of `SPEED` (`m s-1`), `EVAP` (`kg m-2 s-1`), `EFLUX` and `HFLUX` (`W m-2`). The minimal selected-variable CSV was chosen over the analysis CSV to retain native variables without introducing duration-converted totals into the MVP. Latitude is 42.0; longitudes -93.75 and -93.125 remain separate. This is supporting context, not a county-wide average or a primary decision source. EVAP is not crop demand, ETc or irrigation requirement. Surface wind height has not been separately verified as 10 m. Flux signs are preserved without reassignment. TSH is absent; Var_TSH, PRECCON and PRECSNO are excluded/deferred.

Annual crop denominators are 148,572.90 ha for 2021–2023 and 148,573.80 ha for 2024–2025. Transition denominators are 148,572.90 ha for 2021→2022 and 2022→2023, 148,539.33 ha for 2023→2024, and 148,573.80 ha for 2024→2025. Source percentages remain unchanged. QA uses an absolute tolerance of **0.000050001 percentage points**; a small difference from a displayed sum of 100% is expected from rounding.

MODIS statistics are missing for 2019-02 and 2021-01 and for 18 source composite dates. December 2025 contains available observations through December 19 and has very low valid coverage; its monthly label does not claim complete observation through December 31. Soil texture, AWC, organic matter, drainage and hydrologic group each have nine missing records; slope has seven; root-zone AWS has 86. These gaps are retained without interpolation or substitution. MERRA-2 coverage starts in June 2008, making 2008 partial.

## Reproduction and validation

From the existing repository root, use the existing environment only:

```bash
.venv/bin/python -B -m src.features.build_mvp
.venv/bin/python -B -m src.validation.validate_mvp
.venv/bin/python -B -m unittest discover -s tests -p 'test_phase2a_validation.py' -v
```

The build copies individually valid inputs, emits schemas/manifest/dictionary/input audit, and runs package validation. Validation can also run independently and returns exit code `0` on success and `1` for unresolved failures. It writes [mvp_validation_report.md](../reports/mvp_validation_report.md) and machine-readable [mvp_validation_results.json](../reports/mvp_validation_results.json). `-B` avoids creating bytecode cache artifacts; no dependency installation is needed.

Contracts in `src/features/phase2a_contracts.py` define this fixed snapshot's coverage, counts, nullable fields, units and approved denominators. A future data refresh requires a reviewed contract change; the builder deliberately does not silently adapt contracts to changed inputs. The builder removes only a known generated CSV/schema when its input becomes invalid, so stale outputs cannot appear current. Other valid datasets continue to build.

[phase2a_source_inventory.json](../reports/phase2a_source_inventory.json) holds the pre-build baseline for 56 original files, including every existing data file, source rasters/GeoPackage, dependency specifications, .gitignore and environment documents. Keep this baseline: reruns verify it rather than replacing it. Changes or deletion of protected inputs fail validation. On a genuinely fresh checkout without a baseline, the first build captures one before writing outputs. [phase2a_input_audit.json](../reports/phase2a_input_audit.json) records original CSV headers, row counts, inferred types, missing counts, distinct values and ranges, including the daily and existing analysis products that were not selected for copying.

The validator checks exact schemas/manifest metadata, paths and hashes; ordered columns and strict types; finite numerics and ranges; natural keys; calendar/date/year coverage; documented missing counts; annual and transition denominator consistency; all source percentages within the approved rounding tolerance; source-to-output byte equality; crop summary agreement; and MODIS monthly counts and valid-count-weighted means. Pooled MODIS medians/std cannot be reconstructed from per-date summaries and remain traceable to the preserved source values. Upstream raw extraction and spatial correctness rely on the supplied local audits; this run does not repeat raw NetCDF or spatial processing.

## Deferred after this handoff

Phase 2B includes any raster/polygon overlays, map-unit crop statistics, pixel-level transition locations and soil/crop spatial features. Crop recommendation formulas, scenario scores, yield/economic estimates, crop-specific stress indicators, irrigation demand and soil water storage imputation are not delivered. No Backend API, Frontend implementation, downloads, environment changes, Git commits or pushes were performed. Phase 2A stops here.
