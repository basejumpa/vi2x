import pytest

from tests.conftest import csf_record
from vi2x import __version__
from vi2x.cli import main
from vi2x.readers import read_scan


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_missing_arguments():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_read_csf_runs(make_csf):
    f = make_csf(
        csf_record(100, 200, 300, 5, 1, 0),
        csf_record(10, 20, 336, 5, 2, 0, run=[(1, 2), (1, 2)]),
    )
    pts, ws, ed = read_scan(f)
    assert pts == [(100, 200, 300), (10, 20, 336), (9, 18, 336), (8, 16, 336)]
    assert ws == [0] * 4
    assert ed == [(1, 5), (2, 5), (2, 6), (2, 7)]


@pytest.fixture
def csf(make_csf):
    return make_csf(
        csf_record(0, 0, 0, 0, 1, 0),
        csf_record(100, 0, 36, 0, 2, 1, run=[(-1, 0)]),
        csf_record(0, 100, 72, 0, 3, 2),
    )


@pytest.mark.parametrize("src", ["csf", "grid_bsf"])
@pytest.mark.parametrize("ext", ["ply", "glb"])
def test_convert(request, tmp_path, src, ext):
    inp = request.getfixturevalue(src)
    out = tmp_path / f"out.{ext}"
    assert main([str(inp), str(out)]) == 0
    assert out.read_bytes().startswith(b"ply\n" if ext == "ply" else b"glTF")


def test_extension_is_case_insensitive(grid_bsf, tmp_path):
    out = tmp_path / "OUT.PLY"
    assert main([str(grid_bsf), str(out)]) == 0
    assert out.read_bytes().startswith(b"ply\n")


def test_summary_output_and_extent(grid_bsf, tmp_path, capsys):
    out = tmp_path / "o.ply"
    main([str(grid_bsf), str(out), "--up", "z", "--view", "-y", "--scale", "1"])
    stdout = capsys.readouterr().out
    assert "4 points" in stdout
    assert "X -0.500..0.500" in stdout
    assert "Z 0.000..36.000" in stdout


def test_default_up_is_input_y_output_z(grid_bsf, tmp_path, capsys):
    main([str(grid_bsf), str(tmp_path / "o.ply")])
    stdout = capsys.readouterr().out
    # default up=y: raw y span becomes the Z extent, starting at 0
    assert "Z 0.000.." in stdout

def test_heads_filter(csf, tmp_path, capsys):
    main([str(csf), str(tmp_path / "o.ply"), "--heads", "1"])
    assert "2 points" in capsys.readouterr().out


def test_heads_filter_no_match(csf, tmp_path):
    with pytest.raises(SystemExit, match="no points"):
        main([str(csf), str(tmp_path / "o.ply"), "--heads", "7"])


def test_stride(csf, tmp_path, capsys):
    main([str(csf), str(tmp_path / "o.ply"), "--stride", "2"])
    assert "2 points" in capsys.readouterr().out


def test_glb_per_head_nodes(csf, tmp_path):
    out = tmp_path / "o.glb"
    main([str(csf), str(out)])
    data = out.read_bytes()
    for name in (b"head_0", b"head_1", b"head_2"):
        assert name in data


def test_glb_merge_heads(csf, tmp_path):
    out = tmp_path / "o.glb"
    main([str(csf), str(out), "--merge-heads"])
    data = out.read_bytes()
    assert b'"points"' in data
    assert b"head_0" not in data


def test_ascii_ply(grid_bsf, tmp_path):
    out = tmp_path / "o.ply"
    main([str(grid_bsf), str(out), "--ascii"])
    assert b"format ascii 1.0" in out.read_bytes()


def test_bad_up_view(grid_bsf, tmp_path):
    with pytest.raises(SystemExit):
        main([str(grid_bsf), str(tmp_path / "o.ply"), "--up", "x", "--view", "-x"])

def test_bad_extension(grid_bsf, tmp_path):
    with pytest.raises(SystemExit, match="extension"):
        main([str(grid_bsf), str(tmp_path / "out.obj")])


def test_output_without_extension(grid_bsf, tmp_path):
    with pytest.raises(SystemExit, match="extension"):
        main([str(grid_bsf), str(tmp_path / "out")])


def test_unknown_input_type(tmp_path):
    p = tmp_path / "x.csf"
    p.write_bytes(b"abc" + bytes(300))
    with pytest.raises(SystemExit, match="unknown file type"):
        main([str(p), str(tmp_path / "o.ply")])


def test_empty_scan(make_bsf, tmp_path):
    with pytest.raises(SystemExit, match="no points"):
        main([str(make_bsf([])), str(tmp_path / "o.ply")])


# ------------------------------------------------------------------ mesh
@pytest.fixture
def sphere_bsf(make_bsf):
    import math

    rows = []
    for e in range(40):
        for d in range(60):
            th, ph = math.pi * (e + 0.5) / 40, 2 * math.pi * d / 60
            r = 5000
            rows.append(
                (
                    10000 + round(r * math.sin(th) * math.cos(ph)),
                    10000 + round(r * math.sin(th) * math.sin(ph)),
                    10000 + round(r * math.cos(th)),
                    d,
                    e + 1,
                    0,
                )
            )
    return make_bsf(rows)


@pytest.mark.parametrize("ext", ["ply", "glb"])
def test_mesh_sphere(sphere_bsf, tmp_path, capsys, ext):
    pytest.importorskip("open3d")
    out = tmp_path / f"m.{ext}"
    assert main([str(sphere_bsf), str(out), "--mesh", "--voxel", "0.02", "--depth", "6"]) == 0
    stdout = capsys.readouterr().out
    assert "triangles" in stdout
    assert out.read_bytes().startswith(b"ply\n" if ext == "ply" else b"glTF")


def test_mesh_without_open3d(sphere_bsf, tmp_path, monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "open3d", None)
    with pytest.raises(SystemExit, match="Open3D"):
        main([str(sphere_bsf), str(tmp_path / "m.ply"), "--mesh"])
