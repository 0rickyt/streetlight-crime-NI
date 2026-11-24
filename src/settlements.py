"""Overlay NISRA Settlement Development Limits (2015) on the 1 km grid.

Reads the polygon shapefile directly (no geopandas) and estimates the share of
each grid square inside each settlement by testing a 20 x 20 lattice of points
per square (0.25% resolution) with matplotlib's point-in-polygon test.
"""
import struct
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath


def read_dbf(path) -> pd.DataFrame:
    b = Path(path).read_bytes()
    n = struct.unpack("<I", b[4:8])[0]
    header, record = struct.unpack("<H", b[8:10])[0], struct.unpack("<H", b[10:12])[0]
    fields, i = [], 32
    while b[i] != 0x0D:
        fields.append((b[i:i + 11].split(b"\0")[0].decode(), chr(b[i + 11]), b[i + 16]))
        i += 32
    rows = []
    for r in range(n):
        rec, pos, row = b[header + r * record: header + (r + 1) * record], 1, {}
        for name, kind, length in fields:
            value = rec[pos:pos + length].decode("latin-1").strip()
            row[name] = float(value) if kind in "FN" and value else value
            pos += length
        rows.append(row)
    return pd.DataFrame(rows)


def read_polygons(path):
    """Return one matplotlib Path per shapefile record (rings joined, holes kept)."""
    b = Path(path).read_bytes()
    pos, paths = 100, []
    while pos < len(b):
        length = struct.unpack(">i", b[pos + 4:pos + 8])[0] * 2
        rec = b[pos + 8: pos + 8 + length]
        pos += 8 + length
        if struct.unpack("<i", rec[:4])[0] == 0:          # null shape
            paths.append(None)
            continue
        n_parts, n_points = struct.unpack("<2i", rec[36:44])
        parts = list(struct.unpack(f"<{n_parts}i", rec[44:44 + 4 * n_parts])) + [n_points]
        pts = np.frombuffer(rec[44 + 4 * n_parts: 44 + 4 * n_parts + 16 * n_points], "<f8").reshape(-1, 2)
        verts, codes = [], []
        for a, z in zip(parts[:-1], parts[1:]):
            ring = pts[a:z]
            verts.extend(ring)
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(ring) - 2) + [MplPath.CLOSEPOLY])
        paths.append(MplPath(np.array(verts), codes))
    return paths


def settlement_coverage(cells: pd.DataFrame, shp_path, n: int = 20) -> pd.DataFrame:
    """Share of each square (indexed by cell_id, with x/y centres) inside each settlement.

    Returns a long table: cell_id, settlement code, share (0-1).
    """
    attrs = read_dbf(Path(shp_path).with_suffix(".dbf"))
    polys = read_polygons(shp_path)
    offsets = (np.arange(n) + 0.5) / n * 1000 - 500        # lattice inside a 1 km square
    ox, oy = [a.ravel() for a in np.meshgrid(offsets, offsets)]
    cx, cy = cells["x"].to_numpy(), cells["y"].to_numpy()
    out = []
    for code, poly in zip(attrs["Code"], polys):
        if poly is None:
            continue
        (xmin, ymin), (xmax, ymax) = poly.vertices.min(0), poly.vertices.max(0)
        near = np.flatnonzero((cx + 500 > xmin) & (cx - 500 < xmax) & (cy + 500 > ymin) & (cy - 500 < ymax))
        if not len(near):
            continue
        pts = np.column_stack([(cx[near, None] + ox).ravel(), (cy[near, None] + oy).ravel()])
        share = poly.contains_points(pts).reshape(len(near), -1).mean(axis=1)
        keep = share > 0
        out.append(pd.DataFrame({"cell_id": cells.index[near][keep], "Code": code, "share": share[keep]}))
    cov = pd.concat(out, ignore_index=True)
    return cov.merge(attrs, on="Code")
