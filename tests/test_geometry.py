import math

import pytest

from vi2x.geometry import build_mesh, parse_axes, rot_matrix, transform

IDENTITY = rot_matrix(0, 0, 0)
RAW_AXES = parse_axes("x,y,z")


def test_parse_axes_default():
    assert parse_axes("x,-z,y") == [(0, 1.0), (2, -1.0), (1, 1.0)]


def test_parse_axes_whitespace_case_plus():
    assert parse_axes(" X , +Y , -Z ") == [(0, 1.0), (1, 1.0), (2, -1.0)]


@pytest.mark.parametrize("spec", ["x,y", "x,y,z,x", "x,y,q", "x,x,y", "x,-x,y", ""])
def test_parse_axes_invalid(spec):
    with pytest.raises(SystemExit):
        parse_axes(spec)


def test_identity_rotation():
    for row, expected in zip(IDENTITY, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], strict=True):
        assert row == pytest.approx(expected)


def test_rotation_z_90_maps_x_to_y():
    m = rot_matrix(0, 0, 90)
    assert [sum(m[i][k] * v for k, v in enumerate((1, 0, 0))) for i in range(3)] == pytest.approx(
        [0, 1, 0]
    )


def test_rotation_order_is_x_then_y_then_z():
    m = rot_matrix(90, 90, 0)
    # x-axis: Rx leaves it, Ry(90) sends it to -z
    assert [m[i][0] for i in range(3)] == pytest.approx([0, 0, -1])
    # y-axis: Rx(90) sends it to z, Ry(90) sends z to x
    assert [m[i][1] for i in range(3)] == pytest.approx([1, 0, 0])


def test_rotation_is_orthonormal():
    m = rot_matrix(12, -47, 133)
    for i in range(3):
        for j in range(3):
            dot = sum(m[i][k] * m[j][k] for k in range(3))
            assert dot == pytest.approx(1.0 if i == j else 0.0, abs=1e-12)


def test_transform_scale_and_axes():
    out = transform([(10, 20, 30)], 0.1, parse_axes("x,-z,y"), IDENTITY, "none")
    assert out == [pytest.approx((1.0, -3.0, 2.0))]


def test_transform_empty():
    assert transform([], 1.0, RAW_AXES, IDENTITY, "floor") == []


PTS = [(0, 0, 0), (10, 4, 2), (4, 2, 8)]


def test_center_none():
    assert transform(PTS, 1, RAW_AXES, IDENTITY, "none") == [(0, 0, 0), (10, 4, 2), (4, 2, 8)]


def test_center_bbox():
    out = transform(PTS, 1, RAW_AXES, IDENTITY, "bbox")
    assert out[0] == pytest.approx((-5, -2, -4))
    assert out[1] == pytest.approx((5, 2, -2))


def test_center_floor():
    out = transform(PTS, 1, RAW_AXES, IDENTITY, "floor")
    assert min(p[1] for p in out) == 0
    assert (min(p[0] for p in out) + max(p[0] for p in out)) / 2 == pytest.approx(0)
    assert (min(p[2] for p in out) + max(p[2] for p in out)) / 2 == pytest.approx(0)


def test_center_mean():
    out = transform(PTS, 1, RAW_AXES, IDENTITY, "mean")
    for k in range(3):
        assert sum(p[k] for p in out) == pytest.approx(0)


def test_transform_applies_rotation_after_scale():
    out = transform([(1, 0, 0)], 2.0, RAW_AXES, rot_matrix(0, 0, 90), "none")
    assert out[0] == pytest.approx((0, 2, 0), abs=1e-12)
    assert math.isclose(math.dist(out[0], (0, 0, 0)), 2.0)


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
