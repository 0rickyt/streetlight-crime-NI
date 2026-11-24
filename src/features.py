"""Feature engineering: lantern wattage and the Street Light Availability Index."""
import numpy as np
import pandas as pd


def parse_wattage(lantern_names: pd.Series) -> pd.Series:
    """Extract lamp wattage from DfI lantern descriptions, e.g. 'Luminaire 250w SON-t' -> 250.

    Rows without a recognisable wattage return NaN.
    """
    watts = lantern_names.astype(str).str.extract(r"(\d+(?:\.\d+)?)\s*[wW]\b")[0]
    return pd.to_numeric(watts, errors="coerce")


def classify_lamp(lantern_names: pd.Series) -> pd.Series:
    """Group DfI lantern descriptions into lamp technologies.

    LED and metal halide give white light; SON (high-pressure sodium) and SOX
    (low-pressure sodium) give the older orange light.
    """
    u = lantern_names.astype(str).str.upper()
    lamp = pd.Series("Other", index=lantern_names.index)
    lamp[u.str.contains(r"CDM|CPO|COSMO|METAL HALIDE|CMH")] = "Metal halide"
    lamp[u.str.contains(r"SOX|LOW PRESSURE")] = "SOX"
    lamp[u.str.contains(r"SON|HIGH PRESSURE")] = "SON"
    lamp[u.str.contains("LED")] = "LED"
    return lamp


def rescale(values: pd.Series, method: str = "rank") -> pd.Series:
    """Rescale a series to 0-1.

    'rank' (default) uses percentile ranks, so a handful of extreme city-centre
    cells cannot compress everyone else into a narrow band. 'minmax' is the
    plain (x - min) / (max - min) alternative.
    """
    if method == "rank":
        ranks = values.rank(pct=True)
        ranks[values == 0] = 0.0          # unlit cells stay at the bottom of the scale
        return ranks
    if method == "minmax":
        spread = values.max() - values.min()
        return (values - values.min()) / spread if spread else values * 0.0
    raise ValueError("method must be 'rank' or 'minmax'")


def build_slai(cells: pd.DataFrame, components: list, method: str = "rank") -> pd.Series:
    """Street Light Availability Index: the mean of rescaled lighting components.

    Missing component values (e.g. mean wattage in an unlit cell) are treated
    as 0 before rescaling.
    """
    scaled = pd.concat(
        [rescale(cells[c].fillna(0), method) for c in components], axis=1
    )
    return scaled.mean(axis=1)
