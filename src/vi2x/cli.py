"""Command line interface for vi2x."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from vi2x import __version__
from vi2x.geometry import build_mesh, parse_axes, rot_matrix, transform
from vi2x.readers import read_scan
from vi2x.writers import write_glb, write_ply


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="vi2x",
        description="Convert a Vitronic .csf or .bsf scan to a PLY or GLB point cloud or mesh.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Order of operations: axis remap/flip -> scale -> rotation -> centering.",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("input", help="input .csf or .bsf file")
    ap.add_argument("output", help="output file; format chosen by extension (.ply or .glb)")
    ap.add_argument(
        "--scale",
        "--unit-scale",
        type=float,
        default=1e-4,
        dest="scale",
        help="multiplier applied to raw values (default 0.0001 = raw 0.1 mm -> metres)",
    )
    ap.add_argument(
        "--axes",
        default="x,-z,y",
        help="output axes as source axes with optional sign, e.g. 'x,-z,y' "
        "(default; makes the person stand along +Y, glTF convention). "
        "Use 'x,y,z' to keep the raw axes.",
    )
    ap.add_argument(
        "--rotate",
        default="0,0,0",
        metavar="RX,RY,RZ",
        help="extra rotation in degrees about the output X, Y, Z axes, applied in that "
        "order (default 0,0,0), e.g. 0,180,0 to turn the person around",
    )
    ap.add_argument(
        "--center",
        choices=["none", "bbox", "mean", "floor"],
        default="floor",
        help="translate the cloud: bbox centre, mean, or 'floor' (centre X/Z, lowest "
        "point on the 2nd axis at 0; default)",
    )
    ap.add_argument("--no-center", action="store_true", help="same as --center none")
    ap.add_argument("--heads", help="only keep these head/pass ids, e.g. 0,1,2")
    ap.add_argument(
        "--merge-heads",
        action="store_true",
        help="GLB only: put all heads into one mesh (default: one node/mesh 'head_<id>' per head)",
    )
    ap.add_argument(
        "--mesh",
        action="store_true",
        help="write a triangle mesh instead of a point cloud (triangulates the scan "
        "grid of each head; not combinable with --stride)",
    )
    ap.add_argument(
        "--max-edge",
        type=float,
        default=0.01,
        metavar="M",
        help="with --mesh: drop triangles with an edge longer than this many metres "
        "(default 0.01). Larger = fewer holes but bridges across gaps.",
    )
    ap.add_argument("--ascii", action="store_true", help="write ASCII PLY instead of binary")
    ap.add_argument("--stride", type=int, default=1, help="keep every Nth point (decimation)")
    return ap


def _merge(meshes):
    verts, faces, off = [], [], 0
    for w in sorted(meshes):
        v, f = meshes[w]
        verts += v
        faces += [(i + off, j + off, k + off) for i, j, k in f]
        off += len(v)
    return verts, faces


def main(argv: Sequence[str] | None = None) -> int:
    a = build_parser().parse_args(argv)

    ext = a.output.lower().rsplit(".", 1)[-1]
    if ext not in ("ply", "glb"):
        raise SystemExit("output extension must be .ply or .glb")
    try:
        rot = [float(v) for v in a.rotate.split(",")]
        if len(rot) != 3:
            raise ValueError
    except ValueError:
        raise SystemExit("--rotate needs three numbers, e.g. 0,180,0") from None
    heads = {int(h) for h in a.heads.split(",")} if a.heads else None

    if a.mesh and a.stride > 1:
        raise SystemExit("--mesh cannot be combined with --stride")
    pts, ws, ed = read_scan(a.input, heads)
    if a.stride > 1:
        pts, ws = pts[:: a.stride], ws[:: a.stride]
    if not pts:
        raise SystemExit("no points")
    pts = transform(
        pts, a.scale, parse_axes(a.axes), rot_matrix(*rot), "none" if a.no_center else a.center
    )
    by: dict[int, list[int]] = {}
    for i, w in enumerate(ws):
        by.setdefault(w, []).append(i)
    ntri = 0
    if a.mesh:
        # --max-edge is in metres (1 m = 10000 raw units); output units are raw * scale
        max_edge = a.max_edge * 10000 * a.scale
        meshes = {w: build_mesh(pts, ed, by[w], max_edge) for w in sorted(by)}
        ntri = sum(len(f) for _, f in meshes.values())
        if ntri == 0:
            raise SystemExit("mesh is empty; try a larger --max-edge")
        if ext == "ply" or a.merge_heads:
            verts, faces = _merge(meshes)
            if ext == "ply":
                write_ply(a.output, verts, a.ascii, faces)
            else:
                write_glb(a.output, [("mesh", verts, faces)])
            pts = verts
        else:
            write_glb(
                a.output,
                [(f"head_{w}",) + meshes[w] for w in sorted(meshes) if meshes[w][1]],
            )
            pts = [p for m in meshes.values() for p in m[0]]
    elif ext == "ply":
        write_ply(a.output, pts, a.ascii)
    elif a.merge_heads:
        write_glb(a.output, [("points", pts, None)])
    else:
        write_glb(a.output, [(f"head_{w}", [pts[i] for i in by[w]], None) for w in sorted(by)])
    mins = [min(p[k] for p in pts) for k in range(3)]
    maxs = [max(p[k] for p in pts) for k in range(3)]
    if a.mesh:
        print(f"{len(pts)} vertices, {ntri} triangles -> {a.output}")
    else:
        print(f"{len(pts)} points -> {a.output}")
    print("extent: " + "  ".join(f"{'XYZ'[k]} {mins[k]:.3f}..{maxs[k]:.3f}" for k in range(3)))
    return 0
