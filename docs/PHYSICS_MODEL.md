# TrackLab — Physical and Optical Models

TrackLab simulates the physical formation and chemical etching of charged particle tracks in poly-allyl diglycol carbonate (PADC) detectors, commercially known as CR-39, and models their visual appearance under a transmission optical microscope.

---

## 1. Track Structure Generation

The generation of the 3D track structure in TrackLab proceeds through the following computational steps:

### A. Range Determination from SRIM Data
When an ion of a given initial energy $E$ enters the detector, its projected range $R(E)$ represents the total trajectory length. TrackLab loads precomputed range-energy tables derived from SRIM (Stopping and Range of Ions in Matter) databases:
1. The package reads `Rang_CR_all_ions_SRIM.dat` which contains range tables for all supported ions (protons, alpha particles, lithium, carbon, oxygen).
2. The ranges are evaluated at run-time using a monotone piecewise cubic Hermite interpolating polynomial (PCHIP) to avoid non-physical oscillations.
3. If the ion energy exceeds the database range, the range is extended using the Bragg-Kleeman power law:
   $$R(E) = a \cdot E^{p}$$
   where $p \approx 1.77$ for protons and light ions.

### B. The Etch Rate Ratio $V(y)$ function
Chemical etching removes the undamaged bulk detector material at a constant rate $v_B$ (bulk etch rate, $\mu\text{m/h}$). Along the particle path, radiation damage increases the local dissolution rate to $v_T$ (track etch rate, $\mu\text{m/h}$). 

The geometry of the etched track is governed by the reduced etch-rate ratio:
$$V(y) = \frac{v_T(y)}{v_B} \ge 1$$
where $y = R - x$ is the **residual range** (the remaining distance along the particle trajectory to its stopping point, where $x$ is the coordinate along the track axis).

TrackLab implements distinct $V(y)$ parameterizations for different ion species:

#### Proton Model (Nikezi&cacute; / Hermsdorf)
For protons, the standard formulation is a double-exponential fit:
$$V(y) = 1 + \left(a_1 e^{-a_2 y} + a_3 e^{-a_4 y}\right)\left(1 - e^{-a_5 y}\right)$$
This satisfies the boundary condition $V(0) = 1$ (the track etch rate equals the bulk etch rate at the stopping point). The standard parameters are:
$$a_1 = 0.4306, \quad a_2 = 0.00737, \quad a_3 = 1.0559, \quad a_4 = 0.1072, \quad a_5 = 1.412$$

#### Light Ion Model
For heavier ions (Lithium, Carbon, Oxygen), a Broken Power Law (BPL) model is used to fit the experimental data:
$$V(y) = 1 + \frac{A \cdot y^{\alpha}}{1 + \left(\frac{y}{y_0}\right)^{\alpha+\beta}}$$
where $A$, $y_0$, $\alpha$, and $\beta$ are parameters fitted to the digitized experimental data from Dörschel et al.

#### Helium Ion (Alpha) Models
For alpha particles, TrackLab supports 7 alternative parameterizations from the literature (e.g., Durrani & Bull, Brun et al., Yu et al., Hermsdorf, Green et al.). The default is Brun et al. (1999):
$$V(y) = 1 + e^{-a_1 y + a_4} - e^{-a_2 y + a_3} + e^{a_3} - e^{a_4}$$

### C. Integrating Wavefront Propagation
To find the position reached by the etchant along the track axis, we precompute a cumulative integration function $F(u)$ of the inverse etch-rate ratio:
$$F(u) = \int_0^u \frac{1}{V(\xi)} d\xi$$
The integral of the track etch rate along a segment $[u_a, u_b]$ is then efficiently computed by interpolation:
$$\int_{u_a}^{u_b} \frac{1}{V(\xi)} d\xi = F(u_b) - F(u_a)$$

For a track originating at depth $z_{\text{origin}}$ relative to the etched surface, the etchant must first remove the bulk material to reach the track origin. This introduces a delay before track etching begins:
$$t_{\text{delay}} = \frac{z_{\text{origin}}}{v_B}$$
The effective etching time available for track formation is therefore:
$$t_{\text{eff}} = \max(0, t - t_{\text{delay}})$$

The etched distance $d_{\text{etch}}$ along the track is found by solving:
$$\int_0^{d_{\text{etch}}} \frac{1}{v_T(R-x)} dx = t_{\text{eff}}$$

At any point $x \le d_{\text{etch}}$, the time $t(x)$ when the etchant first reached $x$ relative to the start of track etching is:
$$t(x) = \int_0^x \frac{1}{v_T(R-\xi)} d\xi$$

The remaining etching time available for lateral growth at that point is $t_{\text{over}} = t_{\text{eff}} - t(x)$. The radius of the resulting circular envelope at $x$ is:
$$r_{\text{wall}}(x) = v_B \cdot t_{\text{over}} \cdot \cos(\delta)$$
where $\delta = \arcsin(1/V(R-x))$ is the local critical angle.

