"""Readers for Vitronic / Human Solutions ``.csf`` and ``.bsf`` scan files.

See ``docs/formats.md`` for the (reverse engineered) format description.

Every reader returns ``(points, head_ids, grid)`` where ``points`` is a list of raw
``(x, y, z)`` tuples, ``head_ids`` the head/pass id ``w`` of each point and ``grid`` the
``(scan line e, pixel column d)`` of each point.
"""

from __future__ import annotations

import struct
import sys
import zlib
from collections.abc import Collection
from pathlib import Path

HEADER_SIZE = 256

Scan = tuple[list[tuple[int, int, int]], list[int], list[tuple[int, int]]]


def read_scan(path: str | Path, heads: Collection[int] | None = None) -> Scan:
    """Read a .csf or .bsf file; the type is detected from the magic bytes."""
    with open(path, "rb") as f:
        magic = f.read(3)
    if magic == b"csf":
        return read_csf(path, heads)
    if magic == b"bsf":
        return read_bsf(path, heads)
    raise SystemExit(f"{path}: unknown file type (magic {magic!r}), expected csf or bsf")


def read_bsf(path: str | Path, heads: Collection[int] | None = None) -> Scan:
    data = Path(path).read_bytes()
    body = len(data) - HEADER_SIZE
    if data[:3] != b"bsf" or body < 0 or body % 12:
        raise SystemExit(f"{path}: not a valid bsf file")
    pts, ws, ed = [], [], []
    for x, y, z, d, e, w in struct.iter_unpack(">6H", data[HEADER_SIZE:]):
        if heads is None or w in heads:
            pts.append((x, y, z))
            ws.append(w)
            ed.append((e, d))
    return pts, ws, ed


def read_csf(path: str | Path, heads: Collection[int] | None = None) -> Scan:
    data = Path(path).read_bytes()
    if data[:3] != b"csf":
        raise SystemExit(f"{path}: not a csf file (magic {data[:3]!r})")
    (size,) = struct.unpack_from("<I", data, HEADER_SIZE)
    try:
        o = zlib.decompress(data[HEADER_SIZE + 4 :])
    except zlib.error as ex:
        raise SystemExit(f"{path}: zlib error: {ex}") from ex
    if len(o) != size:
        print(f"warning: size mismatch ({len(o)} != {size})", file=sys.stderr)

    pts: list[tuple[int, int, int]] = []
    ws: list[int] = []
    ed: list[tuple[int, int]] = []
    i, n = 0, len(o)
    unpack = struct.unpack_from
    while i < n:
        if i + 13 > n:
            raise SystemExit(f"truncated record at offset {i}")
        x, y, z, d, e, w = unpack(">hhhHHH", o, i)
        c = o[i + 12]
        i += 13
        keep = heads is None or w in heads
        if keep:
            pts.append((x, y, z))
            ws.append(w)
            ed.append((e, d))
        if c:
            cx, cy, dd = x, y, d
            while True:
                if i + 2 > n:
                    raise SystemExit(f"truncated run at offset {i}")
                a, b = o[i], o[i + 1]
                i += 2
                if a == 0 and b == 0:
                    break
                cx -= a - 256 if a > 127 else a
                cy -= b - 256 if b > 127 else b
                dd += 1
                if keep:
                    pts.append((cx, cy, z))
                    ws.append(w)
                    ed.append((e, dd))
            if c == 7:
                i += 2
    return pts, ws, ed
