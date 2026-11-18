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
    main([str(grid_bsf), str(out), "--axes", "x,y,z", "--scale", "1", "--no-center"])
    stdout = capsys.readouterr().out
    assert "4 points" in stdout
    assert "X 1000.000..1001.000" in stdout
    assert "Z 3000.000..3036.000" in stdout


def test_default_axes_stand_person_along_y(grid_bsf, tmp_path, capsys):
    main([str(grid_bsf), str(tmp_path / "o.ply")])
    stdout = capsys.readouterr().out
    # raw z span 36 units = 3.6 mm becomes the Y extent, floor-centred (min 0)
    assert "Y 0.000..0.004" in stdout


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


def test_center_modes_accepted(grid_bsf, tmp_path):
    for mode in ("none", "bbox", "mean", "floor"):
        assert main([str(grid_bsf), str(tmp_path / "o.ply"), "--center", mode]) == 0


def test_rotate_changes_extent(grid_bsf, tmp_path, capsys):
    args = [str(grid_bsf), str(tmp_path / "o.ply"), "--axes", "x,y,z", "--scale", "1"]
    main(args + ["--no-center"])
    plain = capsys.readouterr().out
    main(args + ["--no-center", "--rotate", "0,0,180"])
    rotated = capsys.readouterr().out
    assert "X 1000.000..1001.000" in plain
    assert "X -1001.000..-1000.000" in rotated


@pytest.mark.parametrize("rotate", ["1,2", "a,b,c", "1,2,3,4", ""])
def test_bad_rotate(grid_bsf, tmp_path, rotate):
    with pytest.raises(SystemExit, match="--rotate"):
        main([str(grid_bsf), str(tmp_path / "o.ply"), "--rotate", rotate])


def test_bad_axes(grid_bsf, tmp_path):
    with pytest.raises(SystemExit):
        main([str(grid_bsf), str(tmp_path / "o.ply"), "--axes", "x,x,y"])


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
def test_mesh_ply(grid_bsf, tmp_path, capsys):
    out = tmp_path / "m.ply"
    assert main([str(grid_bsf), str(out), "--mesh", "--max-edge", "1", "--ascii"]) == 0
    assert b"element face 2" in out.read_bytes()
    assert "4 vertices, 2 triangles" in capsys.readouterr().out


def test_mesh_glb_per_head(grid_bsf, tmp_path):
    out = tmp_path / "m.glb"
    main([str(grid_bsf), str(out), "--mesh", "--max-edge", "1"])
    data = out.read_bytes()
    assert b"head_0" in data
    assert b'"mode":4' in data


def test_mesh_glb_merged(grid_bsf, tmp_path):
    out = tmp_path / "m.glb"
    main([str(grid_bsf), str(out), "--mesh", "--max-edge", "1", "--merge-heads"])
    assert b'"mesh"' in out.read_bytes()


def test_mesh_multiple_heads_merge_offsets(make_bsf, tmp_path):
    rows = [
        (1000 + d, 2000, 3000 + 36 * e, d, e + 1, w)
        for w in (0, 1)
        for e in range(2)
        for d in range(2)
    ]
    out = tmp_path / "m.ply"
    main([str(make_bsf(rows)), str(out), "--mesh", "--max-edge", "1", "--ascii"])
    lines = out.read_text(encoding="ascii").splitlines()
    assert "element vertex 8" in lines
    assert "element face 4" in lines
    faces = [list(map(int, ln.split()[1:])) for ln in lines if ln.startswith("3 ")]
    assert all(0 <= i < 8 for f in faces for i in f)
    assert any(i >= 4 for f in faces for i in f)  # second head's indices are offset


def test_mesh_too_small_max_edge(grid_bsf, tmp_path):
    with pytest.raises(SystemExit, match="mesh is empty"):
        main([str(grid_bsf), str(tmp_path / "m.ply"), "--mesh", "--max-edge", "0.0000001"])


def test_mesh_with_stride_rejected(grid_bsf, tmp_path):
    with pytest.raises(SystemExit, match="stride"):
        main([str(grid_bsf), str(tmp_path / "m.ply"), "--mesh", "--stride", "2"])
