"""Coordinate transformation."""

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

    The origin ends up at the centre of the lowest slice (the feet) in X/Y and at the minimum
    in Z.
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
