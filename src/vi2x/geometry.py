"""Coordinate transformation and meshing."""

from __future__ import annotations

Point = tuple[float, float, float]


def _parse_axis(spec: str, opt: str) -> tuple[int, int]:
    """'-y' -> (1, -1): source axis index and sign."""
    s = spec.strip().lower()
    sign = -1 if s.startswith("-") else 1
    s = s.lstrip("+-")
    if s not in ("x", "y", "z"):
        raise SystemExit(f"{opt} needs one of x, y, z with optional sign, e.g. -y; got {spec!r}")
    return "xyz".index(s), sign


def parse_axes(up: str, view: str) -> list[tuple[int, float]]:
    """Input axes 'up' and 'view' (towards the viewer) -> axis mapping.

    The output always has up = +Z and view = -Y, so X = up x view (right-handed).
    Returns [(src_index, sign), ...]: output axis k takes sign*input[src].
    """
    ui, us = _parse_axis(up, "--up")
    vi, vs = _parse_axis(view, "--view")
    if ui == vi:
        raise SystemExit("--up and --view must be different axes")
    xi = 3 - ui - vi  # the remaining axis
    # sign of the remaining axis so that x = up x view: e_u x e_v = +/- e_x (cyclic parity)
    cyc = 1 if (vi - ui) % 3 == 1 else -1
    xs = us * vs * cyc
    return [(xi, float(xs)), (vi, float(-vs)), (ui, float(us))]

FLOOR_SLICE = 0.02  # fraction of the height that counts as "lowest" for the origin


def transform(pts, scale: float, axes) -> list[Point]:
    """Remap axes, scale, then move the origin to the lowest centre point.

    The origin ends up at the centre of the lowest slice (the feet) in X/Y and at the minimum\n    in Z.
    """
    out = [tuple(sg * p[src] * scale for src, sg in axes) for p in pts]
    if out:
        zmin = min(p[2] for p in out)
        zmax = max(p[2] for p in out)
        # the lowest slice (feet): points within FLOOR_SLICE of the height above the minimum
        low = [p for p in out if p[2] <= zmin + FLOOR_SLICE * (zmax - zmin)]
        off = [
            (min(p[0] for p in low) + max(p[0] for p in low)) / 2,
            (min(p[1] for p in low) + max(p[1] for p in low)) / 2,
            zmin,
        ]
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
