# Phase 2A Delivery Summary

Package validation: **PASS**. Regression tests: **16 passed**. Repeated builds produce identical generated artifact hashes. All **56 protected original files** match the pre-build SHA-256 baseline. No unresolved validation failures.

All seven required feature tables and optional MERRA-2 context are present, along with eight JSON schemas, the manifest, reproducible build/validation code, input inventory/audit, dictionary, and Backend handoff.

## Delivered data

| File | Actual rows |
|---|---:|
| `data/processed/features/nasa_power_monthly_features.csv` | 432 |
| `data/processed/features/modis_monthly_features.csv` | 108 |
| `data/processed/features/modis_16day_features.csv` | 207 |
| `data/processed/features/crop_annual_features.csv` | 15 |
| `data/processed/features/crop_class_annual_features.csv` | 156 |
| `data/processed/features/crop_transition_features.csv` | 36 |
| `data/processed/features/soil_mapunit_features.csv` | 86 |
| `data/processed/features/merra2_monthly_context_features.csv` | 422 |

All feature definitions, verified units, grains, keys and null policies are in [feature_dictionary.md](../docs/feature_dictionary.md); [engine_handoff.md](../docs/engine_handoff.md) explains Backend consumption. Validation evidence is in [mvp_validation_report.md](mvp_validation_report.md) and [mvp_validation_results.json](mvp_validation_results.json).

## Warnings and limits

- MODIS retains 18 empty composite dates and two empty months (2019-02 and 2021-01). December 2025 observations end December 19. Exact county pixel-center summaries are used.
- Root-zone AWS remains NULL for all 86 map units. Other documented soil nulls are preserved. Some detailed CDL class names retain source placeholders.
- MERRA-2 remains optional coarse-cell context with separate longitudes. EVAP is not crop water demand or irrigation requirement. TSH is absent; Var_TSH is excluded; PRECCON/PRECSNO remain deferred.
- Spatial correctness and upstream raw extraction are supported by the existing local audits; this MVP does not repeat NetCDF extraction or raster/polygon processing. No recommendation formulas, Backend APIs, or Frontend functionality are included.

## Exact reproduction commands

Run from the repository root:

```bash
.venv/bin/python -B -m src.features.build_mvp
.venv/bin/python -B -m src.validation.validate_mvp
.venv/bin/python -B -m unittest discover -s tests -p 'test_phase2a_validation.py' -v
```

The existing virtual environment and dependency files are unchanged. Source copies preserve bytes, dates, precision, null markers and order. Keep the pre-build source inventory for subsequent validation.

## Git status and file changes

No tracked files were modified. **28 new Phase 2A files are untracked**. The 51 original data files were already untracked at task start and remain unchanged. No Git initialization, commits, staging, or pushes were performed.

Created files (complete list):

- `data/processed/features/crop_annual_features.csv`
- `data/processed/features/crop_class_annual_features.csv`
- `data/processed/features/crop_transition_features.csv`
- `data/processed/features/feature_manifest.json`
- `data/processed/features/merra2_monthly_context_features.csv`
- `data/processed/features/modis_16day_features.csv`
- `data/processed/features/modis_monthly_features.csv`
- `data/processed/features/nasa_power_monthly_features.csv`
- `data/processed/features/soil_mapunit_features.csv`
- `docs/engine_handoff.md`
- `docs/feature_dictionary.md`
- `reports/mvp_validation_report.md`
- `reports/mvp_validation_results.json`
- `reports/phase2a_delivery_summary.md`
- `reports/phase2a_input_audit.json`
- `reports/phase2a_source_inventory.json`
- `src/features/build_mvp.py`
- `src/features/phase2a_contracts.py`
- `src/schemas/crop_annual_features.schema.json`
- `src/schemas/crop_class_annual_features.schema.json`
- `src/schemas/crop_transition_features.schema.json`
- `src/schemas/merra2_monthly_context_features.schema.json`
- `src/schemas/modis_16day_features.schema.json`
- `src/schemas/modis_monthly_features.schema.json`
- `src/schemas/nasa_power_monthly_features.schema.json`
- `src/schemas/soil_mapunit_features.schema.json`
- `src/validation/validate_mvp.py`
- `tests/test_phase2a_validation.py`

No existing files were modified. Phase 2A is complete; Phase 2B was not started.
