# The CSF and BSF file formats

Both formats are produced by the Vitronic / Human Solutions VITUS Smart XX body
scanner (header strings `HUMAN SOLUTIONS` / `Vitronic`, `XX-SMART_XX`).

The formats are reverse engineered (no vendor spec was available). The CSF decoder
reproduces exactly the point count of the sibling uncompressed `.bsf` file (440,800
points for the original scan) and consumes the file completely, and the rendered cloud
shows a plausible human body. Details marked *(inferred)* are not confirmed.

Both formats share the same 256-byte header layout and are distinguished by their magic
bytes (`csf` / `bsf`).

## Header (256 bytes, both formats)

| Offset | Content (example)                                                           |
|--------|-----------------------------------------------------------------------------|
| 0      | magic `csf` (`63 73 66`) or `bsf`                                           |
| 3      | version byte (`06`)                                                         |
| 4      | format byte (`03`) *(meaning inferred)*                                     |
| 16     | date string `06.03.2010`, zero terminated                                   |
| 65     | a few small binary fields (`01 04`, a timestamp-like value) *(not decoded)* |
| 128    | vendor string (`HUMAN SOLUTIONS` in CSF, `Vitronic` in BSF)                 |
| 144    | scanner/system string `XX-SMART_XX` (BSF additionally has `intern`)         |
| rest   | zero padding / further unknown fields                                       |

## CSF

### File structure

```
offset  size  content
0       256   header
256     4     uint32 little endian: size of the uncompressed payload
260     ...   one zlib stream (starts with 78 9c); decompresses to exactly that size
```

### Payload

A sequence of records, all multi-byte values **big endian**:

| Size | Field | Meaning                                                                                                |
|------|-------|--------------------------------------------------------------------------------------------------------|
| 2    | `x`   | int16                                                                                                  |
| 2    | `y`   | int16                                                                                                  |
| 2    | `z`   | int16 – height; constant within one scan line `e`, increases by 36 per line; positive towards the feet |
| 2    | `d`   | uint16 – pixel column of the laser stripe (0–283)                                                      |
| 2    | `e`   | uint16 – scan line index (1–573); non-decreasing within a head                                         |
| 2    | `w`   | uint16 – head/pass id 0–7 *(meaning inferred)*; records come grouped by `w`                            |
| 1    | `c`   | run code: `0`, `6` or `7`                                                                              |

Then, depending on `c`:

- `c == 0`: the record is a single point; next record follows immediately.
- `c == 6` or `7`: a run of further points follows as pairs of signed bytes
  `(dx, dy)`. Each pair yields one more point
  `d += 1`, `x -= dx`, `y -= dy`, `z` unchanged (same scan line, neighbouring
  pixel column), with deltas relative to the previous point of the run.
  The pair `00 00` terminates the run.
  If `c == 7`, two further zero bytes follow the terminator *(purpose unknown, always `00 00`)*.

Pseudo code:

```python
while i < len(o):
    x, y, z, d, e, w = struct.unpack_from(">hhhHHH", o, i)
    c = o[i + 12]
    i += 13
    emit(x, y, z)
    if c:
        cx, cy = x, y
        while True:
            dx, dy = struct.unpack_from(">bb", o, i)
            i += 2
            if dx == 0 and dy == 0:
                break
            cx -= dx
            cy -= dy
            emit(cx, cy, z)
        if c == 7:
            i += 2
```

## BSF

After the 256-byte header (magic `bsf`) follow **uncompressed** records of six
big-endian `uint16`: `x, y, z, d, e, w` (12 bytes each) — the same fields as in CSF, but
unsigned and without run compression.

```
offset  size  content
0       256   header
256     12*n  records: >HHHHHH  (x, y, z, d, e, w)
```

### Relation to CSF

In the sample, the BSF and `out.csf.orig` contain exactly the same 440,800 points: the
keys (`w`, `e`, `d`) match one to one. They are not bit-identical: `z` differs by 0 or 1,
`x`/`y` by up to about ±20 units (~2 mm) with no constant offset, so the two were
probably produced by different processing stages *(inferred)*.

The BSF coordinates are unsigned and all positive (raw scanner coordinates), while CSF
coordinates are signed and centred (offset about −5416, −5978, −10766 in x, y, z). The
BSF records are in acquisition order *(inferred)*, not grouped by head as in the CSF.

## Units and coordinate system

- Raw values appear to be **0.1 mm**: z spans about 17,600 units, matching a
  1.76 m person. This is an assumption; use `--scale` to override.
- z is the vertical axis (feet = larger z). x/y are the horizontal axes. The
  cloud also contains background points (a "shadow" visible in the preview
  image) in addition to the body.
- Points form laser stripes, so the cloud looks like horizontal contour lines
  rather than a dense surface.

## Known gaps

- Meaning of header bytes beyond the strings and date.
- Exact meaning of `w` (laser head vs. scan pass) and of the two zero bytes after code 7.
- Whether `x`/`y` are in a calibrated scanner coordinate system or sensor coordinates; the
  facing direction of the person in the raw axes.
- `out.csf` has 10,631 fewer points (430,169) than the original (440,800). 10,345 of the
  removed points belong to head 1 (the background sheet), 242 to head 5 and the rest to
  heads 0, 2, 4, 6, 7; everything else is unchanged except a shift of the origin.
  Presumably a background cleanup by some tool.
