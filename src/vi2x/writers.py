"""PLY and GLB writers."""

from __future__ import annotations

import json
import struct
from pathlib import Path

GENERATOR = "vi2x"


def write_ply(path: str | Path, pts, ascii_: bool = False, faces=None) -> None:
    hdr = [
        "ply",
        "format ascii 1.0" if ascii_ else "format binary_little_endian 1.0",
        f"comment converted by {GENERATOR}",
        f"element vertex {len(pts)}",
        "property float x",
        "property float y",
        "property float z",
    ]
    if faces is not None:
        hdr += [f"element face {len(faces)}", "property list uchar int vertex_indices"]
    hdr.append("end_header")
    with open(path, "wb") as f:
        f.write(("\n".join(hdr) + "\n").encode("ascii"))
        if ascii_:
            f.write("".join(f"{x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in pts).encode("ascii"))
            if faces is not None:
                f.write("".join(f"3 {i} {j} {k}\n" for i, j, k in faces).encode("ascii"))
        else:
            f.write(b"".join(struct.pack("<3f", *p) for p in pts))
            if faces is not None:
                f.write(b"".join(struct.pack("<B3i", 3, *t) for t in faces))


def write_glb(path: str | Path, groups) -> None:
    """Write a GLB.

    `groups` is a list of (name, vertices, faces-or-None); each group becomes one node +
    mesh with that name. Without faces it is a POINTS primitive, with faces a TRIANGLES
    primitive (double sided material).
    """
    binary = b""
    nodes, meshes, accessors, views, materials = [], [], [], [], []
    for name, g, faces in groups:
        data = b"".join(struct.pack("<3f", *p) for p in g)
        views.append(
            {"buffer": 0, "byteOffset": len(binary), "byteLength": len(data), "target": 34962}
        )
        binary += data  # float32 VEC3 = 12 bytes, so offsets stay 4-byte aligned
        accessors.append(
            {
                "bufferView": len(views) - 1,
                "componentType": 5126,
                "count": len(g),
                "type": "VEC3",
                "min": [min(p[k] for p in g) for k in range(3)],
                "max": [max(p[k] for p in g) for k in range(3)],
            }
        )
        prim = {"attributes": {"POSITION": len(accessors) - 1}, "mode": 0}
        if faces is not None:
            idx = b"".join(struct.pack("<3I", *t) for t in faces)
            views.append(
                {"buffer": 0, "byteOffset": len(binary), "byteLength": len(idx), "target": 34963}
            )
            binary += idx
            accessors.append(
                {
                    "bufferView": len(views) - 1,
                    "componentType": 5125,
                    "count": len(faces) * 3,
                    "type": "SCALAR",
                }
            )
            if not materials:
                materials.append(
                    {
                        "name": "scan",
                        "doubleSided": True,
                        "pbrMetallicRoughness": {
                            "baseColorFactor": [0.8, 0.8, 0.8, 1],
                            "metallicFactor": 0.0,
                            "roughnessFactor": 0.9,
                        },
                    }
                )
            prim.update({"indices": len(accessors) - 1, "mode": 4, "material": 0})
        meshes.append({"name": name, "primitives": [prim]})
        nodes.append({"name": name, "mesh": len(meshes) - 1})
    gltf = {
        "asset": {"version": "2.0", "generator": GENERATOR},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(binary)}],
    }
    if materials:
        gltf["materials"] = materials
    js = json.dumps(gltf, separators=(",", ":")).encode("utf8")
    js += b" " * (-len(js) % 4)
    binary += b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(js), b"JSON") + js)
        f.write(struct.pack("<I4s", len(binary), b"BIN\0") + binary)
