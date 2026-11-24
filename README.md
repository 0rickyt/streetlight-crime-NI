# Lighting the Way? Street Light Availability and Street Crime across Urban Northern Ireland

Code for my 6SSG3077 *Applications of Spatial Data Science* project (CW1 report).

**Research question:** Is street light availability associated with the spatial pattern of street crime across urban Northern Ireland, and does this differ from crime types that lighting is unlikely to affect?

## Approach

1. **Common scale.** Crime, street lights, population and commercial activity are aggregated to NISRA Census 2021 **1 km grid squares**.
   **Study area:** squares at least 50% inside a NISRA Settlement Development Limit (2015) of Band A–E (settlements of 5,000+ people) with at least 100 residents: 447 squares in 42 settlements.
2. **Street Light Availability Index (SLAI).** The mean of two percentile-ranked components: lights per km² and lights per 1,000 residents. Lamp type (% LED) is recorded separately.
3. **Lighting classes.** Crime rates across Low / Medium / High SLAI classes (Kruskal–Wallis). Almost no urban square is unlit, so lit vs unlit is only meaningful across all of NI, where it mostly reflects urban vs rural.
4. **Spatial structure.** Global Moran's I, LISA, and bivariate LISA (SLAI vs street crime).
5. **Modelling.** OLS baseline, then a random forest tuned with `GridSearchCV`, comparing **random** and **spatial (block) cross-validation**. Final test on held-out 10 km blocks. SHAP for interpretation, and Moran's I on residuals.
6. **Crime 1 vs Crime 2.** Everything is run for *street crime* (robbery, theft from the person, vehicle crime, criminal damage and arson) and a *comparison* group (violence and sexual offences, shoplifting).

## Repository structure

```
├── data/
│   ├── README.md          download instructions (raw data is not committed)
│   ├── raw/               police/, streetlights/, nisra_grid/, settlements/, osm/
│   └── processed/         grid_cells.gpkg, created by notebook 01
├── scripts/
│   └── aggregate_to_grid.py   cleaning + 1 km aggregation without geopandas
├── notebooks/
│   ├── 01_data_preparation.ipynb
│   ├── 02_exploratory_spatial_analysis.ipynb
│   └── 03_modelling.ipynb
├── outputs/
│   ├── figures/           maps and plots used in the report
│   └── tables/            CSV results (cleaning log, Moran's I, CV and test scores, SHAP)
├── src/
│   ├── config.py          paths, study period, crime groups, model settings
│   ├── features.py        lamp-type classification, SLAI
│   ├── settlements.py     settlement (SDL 2015) overlay on the grid
│   ├── irish_grid.py      WGS84 → Irish Grid projection and grid-square codes (numpy only)
│   └── modelling.py       OLS, random forest tuning, random vs spatial CV
└── requirements.txt
```

## How to run

```bash
pip install -r requirements.txt
```

1. Download the data into `data/raw/` as described in [`data/README.md`](data/README.md).
2. Open `src/config.py` and check the settings marked **CHECK** (NISRA file and column names).
3. Run the notebooks in order from the `notebooks/` folder: `01` → `02` → `03`.

If geopandas is not available, `python scripts/aggregate_to_grid.py` produces the same
grid-cell table (`data/processed/grid_cells_1km.csv`) using only numpy and pandas. Points are
assigned to squares through the NISRA grid code, and police.uk coordinates are projected to the
TM65 Irish Grid (checked: projected crime points lie a median 9.7 m from the nearest street light).

## Data sources

| Dataset | Source | Licence |
|---|---|---|
| Street-level crime, PSNI, Oct 2023 – Sep 2024 | [data.police.uk](https://data.police.uk/data/) | Open Government Licence v3.0 |
| All Street Lighting Columns (NI), DfI Roads, June 2023 | [OpenDataNI](https://admin.opendatani.gov.uk/dataset/lighting-assets) | Open Government Licence |
| Census 2021 grid square product (1 km) | [NISRA](https://www.nisra.gov.uk/publications/census-2021-grid-square-product-northern-ireland) | Open Government Licence |
| Settlement Development Limits 2015 | [NISRA](https://www.nisra.gov.uk/publications/urban-rural-geography-documents-2015) | Open Government Licence |
| Points of interest (optional) | [OpenStreetMap via Geofabrik](https://download.geofabrik.de/europe/united-kingdom/northern-ireland.html) | ODbL |

## Key limitations

- police.uk locations are snapped to anonymised points, and there is no time of day, so night-time crime cannot be isolated.
- The street-light register records where columns are installed, not whether they worked; DfI reported thousands of outages during the period.
- Census population measures where people live, not where they are at night (the ambient population problem), which inflates rates in town centres.
- Results depend on the 1 km grid (MAUP), and the design is cross-sectional: the findings are associations, not causal effects.
