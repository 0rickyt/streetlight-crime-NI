"""Irish Grid helpers that need only numpy.

- wgs84_to_irish_grid(): longitude/latitude (WGS84) -> TM65 Irish Grid metres
  (EPSG:29902), via a 7-parameter Helmert datum shift and the Transverse
  Mercator projection. Accurate to a few metres, ample for 1 km cells.
- grid_square_id(): Irish Grid easting/northing -> NISRA 1 km grid square code
  ("J 38 77"), which is referenced from the square's south-west corner.

geopandas/pyproj (used in the notebooks) give the same results; these
functions let the aggregation run where those packages are unavailable.
"""
import numpy as np

# 100 km square letters, rows from south (northing 0-100 km) to north
_LETTERS = ["VWXYZ", "QRSTU", "LMNOP", "FGHJK", "ABCDE"]


def grid_square_id(easting, northing) -> np.ndarray:
    e = np.asarray(easting, dtype=float)
    n = np.asarray(northing, dtype=float)
    ek, nk = np.floor(e / 1000).astype(int), np.floor(n / 1000).astype(int)
    col, row = ek // 100, nk // 100
    out = np.full(e.shape, None, dtype=object)
    ok = (col >= 0) & (col < 5) & (row >= 0) & (row < 5)
    for i in np.flatnonzero(ok):
        out[i] = f"{_LETTERS[row[i]][col[i]]} {ek[i] % 100:02d} {nk[i] % 100:02d}"
    return out


def grid_square_sw_corner(cell_ids):
    """Inverse of grid_square_id: south-west corner (metres) of each square."""
    e, n = [], []
    for cid in cell_ids:
        letter, ek, nk = cid.split()
        row = next(r for r, s in enumerate(_LETTERS) if letter in s)
        col = _LETTERS[row].index(letter)
        e.append(col * 100_000 + int(ek) * 1000)
        n.append(row * 100_000 + int(nk) * 1000)
    return np.array(e, float), np.array(n, float)


def _geodetic_to_ecef(lat, lon, a, f, h=0.0):
    e2 = f * (2 - f)
    nu = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    return ((nu + h) * np.cos(lat) * np.cos(lon),
            (nu + h) * np.cos(lat) * np.sin(lon),
            (nu * (1 - e2) + h) * np.sin(lat))


def _ecef_to_geodetic(x, y, z, a, f):
    e2 = f * (2 - f)
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1 - e2))
    for _ in range(10):
        nu = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
        lat = np.arctan2(z + e2 * nu * np.sin(lat), p)
    return lat, np.arctan2(y, x)


def _helmert(x, y, z, tx, ty, tz, rx, ry, rz, s_ppm):
    """Position-vector Helmert transform (rotations in arc-seconds)."""
    rx, ry, rz = (np.radians(v / 3600) for v in (rx, ry, rz))
    s = 1 + s_ppm * 1e-6
    return (tx + s * (x - rz * y + ry * z),
            ty + s * (rz * x + y - rx * z),
            tz + s * (-ry * x + rx * y + z))


def _transverse_mercator(lat, lon, a, f, lat0, lon0, k0, fe, fn):
    """Ordnance Survey Transverse Mercator formulae."""
    b = a * (1 - f)
    e2 = 1 - b**2 / a**2
    n = (a - b) / (a + b)
    lat0, lon0 = np.radians(lat0), np.radians(lon0)
    sin, cos, tan = np.sin(lat), np.cos(lat), np.tan(lat)
    nu = a * k0 / np.sqrt(1 - e2 * sin**2)
    rho = a * k0 * (1 - e2) / (1 - e2 * sin**2) ** 1.5
    eta2 = nu / rho - 1
    dl, sl = lat - lat0, lat + lat0
    m = b * k0 * (
        (1 + n + 1.25 * n**2 + 1.25 * n**3) * dl
        - (3 * n + 3 * n**2 + 21 / 8 * n**3) * np.sin(dl) * np.cos(sl)
        + (15 / 8 * n**2 + 15 / 8 * n**3) * np.sin(2 * dl) * np.cos(2 * sl)
        - 35 / 24 * n**3 * np.sin(3 * dl) * np.cos(3 * sl)
    )
    i = m + fn
    ii = nu / 2 * sin * cos
    iii = nu / 24 * sin * cos**3 * (5 - tan**2 + 9 * eta2)
    iiia = nu / 720 * sin * cos**5 * (61 - 58 * tan**2 + tan**4)
    iv = nu * cos
    v = nu / 6 * cos**3 * (nu / rho - tan**2)
    vi = nu / 120 * cos**5 * (5 - 18 * tan**2 + tan**4 + 14 * eta2 - 58 * tan**2 * eta2)
    d = lon - lon0
    north = i + ii * d**2 + iii * d**4 + iiia * d**6
    east = fe + iv * d + v * d**3 + vi * d**5
    return east, north


# WGS84 and Airy Modified (Ireland 1965) ellipsoids
_WGS84 = (6378137.0, 1 / 298.257223563)
_AIRY_MOD = (6377340.189, 1 / 299.3249646)
# EPSG:29902 towgs84 (TM65 -> WGS84); negated here for WGS84 -> TM65
_TOWGS84 = (482.5, -130.6, 564.6, -1.042, -0.214, -0.631, 8.15)


def wgs84_to_irish_grid(lon, lat):
    lat = np.radians(np.asarray(lat, float))
    lon = np.radians(np.asarray(lon, float))
    x, y, z = _geodetic_to_ecef(lat, lon, *_WGS84)
    x, y, z = _helmert(x, y, z, *(-v for v in _TOWGS84))
    lat65, lon65 = _ecef_to_geodetic(x, y, z, *_AIRY_MOD)
    return _transverse_mercator(lat65, lon65, *_AIRY_MOD,
                                lat0=53.5, lon0=-8.0, k0=1.000035, fe=200000, fn=250000)
