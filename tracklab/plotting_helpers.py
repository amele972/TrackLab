import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.ndimage import gaussian_filter


def plot_track_skeleton(vertices, normals):
    """3D Wireframe Plot"""
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    # Subsample for speed if mesh is huge
    verts_sub = vertices if len(vertices) < 5000 else vertices[::2]

    mesh = Poly3DCollection(verts_sub, alpha=0.1, edgecolor="k", linewidths=0.05)
    mesh.set_facecolor((0.2, 0.8, 0.2, 0.1))  # Transparent Green
    ax.add_collection3d(mesh)

    # Limits
    pts = vertices.reshape(-1, 3)
    x_lim = np.max(np.abs(pts[:, 0]))
    y_lim = np.max(np.abs(pts[:, 1]))
    z_min = np.min(pts[:, 2])

    limit = max(x_lim, y_lim) * 1.1
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_zlim(z_min, 0)

    ax.set_xlabel("X (µm)")
    ax.set_ylabel("Y (µm)")
    ax.set_zlabel("Depth (µm)")
    ax.set_title("3D Track Geometry")
    plt.show()


def plot_upper_surface_colored(vertices, normals, brightness, blur_sigma=2.0):
    """
    Simulates Microscope View:
    1. Render triangles in Greyscale (Transmission).
    2. Apply Gaussian Blur (Diffraction Limit).
    """
    # Setup Canvas
    pts = vertices.reshape(-1, 3)
    max_dim = np.max(np.abs(pts[:, :2])) * 1.2

    # Use standard matplotlib figure to rasterize
    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)

    # Sort by depth (Deepest first)
    z_centers = np.mean(vertices[:, :, 2], axis=1)
    sort_idx = np.argsort(z_centers)

    verts_sorted = vertices[sort_idx, :, :2]  # XY only
    bright_sorted = brightness[sort_idx]

    # Create Collection
    coll = PolyCollection(
        verts_sorted, array=bright_sorted, cmap="gray", edgecolors="face"
    )
    coll.set_clim(0.0, 1.0)  # 0=Black, 1=White

    ax.add_collection(coll)
    ax.set_xlim(-max_dim, max_dim)
    ax.set_ylim(-max_dim, max_dim)
    ax.set_aspect("equal")
    ax.axis("off")

    # Render to buffer
    fig.canvas.draw()
    data = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    plt.close(fig)

    # Extract channel (Greyscale) & Blur
    img = data[:, :, 0].astype(float)
    img_blurred = gaussian_filter(img, sigma=blur_sigma)

    # Display Result
    fig_final, ax_final = plt.subplots(figsize=(7, 6))
    cax = ax_final.imshow(
        img_blurred,
        extent=[-max_dim, max_dim, -max_dim, max_dim],
        cmap="gray",
        origin="upper",
        vmin=0,
        vmax=255,
    )

    ax_final.set_title("Simulated Microscope View (Green Light)")
    ax_final.set_xlabel("X (µm)")
    ax_final.set_ylabel("Y (µm)")
    plt.colorbar(cax, label="Transmission Intensity")
    plt.show()


from mpl_toolkits.mplot3d import Axes3D  # noqa
import os


def plot_trisurf(
    df_surface, xcol, ycol, zcol, title, outdir=None, save_svg=True, dpi=600
):
    """
    Plots a 3D trisurf surface for given columns and saves both normal and inverted axes versions.

    Parameters
    ----------
    df_surface : pd.DataFrame
        Dataframe containing data.
    xcol, ycol, zcol : str
        Column names for x, y, z axes.
    title : str
        Title for the plot.
    outdir : str, optional
        Directory to save SVGs. If None, figure is not saved.
    save_svg : bool
        Whether to save figures as SVG.
    dpi : int
        Resolution for saved figure.
    """

    for invert in [False, True]:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")
        x = df_surface[xcol]
        y = df_surface[ycol]
        z = df_surface[zcol]

        ax.plot_trisurf(
            x, y, z, cmap="plasma", alpha=0.8, linewidth=0.2, edgecolor="none"
        )
        ax.set_xlabel("Proton Energy (MeV)")
        ax.set_ylabel("Proton Angle (°)")
        ax.set_zlabel(title)
        ax.set_title(title)
        ax.view_init(elev=30, azim=-60)

        if invert:
            ax.invert_xaxis()
            ax.invert_yaxis()
            suffix = "_inverted"
        else:
            suffix = "_normal"

        if save_svg and outdir is not None:
            os.makedirs(outdir, exist_ok=True)
            filename = os.path.join(outdir, f"trisurf_{zcol}{suffix}.svg")
            plt.savefig(filename, format="svg", dpi=dpi)

        plt.close(fig)
