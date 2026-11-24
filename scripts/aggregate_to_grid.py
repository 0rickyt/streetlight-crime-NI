"""Clean crime and street-light data and aggregate them to NISRA 1 km grid squares.

A numpy/pandas-only version of notebook 01 (no geopandas needed). Points are
assigned to squares through the grid-square code ("J 38 77"), which encodes
each square's south-west corner on the TM65 Irish Grid.

Run from the repository root:  python scripts/aggregate_to_grid.py
Writes data/processed/grid_cells_1km.csv and cleaning tables in outputs/tables/.
"""
import struct
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src import config                                          # noqa: E402
from src.features import build_slai, classify_lamp               # noqa: E402
from src.irish_grid import (grid_square_id, grid_square_sw_corner,  # noqa: E402
                            wgs84_to_irish_grid)
from src.modelling import make_blocks                            # noqa: E402
from src.settlements import settlement_coverage                  # noqa: E402


def read_dbf_ids(path):
    """Read the single ID column from the grid shapefile's .dbf table."""
    b = Path(path).read_bytes()
    n = struct.unpack("<I", b[4:8])[0]
    header, record = struct.unpack("<H", b[8:10])[0], struct.unpack("<H", b[10:12])[0]
    return [b[header + r * record + 1: header + (r + 1) * record].decode().strip() for r in range(n)]


def clean_crime(log):
    files = sorted(config.POLICE_DIR.rglob("*-street.csv"))
    c = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    log.append(("crime", "raw rows", len(c)))
    c = c[c["Month"].between(config.START_MONTH, config.END_MONTH)]
    log.append(("crime", f"months {config.START_MONTH} to {config.END_MONTH}", len(c)))
    c = c[c["Crime type"] != "Anti-social behaviour"]
    log.append(("crime", "anti-social behaviour removed", len(c)))
    c = c.dropna(subset=["Longitude", "Latitude"])
    log.append(("crime", "missing coordinates removed", len(c)))
    # PSNI reuses Crime IDs across months, so check duplicates within a month
    c = c.drop_duplicates(subset=["Crime ID", "Month"])
    log.append(("crime", "duplicate (Crime ID, Month) removed", len(c)))
    c["group"] = "other"
    for group, types in config.CRIME_GROUPS.items():
        c.loc[c["Crime type"].isin(types), "group"] = group
    e, n = wgs84_to_irish_grid(c.Longitude.values, c.Latitude.values)
    c["cell_id"] = grid_square_id(e, n)
    return c


def clean_lights(log):
    d = pd.read_csv(config.STREETLIGHT_CSV, low_memory=False)
    log.append(("lights", "raw rows", len(d)))
    if config.LIGHT_ITEM_TYPES:
        d = d[d["ITEM_TYPE_NAME"].isin(config.LIGHT_ITEM_TYPES)]
        log.append(("lights", "item type LIGHTING_POINT", len(d)))
    d = d[d.EASTING.between(*config.NI_EASTING_RANGE) & d.NORTHING.between(*config.NI_NORTHING_RANGE)]
    log.append(("lights", "valid Irish Grid coordinates", len(d)))
    d = d.drop_duplicates(subset=["EASTING", "NORTHING"])
    log.append(("lights", "duplicate locations removed", len(d)))
    d["lamp_type"] = classify_lamp(d["LANTERN_BOQ_NAME"])
    d["mount_height"] = pd.to_numeric(d["MOUNT_HEIGHT"], errors="coerce")
    d.loc[~d.mount_height.between(*config.MOUNT_HEIGHT_RANGE), "mount_height"] = np.nan
    d["cell_id"] = grid_square_id(d.EASTING.values, d.NORTHING.values)
    return d