Tracks can originate from both the top and bottom surfaces of the detector. For tracks originating from the bottom surface (e.g., in a transmission configuration), the simulation effectively mirrors the geometry to model etching from the reverse side.

Combining the lateral spheres along the trajectory constructs the 3D track wall profile.

---

## 2. Microscope View and Optical Simulation

The optical module simulates how light passes through the 3D track structure under transmission light microscopy to generate the final synthetic microscope image.

```
          [ Light Rays (Condenser Cone) ]
                         |
                         v
       [ Plastic Detector (CR-39, n = 1.504) ]
             \                       /
              \   3D Track Mesh     /
               \___________________/
                         |
                         v  Snell's Law Refraction
                       [ Air ]
                         |
                         v  Objective NA Aperture Filter
                [ Brightness Matrix ]
                         |
                         v
           [ XY Microscope View Image ]
```

### A. From Track Mesh to Image Space
1. The 3D track wall profile is discretized into a 3D surface mesh containing $N_z \times N_{\alpha}$ quadrilateral faces.
2. For each face, stable local orientation is defined by computing surface normal vectors using diagonal cross products, avoiding numerical singularities at high curvature zones (such as near the conical track tip).
3. The detector is assumed to have a refractive index of $n_{\text{plastic}} = 1.504$ (CR-39) and is surrounded by air ($n_{\text{air}} = 1.0$).

### B. 3D Vector Snell's Law and Ray Tracing
Light rays originating from the microscope's illumination system enter the detector from below.
* **Vector Refraction**: For each ray with incident vector $\mathbf{I}$ hitting a mesh face with normal vector $\mathbf{N}$, the refracted ray vector $\mathbf{T}$ entering the air pocket inside the track pit is calculated using the full 3D vector form of Snell's Law:
  $$\mathbf{T} = \eta \mathbf{I} + \left( \eta \cos(\theta_i) - \sqrt{1 - \eta^2 (1 - \cos^2(\theta_i))} \right) \mathbf{N}$$
  where $\eta = n_{\text{plastic}}/n_{\text{air}}$ and $\cos(\theta_i) = -\mathbf{N} \cdot \mathbf{I}$.
* **Total Internal Reflection (TIR)**: If the term inside the square root is negative, total internal reflection occurs. The ray is completely reflected back into the plastic and does not reach the microscope objective, appearing dark (black).

### C. Condenser Cone Averaging and Numerical Aperture Filter
* **Condenser NA**: Instead of simulating a single vertical light ray (which results in unrealistic, sharp black/white transitions), TrackLab models the physical microscope condenser. It samples a distribution of rays (default 32 rays) within a cone defined by the Condenser Numerical Aperture ($\text{NA}_{\text{cond}} = 0.25$).
* **Fresnel Transmittance**: For refracted rays, the transmitted intensity is scaled using the Fresnel equations, accounting for polarization and angle-dependent loss.
* **Objective NA Filter**: Only rays that exit the track pit and fall within the collection angle of the objective lens (defined by $\text{NA}_{\text{obj}} = 0.45$) contribute to the final image brightness. Rays refracted at high angles are discarded.

Averaging the transmitted intensities of all cone rays for each mesh face yields the **Brightness Matrix**, which is then mapped to the 2D XY plane to render a high-fidelity synthetic microscope image.

---

## 3. References

The physical framework in TrackLab derives from the legacy TRACK_P and TRACK_VISION codes, with track etch rate parametrizations incorporating extensive literature models. 

1. **TRACK_P (Proton Tracks):** D. Nikezic and K. N. Yu, *"A computer program TRACK_p for studying proton tracks in PADC detectors"*, SoftwareX, 5, 74–79, (2016). [DOI: 10.1016/j.softx.2016.04.006](https://doi.org/10.1016/j.softx.2016.04.006)
2. **TRACK_VISION (Optical Simulation):** D. Nikezic and K. N. Yu, *"Computer program TRACK_vision for simulating optical appearance of etched tracks in CR-39 nuclear track detectors"*, Computer Physics Communications, 178(8), 591–595, (2008). [DOI: 10.1016/j.cpc.2007.11.011](https://doi.org/10.1016/j.cpc.2007.11.011)
3. **Proton $V(R')$ model:** D. Hermsdorf, *"Measurement and comparative evaluation of the sensitivity V for protons and hydrogen isotopes registration in PADC detectors of type CR-39"*, Radiation Measurements 44, 806–812, (2009).
4. **Alpha particle $V(R')$ model:** D. Hermsdorf, *"Evaluation of the sensitivity function V for registration of $\alpha$-particles in PADC CR-39 solid state nuclear track detector material"*, Radiation Measurements 44, 283–288, (2009).
