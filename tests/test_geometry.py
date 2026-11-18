import math

import pytest

from vi2x.geometry import build_mesh, parse_axes, transform

RAW_AXES = parse_axes("z", "-y")  # identity mapping


def test_parse_axes_default():
    assert parse_axes("y", "z") == [(0, 1.0), (2, -1.0), (1, 1.0)]


def test_parse_axes_already_output_convention():
    assert parse_axes("z", "-y") == RAW_AXES


def test_parse_axes_whitespace_case_plus():
    assert parse_axes(" Z ", " +X ") == [(1, 1.0), (0, -1.0), (2, 1.0)]


@pytest.mark.parametrize("up,view", [("x", "x"), ("y", "-y"), ("q", "z"), ("y", ""), ("", "z")])
def test_parse_axes_invalid(up, view):
    with pytest.raises(SystemExit):
        parse_axes(up, view)


@pytest.mark.parametrize("up", ["x", "-x", "y", "-y", "z", "-z"])
@pytest.mark.parametrize("view", ["x", "-x", "y", "-y", "z", "-z"])
def test_parse_axes_maps_up_and_view(up, view):
    if up.lstrip("-") == view.lstrip("-"):
        return
    axes = parse_axes(up, view)
    unit = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}

    def vec(s):
        return tuple((-1 if s[0] == "-" else 1) * c for c in unit[s.lstrip("-")])

    out_up = tuple(sg * vec(up)[src] for src, sg in axes)
    out_view = tuple(sg * vec(view)[src] for src, sg in axes)
    assert out_up == (0, 0, 1)
    assert out_view == (0, -1, 0)

def test_transform_scale_and_axes():
    out = transform([(0, 0, 0), (10, 20, 30)], 0.1, parse_axes("y", "z"))
    # raw (10,20,30)*0.1 = (1,2,3) -> (x, -z, y) = (1,-3,2); the lowest point (0,0,0) is the origin
    assert out[0] == pytest.approx((0, 0, 0))
    assert out[1] == pytest.approx((1, -3, 2))


def test_transform_empty():
    assert transform([], 1.0, RAW_AXES) == []


PTS = [(0, 0, 0), (10, 4, 2), (4, 2, 8)]


def test_origin_is_centre_of_lowest_slice():
    # feet at z=0 spanning x 2..6, y 0..4; a head at z=100 far off to the side must not matter
    pts = [(2, 0, 0), (6, 4, 0), (50, 50, 100)]
    out = transform(pts, 1, RAW_AXES)
    assert out[0] == pytest.approx((-2, -2, 0))
    assert out[1] == pytest.approx((2, 2, 0))
    assert out[2] == pytest.approx((46, 48, 100))


# ------------------------------------------------------------------ meshing
def _quad(extra=None):
    """Unit grid; point index = 2 * e + d."""
    pts = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0)]
    ed = [(0, 0), (0, 1), (1, 0), (1, 1)]
    return pts, ed


def test_mesh_full_cell_gives_two_triangles():
    pts, ed = _quad()
    verts, faces = build_mesh(pts, ed, range(4), max_edge=10)
    assert len(verts) == 4
    assert len(faces) == 2
    assert {v for f in faces for v in f} == {0, 1, 2, 3}


def test_mesh_picks_shorter_diagonal():
    pts, ed = _quad()
    pts[3] = (1.0, 1.0, 5.0)  # a-c diagonal is now long, b-q is shorter
    _, faces = build_mesh(pts, ed, range(4), max_edge=100)
    edges = {frozenset(e) for f in faces for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0]))}
    assert frozenset((1, 2)) in edges
    assert frozenset((0, 3)) not in edges


def test_mesh_drops_long_edges():
    pts, ed = _quad()
    verts, faces = build_mesh(pts, ed, range(4), max_edge=0.5)
    assert verts == []
    assert faces == []


def test_mesh_missing_corner_gives_one_triangle():
    pts, ed = _quad()
    verts, faces = build_mesh(pts, ed, [0, 1, 2], max_edge=10)  # no (1, 1)
    assert len(faces) == 1
    assert len(verts) == 3


def test_mesh_disconnected_points_have_no_faces():
    pts = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    ed = [(0, 0), (5, 5)]
    assert build_mesh(pts, ed, [0, 1], max_edge=10) == ([], [])


def test_mesh_indices_are_remapped_to_used_vertices():
    # unused point 0 is outside the cell; indices must refer to the returned vertex list
    pts = [(9.0, 9.0, 9.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    ed = [(100, 100), (0, 0), (0, 1), (1, 0)]
    verts, faces = build_mesh(pts, ed, range(4), max_edge=10)
    assert (9.0, 9.0, 9.0) not in verts
    assert all(0 <= i < len(verts) for f in faces for i in f)
