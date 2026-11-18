"""Surface reconstruction with Open3D (optional dependency, install with the `mesh` extra)."""

from __future__ import annotations

import numpy as np

Mesh = tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]


MIN_PIECE = 0.05  # keep connected pieces with at least this fraction of the largest one's triangles


def _open3d():
    try:
        import open3d as o3d
    except ImportError as exc:
        raise SystemExit(
            f"--mesh needs a working Open3D ({exc}). Install it with: "
            "pip install 'vi2x[mesh]' (uv sync --extra mesh). On Linux it also needs the system "
            "libraries libegl1, libgl1 and libgomp1."
        ) from None
    return o3d


def poisson_mesh(pts, voxel: float, depth: int, trim: float) -> Mesh:
    """Fuse all points into one watertight-ish surface (Poisson reconstruction).

    voxel: grid size for thinning the cloud, in output units (0 = no thinning).
    depth: octree depth of the reconstruction; higher = finer detail, more memory.
    trim:  fraction (0..1) of the lowest-density vertices to remove, which cuts away the
           surface Poisson invents over gaps and around the scan borders.
    Normals are estimated from the neighbourhood, propagated consistently over the cloud and
    finally pointed away from the vertical axis through the centroid.
    """
    o3d = _open3d()
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.asarray(pts, dtype=np.float64))
    if voxel > 0:
        pcd = pcd.voxel_down_sample(voxel)
    spacing = voxel if voxel > 0 else float(np.mean(pcd.compute_nearest_neighbor_distance()))
    pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=spacing * 4, max_nn=30))
    pcd.orient_normals_consistent_tangent_plane(30)
    p, n = np.asarray(pcd.points), np.asarray(pcd.normals)
    outward = p[:, :2] - p[:, :2].mean(axis=0)  # horizontal, away from the body axis
    if float(np.sum(n[:, :2] * outward)) < 0:
        pcd.normals = o3d.utility.Vector3dVector(-n)
    mesh, density = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=depth)
    if trim > 0 and len(density):
        mesh.remove_vertices_by_mask(np.asarray(density) < np.quantile(density, trim))
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    # drop floating debris: connected pieces much smaller than the main body
    labels, counts, _ = mesh.cluster_connected_triangles()
    labels, counts = np.asarray(labels), np.asarray(counts)
    if len(counts):
        small = counts[labels] < max(counts) * MIN_PIECE
        mesh.remove_triangles_by_mask(small)
    mesh.remove_unreferenced_vertices()
    verts = [tuple(map(float, v)) for v in np.asarray(mesh.vertices)]
    faces = [tuple(map(int, f)) for f in np.asarray(mesh.triangles)]
    return verts, faces
