# Phase 2 Environment Setup

## Status

The isolated Phase 2 environment was created at `.venv/` using Python 3.12.3. Dependencies were installed into that environment only; system Python was not modified. No datasets were regenerated or changed, and feature extraction has not started.

## Files

- [requirements-phase2.txt](../requirements-phase2.txt): compatible dependency ranges.
- [requirements-phase2-lock.txt](../requirements-phase2-lock.txt): exact installed package versions.
- `.venv/`: isolated virtual environment, excluded by `.gitignore`.

## Installation

From the project root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-phase2.txt
```

The environment was created without `sudo` and without installing standalone GDAL Python bindings. Rasterio and Pyogrio provide the resolved native geospatial runtime used by the environment.

## Activation

Linux/macOS:

```bash
source .venv/bin/activate
```

After activation, use `python` and `pip` normally. To leave the environment:

```bash
deactivate
```

Without activation, use `.venv/bin/python` and `.venv/bin/pip` explicitly.

## Installed versions

| Package | Version |
|---|---:|
| Python | 3.12.3 |
| pip | 26.3 |
| numpy | 2.5.4 |
| pandas | 2.3.3 |
| rasterio | 1.5.2 |
| geopandas | 1.2.0 |
| shapely | 2.2.0 |
| pyogrio | 0.13.0 |
| pyproj | 3.8.0 |

Additional resolved packages are recorded in [requirements-phase2-lock.txt](../requirements-phase2-lock.txt).

## Verification results

All required imports passed:

```text
numpy=2.5.4
pandas=2.3.3
rasterio=1.5.2
geopandas=1.2.0
shapely=2.2.0
pyogrio=0.13.0
pyproj=3.8.0
```

Rasterio runtime:

- GDAL runtime: `3.12.2`
- PROJ runtime reported by Rasterio: `9.8.1`

CDL verification used `data/source_packages/member4_v3/rasters/Story_County_CDL_2021_30m_EPSG5070.tif`:

- Driver: `GTiff`
- Dimensions: `1314 × 1323`
- Bands: `1`
- Data type: `uint8`
- CRS: `EPSG:5070`
- Resolution: `30.0 × 30.0` metres
- NoData: `0.0`
- Bounds: `188745.0, 2097915.0, 228165.0, 2137605.0`
- Metadata read successfully; a one-pixel sample read succeeded.

Soil GeoPackage verification used `data/source_packages/member4_v3/soil/soil_map_units_epsg5070.gpkg`:

- Layer: `soil_map_units_epsg5070`
- Geometry type: `Polygon`
- CRS: `EPSG:5070`
- Feature count: `39,591`
- Unique `mukey` values: `86`

Soil summary verification used `data/source_packages/member4_v3/soil/soil_summary.csv`:

- Row count: `86`
- Unique `mukey` values: `86`
- Columns loaded successfully, including `mukey`, soil attributes, units, and provenance fields.

## Result and remaining blockers

The environment is ready for the next Phase 2 implementation step: controlled raster/polygon feature extraction. No dependency or input-access blocker remains for the requested GeoTIFF and GeoPackage operations. Feature extraction itself remains intentionally unstarted.
