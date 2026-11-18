"""Builders for tiny synthetic scan files."""

import struct
import zlib

import pytest

HEADER = bytes(256)


def csf_record(x, y, z, d, e, w, run=None, code=None):
    """One CSF record. `run` is a list of (dx, dy) pairs; `code` defaults to 6 if run else 0."""
    if code is None:
        code = 6 if run is not None else 0
    rec = struct.pack(">hhhHHHB", x, y, z, d, e, w, code)
    if run is not None:
        for dx, dy in run:
            rec += struct.pack(">bb", dx, dy)
        rec += b"\x00\x00"
        if code == 7:
            rec += b"\x00\x00"
    return rec


@pytest.fixture
def make_csf(tmp_path):
    def make(*records, name="t.csf", size=None):
        payload = b"".join(records)
        p = tmp_path / name
        p.write_bytes(
            b"csf"
            + HEADER[3:]
            + struct.pack("<I", len(payload) if size is None else size)
            + zlib.compress(payload)
        )
        return p

    return make


@pytest.fixture
def make_bsf(tmp_path):
    def make(rows, name="t.bsf"):
        p = tmp_path / name
        p.write_bytes(b"bsf" + HEADER[3:] + b"".join(struct.pack(">6H", *r) for r in rows))
        return p

    return make


@pytest.fixture
def grid_bsf(make_bsf):
    """2x2 grid on one head. Raw (x, y, z): z grows by 36 per scan line, x by 1 per column."""
    return make_bsf(
        [(1000 + d, 2000, 3000 + 36 * e, d, e + 1, 0) for e in range(2) for d in range(2)]
    )
