"""Project settings: file paths, study period, crime groups and model options.

Edit the values marked CHECK after downloading the data (see data/README.md).
"""
from pathlib import Path

# --- Paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "outputs" / "figures"
TABLES = ROOT / "outputs" / "tables"

STREETLIGHT_CSV = DATA_RAW / "streetlights" / "Street Lighting Assets.csv"
POLICE_DIR = DATA_RAW / "police"                        # unzipped data.police.uk folders
GRID_BOUNDARY = DATA_RAW / "nisra_grid" / "Grid_Square_2021_1km.shp"
GRID_DATA_CSV = DATA_RAW / "nisra_grid" / "census-2021-grid-square-product-1km-full-dataset.csv"
OSM_POIS = DATA_RAW / "osm" / "gis_osm_pois_free_1.shp"          # optional

PROCESSED_CELLS = DATA_PROCESSED / "grid_cells.gpkg"

# --- Coordinate reference systems ---------------------------------------------
# All analysis is done in metres on the Irish Grid (TM65), the CRS of the
# NISRA grid-square boundaries.
CRS = "EPSG:29902"
# DfI street-light EASTING/NORTHING are Irish Grid coordinates.  CHECK: if lights
# plot slightly offset from the grid, try EPSG:29903 (TM75) here.
STREETLIGHT_CRS = "EPSG:29902"
POLICE_CRS = "EPSG:4326"                                 # police.uk longitude/latitude

# --- NISRA grid columns -------------------------------------------------------
GRID_ID_COL_BOUNDARY = "GSQ21_1km"   # e.g. "J 26 09" (14,753 cells)
GRID_ID_COL_DATA = "Geography"
POP_COL = "PERSONS"                 # all usual residents (0 where NISRA suppressed the square)

# --- Street lights ------------------------------------------------------------
# Keep only these ITEM_TYPE_NAME values (None keeps every row).  CHECK the
# value_counts() printed in notebook 01 before fixing this.
LIGHT_ITEM_TYPES = ["LIGHTING_POINT"]
# Valid Irish Grid range for Northern Ireland (drops 0,0 and lat/long typos)
NI_EASTING_RANGE = (180_000, 370_000)
NI_NORTHING_RANGE = (300_000, 460_000)
# Mount heights outside this range (m) are treated as data-entry errors
MOUNT_HEIGHT_RANGE = (2, 20)
# Components of the Street Light Availability Index. Lantern wattage is not
# used: it is only recorded for ~12% of lanterns (mostly old sodium lamps).
SLAI_COMPONENTS = ["lights_per_km2", "lights_per_1000"]

# --- Study period -------------------------------------------------------------
# Earliest 12 months available on data.police.uk (Nov 2026); starts 4 months
# after the June 2023 street-light snapshot.
START_MONTH = "2023-10"
END_MONTH = "2024-09"

# --- Crime groups (police.uk 'Crime type' values) -----------------------------
# Street crime: outdoor, mostly stranger offences where visibility after dark
# plausibly matters (the "lighting-sensitive" group).
STREET_CRIME = [
    "Robbery",
    "Theft from the person",
    "Vehicle crime",
    "Criminal damage and arson",
]
# Comparison group: offences mostly indoors or between known parties, where the
# surveillance mechanism of lighting is unlikely to operate.
COMPARISON_CRIME = [
    "Violence and sexual offences",
    "Shoplifting",
]
CRIME_GROUPS = {"street": STREET_CRIME, "comparison": COMPARISON_CRIME}

# --- Commercial activity (OpenStreetMap 'fclass' values) ----------------------
COMMERCIAL_FCLASSES = [
    "pub", "bar", "nightclub", "restaurant", "fast_food", "cafe",
    "supermarket", "convenience", "department_store", "mall",
    "clothes", "shoes", "mobile_phone", "chemist", "bank", "atm",
]

# --- Study area ---------------------------------------------------------------
# Urban = NISRA Settlement Development Limits 2015, Bands A-E (settlements of
# 5,000+ people; NISRA's default urban-rural threshold). A 1 km square is urban
# if at least URBAN_MIN_SHARE of its area lies inside a Band A-E settlement.
SETTLEMENTS_SHP = DATA_RAW / "settlements" / "settlements-2015-above-500-threshold.shp"
URBAN_BANDS = ["A", "B", "C", "D", "E"]
URBAN_MIN_SHARE = 0.5
# Squares with very few residents (harbours, industrial estates, parks) give
# unstable per-resident rates, so the modelled study area also needs:
MIN_RESIDENTS = 100

# --- Modelling ----------------------------------------------------------------
BLOCK_SIZE_M = 10_000          # spatial CV blocks (10 km squares)
TEST_SIZE = 0.2
N_SPLITS = 5
N_ESTIMATORS = 300
RANDOM_STATE = 42
RF_PARAM_GRID = {
    "max_depth": [4, 8, 12, None],
    "min_samples_leaf": [1, 5, 20],
}
