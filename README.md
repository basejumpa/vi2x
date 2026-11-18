# vi2x

`vi2x` reads a `.csf` or `.bsf` file (the type is detected from the magic bytes;
3D body-scanner point cloud, header strings `HUMAN SOLUTIONS` / `XX-SMART_XX`, i.e.
Vitronic VITUS Smart XX) and writes a point cloud or triangle mesh as **PLY** or **GLB**
with user-defined scaling and axis mapping.

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
| `--up AXIS` | `-z` | Input axis that points up (`x`, `y` or `z`, optional sign). Raw z increases towards the feet, hence the default `-z`. |
| `--view AXIS` | `x` | Input axis that points towards the viewer who looks at the screen (e.g. `-y`). |
| `--heads 1,2`                      | all      | Keep only points of these head/pass ids (field `w`, 0–7).                                                                                                                                         |
| `--stride N`                       | `1`      | Keep every Nth point (decimation).                                                                                                                                                                |
| `--merge-heads`                    | off      | GLB only: put all heads into a single mesh. By default every head becomes its own node and mesh named `head_<id>`, so heads can be shown/hidden separately in a viewer.                           |
| `--mesh` | off | Write one fused triangle mesh instead of a point cloud: Poisson surface reconstruction (Open3D) over all heads together. Needs the `mesh` extra. |
| `--voxel M` | `0.003` | With `--mesh`: thin the cloud to one point per cube of M metres (0 = no thinning). |
| `--depth N` | `9` | With `--mesh`: Poisson octree depth. Higher = finer detail, more memory and time. |
| `--trim F` | `0.05` | With `--mesh`: remove this fraction (0..1) of the least supported vertices, i.e. surface invented over gaps. |
| `--ascii`                          | off      | Write ASCII PLY instead of binary little-endian.                                                                                                                                                  |
| `--version`                        | –        | Print the version.                                                                                                                                                                                |

The output always has **up = +Z** and **view (towards the viewer) = -Y**, so X points to the viewer's right. The origin is moved to the lowest centre point: centre of the lowest slice (the lowest 2 % of the height, i.e. the feet) in X/Y, minimum at Z = 0.

Order of operations: axis remap → scale → origin shift.

### Examples

```
# metres, upright, feet on the floor (defaults)
vi2x out.csf out.ply

# GLB, with the viewer on the opposite side (person turned around)
vi2x out.csf out.glb --view -x

# input with up = -z and the viewer on the +x side, raw units, small ASCII file
vi2x out.csf test.ply --up=-z --view x --scale 1 --ascii --stride 100

# millimetres
vi2x out.csf out_mm.ply --scale 0.1

# triangle mesh
vi2x out.csf out.glb --mesh
```

### Mesh output

`--mesh` needs [Open3D](https://www.open3d.org/), which is an optional extra:

```
uv tool install "vi2x[mesh] @ git+https://github.com/basejumpa/vi2x"   # or: uv sync --extra mesh
```

On Linux, Open3D also needs the system libraries `libegl1`, `libgl1` and `libgomp1`\n(`sudo apt-get install libegl1 libgl1 libgomp1`).

All heads are fused into **one** surface, so the result is a single mesh and not overlapping
patches per head:

1. The points are thinned to one per `--voxel` cube.
2. Normals are estimated, made consistent over the cloud and pointed away from the body axis.
3. Poisson surface reconstruction (`--depth`) builds the surface.
4. The `--trim` fraction of the least supported vertices is cut away (surface invented over
   gaps and scan borders), degenerate and non-manifold triangles are removed, and floating
   pieces much smaller than the main body are dropped.

For `out.csf` with `--heads 0,2,3,4,5,6,7` this takes about 30 s and gives about 200,000
vertices and 400,000 triangles as a single connected, edge-manifold piece. Use `--heads` to
leave out the curtain sheet (head 1). `--stride` thins the cloud before meshing. GLB output
has one mesh named `mesh`; `--merge-heads` does not apply to meshes. The surface is smooth
and may be slightly closed up at thin gaps; raise `--depth` or lower `--voxel` for more
detail.

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

Tell vi2x which input axes are up and towards the viewer with `--up` and `--view`; the output is always up = +Z, view = -Y. If the person looks away from you in your viewer, flip `--view` (e.g. `--view -x`).
In the raw data **z increases towards the feet**, so a raw-axes scan has `--up=-z`. Write negative axes as `--up=-z`.

### Output

- **PLY**: header + `float x y z` per vertex, no colours/normals. With `--mesh`, also faces
  (see [Mesh output](#mesh-output)).
- **GLB**: glTF 2.0. Point clouds use one primitive of mode 0 (POINTS) per mesh, with
  `POSITION` as float32 VEC3 with min/max set; `--mesh` uses TRIANGLES with indices and a
  double-sided material. Z-up, metres by default.

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
