# TrackLab v1.0 — Physics Model

## Overview

TrackLab models the chemical etching of nuclear tracks in CR-39 
(poly-allyl-diglycol carbonate) solid-state nuclear track detectors.

When a charged particle traverses CR-39, it creates a trail of radiation damage.
During chemical etching (typically NaOH at 70°C), the damaged material dissolves
faster than the undamaged bulk, revealing the track as an etch pit observable
under an optical microscope.

## Key Physical Quantities

### Bulk Etch Rate VB (µm/h)

The rate at which undamaged detector material is dissolved. This is **constant**
for a given etching session (depends on NaOH concentration, temperature, detector batch).

| Ion | Default VB (µm/h) | Notes |
|-----|-----------|-------|
| protons | 4.70 | Standard NaOH etching |
| Li, C, O, alpha | 1.73 | Calibration VB for experimental datasets |

### Track Etch Rate VT(y) (µm/h)

The rate at which damaged material along the track is dissolved. VT depends on
the local radiation damage density, which varies along the track.

`y = R - x` is the **residual range** (µm), where R is the total projected range 
and x is the distance etched from the surface along the track axis.

### Etch Rate Ratio V(y) = VT(y) / VB

The dimensionless ratio ≥ 1 that governs all track geometry. **TrackLab v1.0 treats V(y) as the primary physical model.** All geometric dimensions are derived from this ratio.

## V(y) Models

### Protons — Dorschel Analytical Model

```
V(y) = 1 + (a₁·exp(-a₂·y) + a₃·exp(-a₄·y)) · (1 - exp(-a₅·y))
```

Parameters (Dorschel et al., 1997) are calibrated for protons in CR-39. This model captures the behavior where V peaks near the Bragg peak (small y).

### Alpha Particles — Multiple Analytical Models

TrackLab v1.0 supports **7 different alpha particle models** (configurable in `config.py`):
1. **Durrani & Bull** (1987)
2. **Brun et al.** (1999)
3. **Yu et al.** (2005)
4. **Al-Jubbori** (2020)
5. **Hermsdorf** (2009)
6. **Green et al.** (1982)
7. **Yu et al.** (2005a,b)

### Heavy Ions (Li, C, O) — Broken Power Law (BPL)

```
V(y) = 1 + A · y^α / (1 + (y/y₀)^(α+β))
```

Parameters {A, y₀, α, β} are fitted from experimental profiles stored in `Data_ions.xlsx`.

## Track Geometry Calculation (Z-Slice Engine)

> [!IMPORTANT]
> **Z-Slice Parametric Geometry**: Unlike legacy versions that used angular subdivision (prone to "beak" artifacts), v1.0 uses a high-fidelity **Z-Slice logic**. The track is modeled as a solid of revolution, which is then analytically intersected with horizontal planes (Z-slices) from the surface down to the tip. This ensures perfect continuity and numerical stability even at extreme overetching.

### Induction Range induct_range

The distance along the track before etching begins to exceed VB:
```
V(R - induct_range) · sin(θ) = 1
```
This is found via 10-step bisection to ensure sub-µm accuracy.

### Etched Distance etched_dist

The distance along the track that has been etched in time t:
```
∫₀^etched_dist 1/VT(R-x) dx = t
```

### Track Wall Profile

At each position x along the etched segment, the track wall radius is:
```
wall_r(x) = overetch · cos(δ)
```
where δ = arcsin(1/V(R-x)).

### Major/Minor Axes and Depth

- **Major Axis**: The longest dimension of the track opening on the detector surface.
- **Minor Axis**: The width of the opening perpendicular to the major axis.
- **Depth**: The maximum absolute penetration below the **etched surface**. 

> [!TIP]
> **Surface Anchoring**: v1.0 automatically anchors simulated tracks to the minimum depth of experimental data, ensuring that the simulated "z=0" plane perfectly matches the experimental detector surface.

## Optical Model (v2.0)

Track brightness is computed using 3D vector ray-tracing:
1. **Z-Slice mesh generation** (N_z × N_alpha quads)
2. **Face normals** via diagonal cross products (stable at the tip)
3. **Snell's Law** refraction at the CR-39/air interface
4. **Obliquity-corrected Fresnel transmittance** (DEO formula)
5. **Condenser Cone Averaging**: Simulates real illumination by averaging 32 rays per face across the condenser NA.
6. **Projected Surface**: Area-weighted sum of transmittance used for integrated optical density calculations.
