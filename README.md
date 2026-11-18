# vi2x

`vi2x` reads a `.csf` or `.bsf` file (the type is detected from the magic bytes;
3D body-scanner point cloud, header strings `HUMAN SOLUTIONS` / `XX-SMART_XX`, i.e.
Vitronic VITUS Smart XX) and writes a point cloud or triangle mesh as **PLY** or **GLB**
with user-defined scaling, axis mapping and rotation.

- Python 3.10+, standard library only (no numpy needed)
- Tested on `out.csf` (430,169 points, 1.761 m tall person with default settings)

## Installation

Install it as a command line tool with [uv](https://docs.astral.sh/uv/):

```sh
# from GitHub
uv tool install git+https://github.com/basejumpa/vi2x

# or from a local checkout
uv tool install .
```

Then run `vi2x` from anywhere. Other useful commands:

```sh
uv tool upgrade vi2x     # update to the latest version
uv tool uninstall vi2x   # remove it
uvx --from git+https://github.com/basejumpa/vi2x vi2x --help   # run once, no install
```

If `vi2x` is not found after installing, run `uv tool update-shell` and restart the terminal.

## Usage

```
vi2x INPUT.(csf|bsf) OUTPUT.(ply|glb) [options]
```

Run it through uv with `uv run vi2x ...`, or `python -m vi2x ...`.
The output format is chosen by the file extension.

| Option                             | Default  | Meaning                                                                                                                                                                                           |
|------------------------------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--scale F` (alias `--unit-scale`) | `0.0001` | Multiplier for the raw values. Raw unit is assumed to be 0.1 mm, so the default gives metres. Use `0.1` for mm, `1` for raw units.                                                                |
| `--axes a,b,c`                     | `x,-z,y` | Which source axis becomes output X, Y, Z, with optional `-` to flip. Each of x, y, z must appear once. The default makes the person stand along +Y (glTF convention). `x,y,z` keeps the raw axes. |
| `--rotate RX,RY,RZ`                | `0,0,0`  | Additional rotation in degrees about the *output* X, Y, Z axes, applied in that order (X, then Y, then Z).                                                                                        |
| `--center MODE`                    | `floor`  | `floor`: centre X/Z, lowest point on Y at 0. `bbox`: centre bounding box. `mean`: centre on average point. `none`: no translation.                                                                |
| `--no-center`                      | –        | Same as `--center none`.                                                                                                                                                                          |
| `--heads 1,2`                      | all      | Keep only points of these head/pass ids (field `w`, 0–7).                                                                                                                                         |
| `--stride N`                       | `1`      | Keep every Nth point (decimation).                                                                                                                                                                |
| `--merge-heads`                    | off      | GLB only: put all heads into a single mesh. By default every head becomes its own node and mesh named `head_<id>`, so heads can be shown/hidden separately in a viewer.                           |
| `--mesh`                           | off      | Write a triangle mesh instead of a point cloud (triangulates the scan grid of each head). Not combinable with `--stride`.                                                                         |
| `--max-edge M`                     | `0.01`   | With `--mesh`: drop triangles with an edge longer than M metres. Larger = fewer holes but bridges across gaps.                                                                                    |
| `--ascii`                          | off      | Write ASCII PLY instead of binary little-endian.                                                                                                                                                  |
| `--version`                        | –        | Print the version.                                                                                                                                                                                |

Order of operations: axis remap/flip → scale → rotation → centering.

### Examples

```
# metres, upright, feet on the floor (defaults)
vi2x out.csf out.ply

# GLB, person turned around by 180° about the vertical axis
vi2x out.csf out.glb --rotate 0,180,0

# raw axes and raw units, no translation, small ASCII file for inspection
vi2x out.csf test.ply --axes x,y,z --scale 1 --no-center --ascii --stride 100

# millimetres
vi2x out.csf out_mm.ply --scale 0.1

# triangle mesh
vi2x out.csf out.glb --mesh
```

### Mesh output

`--mesh` turns the scan into triangles. Every head is a range image: its points sit on a grid
of scan line `e` and pixel column `d`. Neighbouring grid cells are joined into two triangles
(split along the shorter diagonal), or one triangle if only three corners exist. Triangles with
an edge longer than `--max-edge` are dropped, so gaps and depth jumps at silhouettes are not
bridged. Points that end up in no triangle are not written.

- **PLY:** one vertex list and a `vertex_indices` face list for all heads together.
- **GLB:** one TRIANGLES mesh per head (`head_<id>`, `--merge-heads` for a single mesh), with a
  neutral double-sided material. There are no normals; viewers compute flat shading.
- The heads overlap, so the surface is several partly overlapping patches, not one watertight
  mesh, and the mesh is not welded between heads. For `out.csf` with defaults: 415,425 vertices
  and 801,832 triangles in about 10 s.
- A smaller `--max-edge` gives more holes, a larger one bridges more gaps. The curtain sheet
  (head 1) is meshed too; use `--heads` to leave it out.
- Triangle winding is consistent within a head, but which side is "front" depends on `--axes`;
  that is why the GLB material is double sided.

### How to remove specific heads

A scan consists of up to eight heads (head/pass ids 0–7), and some of them are not part of the
person, e.g. head 1 is the background sheet. To keep only the heads you want:

1. **Convert everything once as GLB** so you can see the heads as separate datasets:

   ```sh
   vi2x out.csf all_heads.glb
   ```

   Every head becomes its own node and mesh named `head_<id>` (`head_0`, `head_1`, ...).
   Open the file in a glTF viewer, hide or show the nodes one by one and note which ids
   belong to the person and which are background or noise.

2. **Convert again with `--heads`** and list the ids you want to keep:

   ```sh
   # keep heads 0, 2 and 4, drop all others
   vi2x out.csf person.ply --heads 0,2,4
   vi2x out.csf person.glb --heads 0,2,4
   ```

`--heads` is a keep list: every head that is not named is removed. There is no option to
exclude heads, so to remove head 1 from a scan with heads 0–7, list the other seven
(`--heads 0,2,3,4,5,6,7`). It works for point clouds and for `--mesh`, and the printed
point count shows how many points remain.

A PLY file has no notion of heads (all points end up in one vertex list), so use GLB for the
inspection step. The `--heads` filter itself works with either output format.

### Orientation hints

The facing direction after the default mapping is unverified. If the person
looks away from you in your viewer, add `--rotate 0,180,0`. If the person lies
down or is mirrored, change `--axes` (e.g. `x,z,y`, `-x,-z,y`).
In the raw data **z increases towards the feet**, which is why the default
uses `-z` as the vertical axis.

### Output

- **PLY**: header + `float x y z` per vertex, no colours/normals. With `--mesh`, also faces
  (see [Mesh output](#mesh-output)).
- **GLB**: glTF 2.0. Point clouds use one primitive of mode 0 (POINTS) per mesh, with
  `POSITION` as float32 VEC3 with min/max set; `--mesh` uses TRIANGLES with indices and a
  double-sided material. Y-up, metres by default.

Not supported: colours, normals.

## File formats

The `.csf` and `.bsf` formats are reverse engineered; see
[docs/formats.md](docs/formats.md) for the description.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                      # create .venv and install project + dev tools
uv run pytest                # run tests
uv run ruff check .          # lint
uv run ruff format .         # format
uv build                     # build sdist and wheel
```

## License

[MIT](LICENSE)
