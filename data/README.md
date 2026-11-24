# Data

Raw data files are not committed to the repository (they are large and
available from the original publishers). Download them into the folders below.

## 1. Crime: `data/raw/police/`

1. Go to https://data.police.uk/data/
2. Date range: **October 2023 to September 2024**
3. Force: **Police Service of Northern Ireland** only
4. Tick **Include crime data** only, then generate and download the file.
5. Unzip it here. You should get monthly folders like `2023-10/2023-10-police-service-of-northern-ireland-street.csv`.

## 2. Street lights: `data/raw/streetlights/`

Download **All Street Lighting Columns (NI)** as CSV from OpenDataNI:
https://admin.opendatani.gov.uk/dataset/lighting-assets

Save it as `Street Lighting Assets.csv` (or change `STREETLIGHT_CSV` in `src/config.py`).

## 3. Population grid: `data/raw/nisra_grid/`

From https://www.nisra.gov.uk/publications/census-2021-grid-square-product-northern-ireland download:

- the **1 km** data (CSV in a ZIP), and
- the **1 km** boundary file (GeoJSON or shapefile).

Unzip the boundary shapefile here (`Grid_Square_2021_1km.shp` and its sidecar files).
Unzip the 1 km data ZIP here too; the project uses `census-2021-grid-square-product-1km-full-dataset.csv`
(`Geography` = square code, `PERSONS` = usual residents).

## 4. Urban areas: `data/raw/settlements/`

From https://www.nisra.gov.uk/publications/urban-rural-geography-documents-2015 download
**Settlement Development Limits 2015 - ESRI format** and unzip it here
(`settlements-2015-above-500-threshold.shp` and its sidecar files).

## 5. Points of interest (optional): `data/raw/osm/`

Download the Northern Ireland shapefile ZIP from Geofabrik:
https://download.geofabrik.de/europe/united-kingdom/northern-ireland.html

Unzip it and keep the `gis_osm_pois_free_1.*` files here. Without them, the models run
without the commercial activity variable.
