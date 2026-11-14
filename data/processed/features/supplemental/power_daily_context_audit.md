# NASA POWER Daily Weather Supplement Audit

**Validation: PASS**

Existing daily data was inspected but not reused: four distinct points each have 1,826 dates in 2021–2025, but none is the requested point; WS10M and PS are absent. Fourteen original weather exports were inspected read-only and have the same parameter/location gaps. Details and original headers/checksums are in `input_inspection.json`.

One new NASA POWER Daily Point CSV request was necessary. No alternate datasets were downloaded. The endpoint URL was not included in the task text; the official documented endpoint was used.

Source URL: https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M_MAX%2CT2M_MIN%2CT2M%2CRH2M%2CWS10M%2CALLSKY_SFC_SW_DWN%2CPRECTOTCORR%2CPS%2CT2MDEW&community=AG&latitude=42.0375&longitude=-93.4661&start=20210101&end=20251231&format=CSV&time-standard=UTC

Retrieved at (UTC): 2026-11-14T02:52:01.878842+00:00

Requested and header-returned coordinates: latitude 42.0375, longitude -93.4661. They are stored separately in metadata. Actual contributing grid centers are not supplied by the CSV. This is a native-resolution point request, not a county spatial average or field measurement.

Records: **1826**; inclusive coverage 2021-01-01 through 2025-12-31, UTC. Missing dates: 0; duplicate dates: 0; unexpected dates: 0.

| Parameter | NASA header unit | Minimum | Maximum | Missing | Fill | Outside screen |
|---|---|---:|---:|---:|---:|---:|
| T2M_MAX | C | -20.13 | 40.22 | 0 | 0 | 0 |
| T2M_MIN | C | -29.08 | 27.35 | 0 | 0 | 0 |
| T2M | C | -24.5 | 31.58 | 0 | 0 | 0 |
| RH2M | % | 36.42 | 99.63 | 0 | 0 | 0 |
| WS10M | m/s | 1.0 | 14.66 | 0 | 0 | 0 |
| ALLSKY_SFC_SW_DWN | MJ/m^2/day | 0.92 | 31.56 | 0 | 0 | 0 |
| PRECTOTCORR | mm/day | 0.0 | 55.99 | 0 | 0 | 0 |
| PS | kPa | 95.21 | 100.02 | 0 | 0 | 0 |
| T2MDEW | C | -26.36 | 25.36 | 0 | 0 | 0 |

Ranges are broad plausibility screens documented in metadata, not NASA product valid-range limits. Numeric finiteness, Tmin ≤ Tmean ≤ Tmax, YEAR/DOY validity, complete chronological calendar, parameter units, coordinates, retrieval identity/time and checksums are checked. No values are clipped or imputed. Optional T2MDEW was supported and is labelled Dew/Frost Point at 2 Meters (C).

Preservation: all 84 pre-existing workspace files match the pre-download baseline, including Phase 2A tables, schemas, manifest and reports. The four existing POWER point identities remain unchanged.

## Backend consumption

Use `power_daily_context.csv` with `power_daily_context_metadata.json`. Key: date within this fixed single-point dataset. All columns are required; YEAR/DOY are integers, date is ISO text, coordinates and weather values are numeric. Source missing/fill markers remain missing under the documented policy. This supplement has no registration in the unchanged Phase 2A manifest.

## FAO-56 ET0 readiness

Conditionally supports a future FAO-56 daily ET0 implementation; no ET0 calculated.

- Daily Tmin/Tmax/Tmean in C, RHmean in %, WS10M in m/s, incoming solar radiation in MJ/m^2/day, pressure in kPa, date and latitude.
- Optional T2MDEW is returned in C, explicitly labelled Dew/Frost Point, with no missing cells.
- Header reports MERRA-2 grid-average elevation 310.22 m; this is not surveyed point elevation.
- Convert 10 m wind to 2 m wind using FAO-56 Eq. 47 and its reference-surface assumptions; do not use WS10M directly as u2.
- Incoming shortwave Rs is not net radiation Rn. Derive net shortwave with reference-grass albedo 0.23 and estimate net longwave with documented FAO-56 assumptions.
- Clear-sky radiation needs an elevation choice. Surveyed point elevation is absent; explicitly approve the supplied coarse grid-average elevation or supply a validated point elevation in a separate task. Do not silently reinterpret it.
- RHmax/RHmin are absent. Evaluate a daily mean dew/frost-point vapour-pressure method (including freezing conventions and nonlinear daily averaging) or the less preferred RHmean method; do not invent RH extrema.
- Use validated PS in kPa for the psychrometric constant; no pressure unit conversion is needed.
- Document daily soil heat flux G≈0, extraterrestrial radiation from latitude/day-of-year, reference grass assumptions and consistency of UTC daily aggregates with FAO daily procedures.
- Reanalysis and satellite point-request values retain native spatial support, not field measurements; validate future ET0 implementation and missing-data handling before use.

ET0 is conditional on those explicit method/elevation decisions. No missing inputs are fabricated. No ET0, ETc, irrigation demand or crop water savings are calculated.

Method references: [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/), [FAO-56 Chapter 3](https://www.fao.org/4/x0490e/x0490e07.htm).

## Checksums

- Raw source CSV: `24754903063ef71e9f833b216c3bdbf0524a4ad477d82b081a044733bdeba041`
- Backend CSV: `b0d5515c546e8e1b69262880a625cbb8e54a4eb86231efbe53c39c2f73649ae3`
- `checksums.sha256` also records metadata, this audit, inspection, retrieval record and preservation baseline checksums (avoiding self-referential hashes).

## Reproduction

Run from the repository root; offline by default:

```bash
.venv/bin/python -B -m src.features.prepare_power_daily_context
.venv/bin/python -B -m src.features.prepare_power_daily_context --validate-only
```

The cached source is reused without network requests. `--download` is permitted only when both cached response and retrieval record are absent; it requests only the same exact NASA POWER point/time window. Do not remove the source preservation baseline or inspection record. This script does not call the Phase 2A builder or validator and never writes their files.
