import struct
import zlib

import pytest

from tests.conftest import HEADER, csf_record
from vi2x.readers import read_bsf, read_csf, read_scan


def test_empty_csf_payload(make_csf):
    assert read_csf(make_csf()) == ([], [], [])


def test_negative_coordinates(make_csf):
    pts, _, _ = read_csf(make_csf(csf_record(-5416, -5978, -10766, 0, 1, 0)))
    assert pts == [(-5416, -5978, -10766)]


def test_run_code_7_skips_two_extra_bytes(make_csf):
    f = make_csf(
        csf_record(10, 10, 0, 0, 1, 0, run=[(1, 1)], code=7),
        csf_record(50, 50, 36, 0, 2, 0),
    )
    pts, _, ed = read_csf(f)
    assert pts == [(10, 10, 0), (9, 9, 0), (50, 50, 36)]
    assert ed == [(1, 0), (1, 1), (2, 0)]


def test_run_with_negative_deltas(make_csf):
    pts, _, _ = read_csf(make_csf(csf_record(0, 0, 0, 0, 1, 0, run=[(-3, 4), (-3, 4)])))
    assert pts == [(0, 0, 0), (3, -4, 0), (6, -8, 0)]


def test_empty_run_yields_only_first_point(make_csf):
    pts, _, _ = read_csf(make_csf(csf_record(1, 2, 3, 0, 1, 0, run=[])))
    assert pts == [(1, 2, 3)]


def test_multiple_heads_and_filter(make_csf):
    f = make_csf(
        csf_record(1, 1, 1, 0, 1, 0),
        csf_record(2, 2, 2, 0, 1, 1, run=[(1, 1)]),
        csf_record(3, 3, 3, 0, 1, 2),
    )
    _, ws, _ = read_csf(f)
    assert ws == [0, 1, 1, 2]
    pts, ws, _ = read_csf(f, heads={1})
    assert ws == [1, 1]
    assert pts == [(2, 2, 2), (1, 1, 2)]
    assert read_csf(f, heads={7}) == ([], [], [])


def test_truncated_record(make_csf):
    f = make_csf(csf_record(1, 2, 3, 0, 1, 0)[:-3])
    with pytest.raises(SystemExit, match="truncated record"):
        read_csf(f)


def test_truncated_run(make_csf):
    f = make_csf(csf_record(1, 2, 3, 0, 1, 0, run=[(1, 1)])[:-3])
    with pytest.raises(SystemExit, match="truncated run"):
        read_csf(f)


def test_bad_zlib(tmp_path):
    p = tmp_path / "bad.csf"
    p.write_bytes(b"csf" + HEADER[3:] + struct.pack("<I", 10) + b"not zlib")
    with pytest.raises(SystemExit, match="zlib"):
        read_csf(p)


def test_size_mismatch_warns(make_csf, capsys):
    f = make_csf(csf_record(1, 2, 3, 0, 1, 0), size=999)
    pts, _, _ = read_csf(f)
    assert len(pts) == 1
    assert "size mismatch" in capsys.readouterr().err


def test_csf_wrong_magic(tmp_path):
    p = tmp_path / "x.csf"
    p.write_bytes(b"bsf" + bytes(300))
    with pytest.raises(SystemExit, match="not a csf"):
        read_csf(p)


def test_bsf_rows_and_filter(make_bsf):
    f = make_bsf([(1, 2, 3, 4, 5, 0), (6, 7, 8, 9, 10, 3)])
    pts, ws, ed = read_bsf(f)
    assert pts == [(1, 2, 3), (6, 7, 8)]
    assert ws == [0, 3]
    assert ed == [(5, 4), (10, 9)]
    assert read_bsf(f, heads={3})[0] == [(6, 7, 8)]


def test_bsf_unsigned_values(make_bsf):
    pts, _, _ = read_bsf(make_bsf([(65535, 40000, 0, 0, 1, 0)]))
    assert pts == [(65535, 40000, 0)]


def test_bsf_empty(make_bsf):
    assert read_bsf(make_bsf([])) == ([], [], [])


def test_bsf_bad_length(tmp_path):
    p = tmp_path / "x.bsf"
    p.write_bytes(b"bsf" + HEADER[3:] + b"\x00" * 5)
    with pytest.raises(SystemExit, match="not a valid bsf"):
        read_bsf(p)


def test_bsf_shorter_than_header(tmp_path):
    p = tmp_path / "x.bsf"
    p.write_bytes(b"bsf")
    with pytest.raises(SystemExit):
        read_bsf(p)


def test_read_scan_dispatches_on_magic_not_extension(make_csf, make_bsf, tmp_path):
    csf = make_csf(csf_record(1, 2, 3, 0, 1, 0))
    renamed = tmp_path / "actually_csf.bsf"
    renamed.write_bytes(csf.read_bytes())
    assert read_scan(renamed)[0] == [(1, 2, 3)]
    assert read_scan(make_bsf([(1, 2, 3, 0, 1, 0)], name="a.csf"))[0] == [(1, 2, 3)]


def test_read_scan_unknown_magic(tmp_path):
    p = tmp_path / "x.dat"
    p.write_bytes(zlib.compress(b"hello"))
    with pytest.raises(SystemExit, match="unknown file type"):
        read_scan(p)
