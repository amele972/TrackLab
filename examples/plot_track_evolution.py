import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# Ensure tracklab can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tracklab import (
    build_vrint_interpolator,
    calculate_track_parameters,
    get_vt_model,
    load_srim_data,
)


def main():
    interps, _ = load_srim_data()
    vt_model = get_vt_model()

    ion = "protons"
    energies = [1.2, 2.2, 2.8]
    # The user wants to display angles as 0, 30, 45 (relative to normal)
    # Internally, tracklab uses angles relative to surface plane (where normal is 90)
    display_angles = [0.0, 30.0, 45.0]
    vb = 4.73
    times = np.linspace(1.5, 10.0, 100)

    # Increase base font sizes
    plt.rcParams.update({"font.size": 14})

    fig, axes = plt.subplots(3, 3, figsize=(22, 14), sharex=True)

    # Overall Title to clarify layout
    fig.suptitle("Proton Track Evolution", fontsize=24, fontweight="bold", y=0.98)

    colors = ["r", "g", "b"]

    for row, disp_angle in enumerate(display_angles):
        tracklab_angle = 90.0 - disp_angle
        for energy, color in zip(energies, colors):
            F_interp = build_vrint_interpolator(
                vt_model=vt_model, ion=ion, energy=energy, vb=vb
            )

            major_axes = []
            minor_axes = []
            depths = []

            for t in times:
                res = calculate_track_parameters(
                    energy=energy,
                    angle_deg=tracklab_angle,
                    vb=vb,
                    time_etching=t,
                    range_interpolator=interps[ion],
                    F_interp=F_interp,
                    ion=ion,
                    vt_model=vt_model,
                )

                ma = res["major_axis_um"]
                mi = res["minor_axis_um"]
                d = res["depth_um"]

                # If track has disappeared or invalid
                if res["status"] == "invalid":
                    ma, mi, d = np.nan, np.nan, np.nan

                major_axes.append(ma)
                minor_axes.append(mi)
                depths.append(d)

            axes[row, 0].plot(
                times, major_axes, label=f"{energy} MeV", color=color, lw=3
            )
            axes[row, 1].plot(
                times, minor_axes, label=f"{energy} MeV", color=color, lw=3
            )
            axes[row, 2].plot(times, depths, label=f"{energy} MeV", color=color, lw=3)

        # Clarify row labels on the y-axis without explicit "Row X" text
        axes[row, 0].set_ylabel(
            f"{disp_angle}° Incident Angle\n\nMajor Axis (µm)",
            fontsize=16,
            fontweight="bold",
        )
        axes[row, 1].set_ylabel("Minor Axis (µm)", fontsize=16)
        axes[row, 2].set_ylabel("Depth (µm)", fontsize=16)

        for col in range(3):
            axes[row, col].grid(True)
            # Add vertical dashed lines at specific etching times: 2h 50m, 4h 30m, 7h
            for vline in [2 + 50 / 60, 4.5, 7.0]:
                axes[row, col].axvline(
                    x=vline, color="k", linestyle="--", alpha=0.7, lw=2
                )
            axes[row, col].tick_params(axis="both", which="major", labelsize=14)
            if row == 0:
                if col == 0:
                    axes[row, col].set_title(
                        "Major Axis", fontsize=20, fontweight="bold", pad=15
                    )
                if col == 1:
                    axes[row, col].set_title(
                        "Minor Axis", fontsize=20, fontweight="bold", pad=15
                    )
                if col == 2:
                    axes[row, col].set_title(
                        "Depth", fontsize=20, fontweight="bold", pad=15
                    )
            if row == 2:  # Last row for x labels
                axes[row, col].set_xlabel(
                    "Etching Time (h)", fontsize=18, fontweight="bold"
                )
            axes[row, col].legend(fontsize=14)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "track_evolution.png"
    )
    plt.savefig(output_path, dpi=300)
    print(f"Plot saved to {output_path}")


if __name__ == "__main__":
    main()
