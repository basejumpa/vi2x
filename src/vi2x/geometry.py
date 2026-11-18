"""Coordinate transformation and meshing."""

from __future__ import annotations

import math

Point = tuple[float, float, float]
Matrix = list[list[float]]


def parse_axes(spec: str) -> list[tuple[int, float]]:
    """'x,-z,y' -> [(src_index, sign), ...]: output axis k takes sign*input[src]."""
    parts = [p.strip().lower() for p in spec.split(",")]
    if len(parts) != 3:
        raise SystemExit("--axes needs three comma separated entries, e.g. x,-z,y")
    res = []
    for p in parts:
        sign = -1.0 if p.startswith("-") else 1.0
        p = p.lstrip("+-")
        if p not in ("x", "y", "z"):
            raise SystemExit(f"bad axis {p!r} in --axes")
        res.append(("xyz".index(p), sign))
    if len({s for s, _ in res}) != 3:
        raise SystemExit("--axes must use each of x, y, z exactly once")
    return res


def rot_matrix(rx: float, ry: float, rz: float) -> Matrix:
    """Rotation about X, then Y, then Z (degrees), as 3x3 row matrix."""
    rx, ry, rz = (math.radians(a) for a in (rx, ry, rz))
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    mx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    my = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    mz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]

    def mul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

    return mul(mz, mul(my, mx))


def transform(pts, scale: float, axes, rot: Matrix, center: str) -> list[Point]:
    m = rot
    out = []
    for p in pts:
        v = [axes[k][1] * p[axes[k][0]] * scale for k in range(3)]
        out.append(
            (
                m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
                m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
                m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
            )
        )
    if center != "none" and out:
        mins = [min(p[k] for p in out) for k in range(3)]
        maxs = [max(p[k] for p in out) for k in range(3)]
        if center == "bbox":
            off = [(mins[k] + maxs[k]) / 2 for k in range(3)]
        elif center == "floor":  # centre x/z, put lowest point (min along 2nd axis) at 0
            off = [(mins[0] + maxs[0]) / 2, mins[1], (mins[2] + maxs[2]) / 2]
        else:  # mean
            off = [sum(p[k] for p in out) / len(out) for k in range(3)]
        out = [(p[0] - off[0], p[1] - off[1], p[2] - off[2]) for p in out]
    return out


def build_mesh(pts, ed, idxs, max_edge: float):
    """Triangulate one head.

    Each head is a range image: points are arranged on a grid of scan line e and pixel
    column d. Neighbouring grid cells are joined into triangles; triangles with an edge
    longer than `max_edge` (in output units) are dropped, so gaps and depth jumps
    (silhouettes) are not bridged.
    Returns (vertices, faces) with only the used vertices and faces indexing into them.
    """
    grid = {ed[i]: i for i in idxs}
    me2 = max_edge * max_edge
    faces: list[tuple[int, int, int]] = []

    def d2(i, j):
        p, q = pts[i], pts[j]
        return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2

    def tri(i, j, k):
        if d2(i, j) <= me2 and d2(j, k) <= me2 and d2(k, i) <= me2:
            faces.append((i, j, k))

    get = grid.get
    for (e, d), a in grid.items():
        b = get((e, d + 1))
        c = get((e + 1, d + 1))
        q = get((e + 1, d))
        if b is not None and c is not None and q is not None:
            if d2(a, c) <= d2(b, q):  # split along the shorter diagonal
                tri(a, b, c)
                tri(a, c, q)
            else:
                tri(a, b, q)
                tri(b, c, q)
        elif b is not None and c is not None:
            tri(a, b, c)
        elif b is not None and q is not None:
            tri(a, b, q)
        elif c is not None and q is not None:
            tri(a, c, q)
    used = sorted({v for f in faces for v in f})
    remap = {v: n for n, v in enumerate(used)}
    return [pts[v] for v in used], [(remap[i], remap[j], remap[k]) for i, j, k in faces]