def main():
    log = []
    ids = read_dbf_ids(config.GRID_BOUNDARY.with_suffix(".dbf"))
    cells = pd.DataFrame(index=pd.Index(ids, name="cell_id"))

    pop = pd.read_csv(config.GRID_DATA_CSV,
                      usecols=[config.GRID_ID_COL_DATA, "SUPPRESSION_FLAG", "HOUSEHOLDS", config.POP_COL])
    pop = pop.rename(columns={config.GRID_ID_COL_DATA: "cell_id", config.POP_COL: "population",
                              "HOUSEHOLDS": "households", "SUPPRESSION_FLAG": "suppression"})
    cells = cells.join(pop.set_index("cell_id"))
    cells["suppression"] = cells["suppression"].fillna("NO DATA")
    cells[["population", "households"]] = cells[["population", "households"]].fillna(0)

    lights = clean_lights(log)
    lights = lights[lights.cell_id.isin(cells.index)]
    log.append(("lights", "inside the grid", len(lights)))
    cells["n_lights"] = lights.groupby("cell_id").size()
    cells["pct_led"] = lights.assign(led=lights.lamp_type.eq("LED")).groupby("cell_id").led.mean() * 100
    cells["mean_mount_height"] = lights.groupby("cell_id").mount_height.mean()

    crime = clean_crime(log)
    crime = crime[crime.cell_id.isin(cells.index)]
    log.append(("crime", "inside the grid", len(crime)))
    for group in list(config.CRIME_GROUPS) + ["other"]:
        cells[f"{group}_count"] = crime[crime.group == group].groupby("cell_id").size()
    by_type = crime.groupby(["cell_id", "Crime type"]).size().unstack(fill_value=0)
    by_type.columns = ["n_" + c.lower().replace(" ", "_") for c in by_type.columns]
    cells = cells.join(by_type)
    counts = [c for c in cells if c.startswith("n_") or c.endswith("_count")]
    cells[counts] = cells[counts].fillna(0).astype(int)

    # Derived variables (every square is 1 km², so per-km² values equal counts)
    cells["area_km2"] = 1.0
    cells["pop_density"] = cells.population / cells.area_km2
    cells["lights_per_km2"] = cells.n_lights / cells.area_km2
    cells["lights_per_1000"] = np.where(cells.population > 0, cells.n_lights / cells.population * 1000, np.nan)
    cells["lit"] = (cells.n_lights > 0).astype(int)
    for group in config.CRIME_GROUPS:
        cells[f"{group}_rate"] = np.where(cells.population > 0,
                                          cells[f"{group}_count"] / cells.population * 1000, np.nan)
    sw_e, sw_n = grid_square_sw_corner(cells.index)
    cells["x"], cells["y"] = sw_e + 500, sw_n + 500
    cells["block"] = make_blocks(cells.x, cells.y, config.BLOCK_SIZE_M)

    # Urban definition: share of each square inside Band A-E settlements (SDL 2015)
    cov = settlement_coverage(cells, config.SETTLEMENTS_SHP)
    cells["urban_share"] = (cov[cov.Band.isin(config.URBAN_BANDS)]
                            .groupby("cell_id").share.sum().clip(upper=1))
    cells["urban_share"] = cells["urban_share"].fillna(0)
    main = cov.sort_values("share", ascending=False).drop_duplicates("cell_id").set_index("cell_id")
    cells["settlement"], cells["settlement_band"] = main.Name, main.Band
    cells["urban"] = cells.urban_share >= config.URBAN_MIN_SHARE
    cells["study_area"] = cells.urban & (cells.population >= config.MIN_RESIDENTS)

    cells["slai"] = np.nan
    cells.loc[cells.study_area, "slai"] = build_slai(cells[cells.study_area], config.SLAI_COMPONENTS)
    cells["light_class"] = "Unlit"
    lit_study = cells.study_area & (cells.lit == 1)
    cells.loc[lit_study, "light_class"] = pd.qcut(
        cells.loc[lit_study, "slai"].rank(method="first"), 3, labels=["Low", "Medium", "High"]).astype(str)
    log.append(("grid", "1 km squares", len(cells)))
    log.append(("grid", f"urban squares (>= {config.URBAN_MIN_SHARE:.0%} in Band A-E settlement)", int(cells.urban.sum())))
    log.append(("grid", f"study area (urban, >= {config.MIN_RESIDENTS} residents)", int(cells.study_area.sum())))

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    config.TABLES.mkdir(parents=True, exist_ok=True)
    cells.reset_index().to_csv(config.DATA_PROCESSED / "grid_cells_1km.csv", index=False)
    pd.DataFrame(log, columns=["dataset", "step", "rows"]).to_csv(config.TABLES / "cleaning_log.csv", index=False)
    for row in log:
        print(f"{row[0]:7s} | {row[1]:45s} | {row[2]:,}")


if __name__ == "__main__":
    main()
