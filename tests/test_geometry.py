import math

import pytest

from vi2x.geometry import parse_axes, transform

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
