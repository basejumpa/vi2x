import json
import struct

import pytest

from vi2x.writers import write_glb, write_ply

TRI = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 2.0, 3.0)]


def parse_glb(data: bytes):
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert (magic, version, length) == (b"glTF", 2, len(data))
    jlen, jtype = struct.unpack_from("<I4s", data, 12)
    assert jtype == b"JSON"
    gltf = json.loads(data[20 : 20 + jlen])
    off = 20 + jlen
    blen, btype = struct.unpack_from("<I4s", data, off)
    assert btype == b"BIN\0"
    return gltf, data[off + 8 : off + 8 + blen]


def test_ply_binary(tmp_path):
    p = tmp_path / "a.ply"
    write_ply(p, TRI)
    data = p.read_bytes()
    head, _, body = data.partition(b"end_header\n")
    assert b"format binary_little_endian 1.0" in head
    assert b"element vertex 3" in head
    assert b"element face" not in head
    assert len(body) == 3 * 12
    assert struct.unpack("<9f", body) == (0, 0, 0, 1, 0, 0, 0, 2, 3)


def test_ply_ascii(tmp_path):
    p = tmp_path / "a.ply"
    write_ply(p, TRI, ascii_=True)
    text = p.read_text(encoding="ascii")
    assert "format ascii 1.0" in text
    assert text.splitlines()[-1] == "0.000000 2.000000 3.000000"


def test_ply_with_faces_binary(tmp_path):
    p = tmp_path / "a.ply"
    write_ply(p, TRI, faces=[(0, 1, 2)])
    head, _, body = p.read_bytes().partition(b"end_header\n")
    assert b"element face 1" in head
    assert b"property list uchar int vertex_indices" in head
    assert body[36:] == struct.pack("<B3i", 3, 0, 1, 2)


def test_ply_with_faces_ascii(tmp_path):
    p = tmp_path / "a.ply"
    write_ply(p, TRI, ascii_=True, faces=[(0, 1, 2)])
    assert p.read_text(encoding="ascii").splitlines()[-1] == "3 0 1 2"


def test_ply_empty(tmp_path):
    p = tmp_path / "a.ply"
    write_ply(p, [])
    assert b"element vertex 0" in p.read_bytes()


def test_glb_points(tmp_path):
    p = tmp_path / "a.glb"
    write_glb(p, [("cloud", TRI, None)])
    gltf, binary = parse_glb(p.read_bytes())
    assert gltf["asset"]["version"] == "2.0"
    assert gltf["scenes"] == [{"nodes": [0]}]
    assert gltf["nodes"] == [{"name": "cloud", "mesh": 0}]
    prim = gltf["meshes"][0]["primitives"][0]
    assert prim["mode"] == 0
    assert "indices" not in prim
    acc = gltf["accessors"][prim["attributes"]["POSITION"]]
    assert acc["count"] == 3
    assert acc["min"] == [0, 0, 0]
    assert acc["max"] == [1, 2, 3]
    assert "materials" not in gltf
    assert gltf["buffers"][0]["byteLength"] == len(binary)
    assert struct.unpack_from("<9f", binary) == (0, 0, 0, 1, 0, 0, 0, 2, 3)


def test_glb_triangles(tmp_path):
    p = tmp_path / "a.glb"
    write_glb(p, [("mesh", TRI, [(0, 1, 2)])])
    gltf, binary = parse_glb(p.read_bytes())
    prim = gltf["meshes"][0]["primitives"][0]
    assert prim["mode"] == 4
    assert prim["material"] == 0
    assert gltf["materials"][0]["doubleSided"] is True
    idx = gltf["accessors"][prim["indices"]]
    assert (idx["componentType"], idx["count"], idx["type"]) == (5125, 3, "SCALAR")
    view = gltf["bufferViews"][idx["bufferView"]]
    assert view["target"] == 34963
    assert struct.unpack_from("<3I", binary, view["byteOffset"]) == (0, 1, 2)


def test_glb_multiple_groups_have_distinct_nodes_and_views(tmp_path):
    p = tmp_path / "a.glb"
    write_glb(p, [("head_0", TRI, None), ("head_3", TRI[:2], None)])
    gltf, binary = parse_glb(p.read_bytes())
    assert [n["name"] for n in gltf["nodes"]] == ["head_0", "head_3"]
    assert gltf["scenes"][0]["nodes"] == [0, 1]
    offsets = [v["byteOffset"] for v in gltf["bufferViews"]]
    assert offsets == [0, 36]
    assert all(o % 4 == 0 for o in offsets)
    assert len(binary) % 4 == 0


def test_glb_chunks_are_4_byte_aligned(tmp_path):
    p = tmp_path / "a.glb"
    write_glb(p, [("x", TRI[:1], None)])
    data = p.read_bytes()
    jlen = struct.unpack_from("<I", data, 12)[0]
    assert jlen % 4 == 0
    assert len(data) % 4 == 0


@pytest.mark.parametrize("ascii_", [False, True])
def test_ply_vertex_count_matches(tmp_path, ascii_):
    p = tmp_path / "a.ply"
    pts = [(float(i), 0.0, 0.0) for i in range(17)]
    write_ply(p, pts, ascii_=ascii_)
    assert b"element vertex 17" in p.read_bytes()
