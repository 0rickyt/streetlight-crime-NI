# Lighting the Way? Street Light Availability and Street Crime across Urban Northern Ireland

Code and data instructions for a spatial analysis of public space crime and street lighting in Northern Ireland, for my 6SSG3077 *Applications of Spatial Data Science* project (CW1 report).

**Research questions**

1. Is street crime spatially clustered across urban Northern Ireland, and does this clustering coincide with areas of low street light availability?
2. Is street light availability a significant predictor of street crime once population density and commercial activity are accounted for?
3. Does this relationship differ between street crime and offences less plausibly affected by lighting?

## Approach

1. **Data cleaning.**
   - *Crime:* anti-social behaviour removed (incidents, not crimes) and records without coordinates dropped (1.3%), leaving 97,041 crimes. PSNI reuses Crime IDs across months, so duplicates are checked on Crime ID and month together (none found).
   - *Street lights:* invalid coordinates removed and lanterns sharing one column counted once, leaving 296,498 lights. Lantern wattage is recorded for only ~12% of lights, so lamp type is classified instead (86.9% LED by June 2023).
2. **Common scale.** Crime, street lights, population and commercial activity are aggregated to NISRA Census 2021 **1 km grid squares**. police.uk coordinates are projected to the TM65 Irish Grid (projected crime points lie a median 9.7 m from the nearest street light).
3. **Study area.** Squares at least 50% inside a NISRA Settlement Development Limit (2015) of Band A–E (settlements of 5,000+ people, NISRA's default urban threshold) with at least 100 residents: **447 squares in 42 settlements**, holding 57% of residents and 78% of street crime.
4. **Street Light Availability Index (SLAI).** The mean of two percentile-ranked components: lights per km² and lights per 1,000 residents.
5. **Lighting classes.** Crime rates compared across Low / Medium / High SLAI tertiles (Kruskal–Wallis). Only one urban square is unlit, so lit vs unlit is only meaningful across all of NI, where it mostly reflects urban vs rural.
6. **Spatial structure.** Global Moran's I, LISA hot spots, and bivariate LISA (SLAI vs street crime), using 8-nearest-neighbour weights.
7. **Modelling.** OLS baseline, then a random forest regressor tuned with `GridSearchCV`, comparing **random** and **spatial (10 km block) cross-validation**. Final test on held-out blocks; SHAP values for interpretation; Moran's I on out-of-fold residuals.
8. **Street crime vs comparison crime.** Every step is run for two groups:
   - *Street crime* (n = 17,533): criminal damage and arson, vehicle crime, robbery, theft from the person. Criminal damage makes up 83% of this group.
   - *Comparison crime* (n = 54,057): violence and sexual offences, shoplifting. These mostly happen indoors or between known parties, where lighting is unlikely to matter.

## Repository structure

```
├── data/README.md         where to download each dataset (raw data is not committed)
├── notebooks/             01 data preparation → 02 exploratory spatial analysis → 03 modelling
├── scripts/
│   └── aggregate_to_grid.py   cleaning + 1 km aggregation using only numpy and pandas
├── src/
│   ├── config.py          paths, study period, crime groups, study area, model settings
│   ├── features.py        lamp-type classification, SLAI
│   ├── irish_grid.py      WGS84 → Irish Grid projection and grid-square codes
│   ├── settlements.py     settlement (SDL 2015) overlay on the grid
│   └── modelling.py       OLS, random forest tuning, random vs spatial CV
├── outputs/               figures and tables used in the report
└── requirements.txt
```

## How to run

```bash
pip install -r requirements.txt
```

1. Download the data into `data/raw/` as described in [`data/README.md`](data/README.md). File names and columns are already set in `src/config.py`.
2. Build the grid-square table, either with notebook `01_data_preparation`, or without geopandas:
   ```bash
   python scripts/aggregate_to_grid.py
   ```
3. Run notebooks `02` and `03` from the `notebooks/` folder.

## Data sources

| Dataset | Source | Licence |
|---|---|---|
| Street-level crime, PSNI, Oct 2023 – Sep 2024 | [data.police.uk](https://data.police.uk/data/) | Open Government Licence v3.0 |
| All Street Lighting Columns (NI), DfI Roads, June 2023 | [OpenDataNI](https://admin.opendatani.gov.uk/dataset/lighting-assets) | Open Government Licence |
| Census 2021 grid square product (1 km) | [NISRA](https://www.nisra.gov.uk/publications/census-2021-grid-square-product-northern-ireland) | Open Government Licence |
| Settlement Development Limits 2015 | [NISRA](https://www.nisra.gov.uk/publications/urban-rural-geography-documents-2015) | Open Government Licence |
| Points of interest | [OpenStreetMap via Geofabrik](https://download.geofabrik.de/europe/united-kingdom/northern-ireland.html) | ODbL |

## Key limitations

- police.uk locations are snapped to anonymised points and carry no time of day, so night-time crime cannot be isolated.
- The street-light register is a June 2023 snapshot of where columns are installed, not whether they worked; the crime period starts four months later.
- Street crime is dominated by criminal damage, and street lights can themselves be targets of it (possible reverse causality).
- Census population measures where people live, not where they are at night (the ambient population problem), which inflates rates in town centres.
- NISRA suppresses population in very small squares; squares under 100 residents are excluded.
- Results depend on the 1 km grid (MAUP), and the design is cross-sectional: the findings are associations, not causal effects.
