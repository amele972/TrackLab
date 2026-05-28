"""
lut_engine.py — TrackLab Proton v2.0
=========================================
LUTEngine: a self-contained wrapper around a pre-computed reference dataset
(Mode-1 CSV) that exposes every fast-simulation capability in one place.

All public methods accept either scalar or array-like inputs and return
plain dicts or pandas DataFrames so they can be used from both the CLI
and the GUI without any extra glue.

Public API
----------
LUTEngine(csv_path)                    Load LUT from Mode-1 CSV
  .query(energy, angle)                Single or vectorised forward lookup
  .process_fluka_file(...)             FLUKA batch → DataFrame
  .inverse_lookup(major, minor)        Measured axes → (E, θ) candidates
  .coverage_map()                      Which (E, θ) grid cells develop?
  .propagate_uncertainty(...)          Monte-Carlo uncertainty propagation
  .statistics(df)                      Summary stats for any result DataFrame
  .export_csv(df, path)                Save result DataFrame to CSV

Properties
----------
  .energy_range   (min, max) MeV
  .angle_range    (min, max) deg
  .n_points       int
  .is_loaded      bool
"""

import os
import numpy as np
import pandas as pd
from scipy.interpolate import griddata, LinearNDInterpolator, NearestNDInterpolator
from scipy.optimize import minimize
import warnings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stack(e, a):
    """Stack energy/angle arrays into (N,2) query array."""
    e = np.atleast_1d(np.asarray(e, dtype=float))
    a = np.atleast_1d(np.asarray(a, dtype=float))
    if e.shape != a.shape:
        e, a = np.broadcast_arrays(e, a)
    return np.column_stack([e.ravel(), a.ravel()]), e.shape


# ---------------------------------------------------------------------------
# LUTEngine
# ---------------------------------------------------------------------------

class LUTEngine:
    """
    Look-Up Table engine built from a Mode-1 reference CSV.

    Parameters
    ----------
    csv_path : str
        Path to the reference_dataset.csv produced by Mode 1.
    """

    # Columns that must exist in the CSV
    _REQUIRED = ['energy_MeV', 'angle_deg',
                 'major_axis_um', 'minor_axis_um',
                 'depth_um', 'black_part']

    # All output columns we interpolate (if present)
    _INTERP_COLS = {
        'major_axis_um':    'major_axis_um',
        'minor_axis_um':    'minor_axis_um',
        'depth_um':         'depth_um',
        'black_part':       'black_part',
        'total_surface':    'total_surface',
        'total_length_um':  'total_length_um',
        'projected_surface':'projected_surface',
        'mean_brightness':  'mean_brightness',
    }

    def __init__(self, csv_path: str):
        self._path       = csv_path
        self._df         = None          # full DataFrame
        self._xy         = None          # (N,2) array of (E, angle)
        self._interp     = {}            # param → scipy interpolator
        self._developed  = None          # boolean mask: which rows developed
        self._load(csv_path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"LUT file not found: {path}")

        df = pd.read_csv(path)

        # Accept alternative column names written by older Mode-1 outputs
        rename = {
            'proton_E_MeV':    'energy_MeV',
            'track_angle_deg': 'angle_deg',
            'maj_axes_um':     'major_axis_um',
            'min_axes_um':     'minor_axis_um',
            'track_depth_um':  'depth_um',
            'blackpart':       'black_part',
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        missing = [c for c in self._REQUIRED if c not in df.columns]
        if missing:
            raise ValueError(f"LUT CSV is missing columns: {missing}")

        # Derived columns
        if 'projected_surface' not in df.columns:
            df['projected_surface'] = (
                np.pi * df['major_axis_um'] * df['minor_axis_um'] / 4.0)
        if 'total_surface' not in df.columns:
            df['total_surface'] = df['projected_surface']

        df = df.fillna(0)

        # Developed mask
        if 'status' in df.columns:
            self._developed = df['status'].str.lower() == 'developed'
        else:
            self._developed = df['major_axis_um'] > 0

        self._df = df
        self._xy = df[['energy_MeV', 'angle_deg']].values.astype(float)

        # Build interpolators on developed rows only
        dev_xy = self._xy[self._developed]
        for col in self._INTERP_COLS:
            if col not in df.columns:
                continue
            z = df.loc[self._developed, col].values.astype(float)
            # Cubic griddata is used at query-time (rescaled); here we build
            # a linear ND interpolator for fast calls and a nearest-neighbour
            # fallback for points outside the convex hull.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    lin  = LinearNDInterpolator(dev_xy, z)
                    near = NearestNDInterpolator(dev_xy, z)
                    self._interp[col] = (lin, near)
                except Exception:
                    self._interp[col] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._df is not None

    @property
    def energy_range(self):
        return (float(self._df['energy_MeV'].min()),
                float(self._df['energy_MeV'].max()))

    @property
    def angle_range(self):
        return (float(self._df['angle_deg'].min()),
                float(self._df['angle_deg'].max()))

    @property
    def n_points(self) -> int:
        return len(self._df)

    @property
    def n_developed(self) -> int:
        return int(self._developed.sum())

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._df.copy()

    # ------------------------------------------------------------------
    # 1. Forward lookup (single or batch)
    # ------------------------------------------------------------------

    def query(self, energy, angle) -> dict:
        """
        Forward lookup: (energy, angle) → track parameters.

        Parameters
        ----------
        energy : float or array-like  — MeV
        angle  : float or array-like  — degrees

        Returns
        -------
        dict with keys:
            energy_MeV, angle_deg,
            major_axis_um, minor_axis_um, depth_um,
            black_part, total_surface, projected_surface,
            developed  (bool array)
        """
        xi, shape = _stack(energy, angle)

        result = {
            'energy_MeV': xi[:, 0],
            'angle_deg':  xi[:, 1],
        }

        for col, (lin, near) in self._interp.items():
            vals = lin(xi)
            # Fill NaN (outside convex hull) with nearest-neighbour
            nan_mask = np.isnan(vals)
            if np.any(nan_mask):
                vals[nan_mask] = near(xi[nan_mask])
            vals = np.clip(vals, 0, None)
            result[col] = vals

        # Developed flag: interpolate the boolean mask
        dev_float = self._developed.astype(float).values
        dev_lin  = LinearNDInterpolator(self._xy, dev_float)
        dev_near = NearestNDInterpolator(self._xy, dev_float)
        dev_vals = dev_lin(xi)
        nan_mask = np.isnan(dev_vals)
        if np.any(nan_mask):
            dev_vals[nan_mask] = dev_near(xi[nan_mask])
        result['developed'] = dev_vals > 0.5

        # Scalar → scalar output
        if shape == () or (len(shape) == 1 and shape[0] == 1):
            return {k: (float(v[0]) if v.dtype != bool else bool(v[0]))
                    for k, v in result.items()}

        return result

    def query_dataframe(self, energy, angle) -> pd.DataFrame:
        """Like query() but returns a DataFrame."""
        return pd.DataFrame(self.query(energy, angle))

    # ------------------------------------------------------------------
    # 2. FLUKA batch processing
    # ------------------------------------------------------------------

    def process_fluka_file(self, filepath: str,
                           col_energy_gev: int = 1,
                           col_x: int = 2,
                           col_y: int = 3,
                           col_z: int = 4,
                           col_cosz: int = 7,
                           skip_header: int = 1,
                           vb: float = 4.7,
                           z_ref: float = -0.55,
                           time_etching_ref: float = 2.83,
                           max_lines: int = None,
                           progress_callback=None) -> pd.DataFrame:
        """
        Process a FLUKA phase-space file using the LUT.

        Parameters
        ----------
        filepath         : str   — path to FLUKA .txt file
        col_*            : int   — 0-based column indices
        skip_header      : int   — header lines to skip
        vb               : float — bulk etch rate µm/h
        z_ref, time_etching_ref : used to compute etching time from Z position
        max_lines        : int or None — cap for large files
        progress_callback: callable(fraction: float) or None

        Returns
        -------
        pd.DataFrame with columns:
            energy_MeV, angle_deg, x_cm, y_cm, z_cm, cosz,
            etching_time_h, major_axis_um, minor_axis_um,
            depth_um, black_part, total_surface, developed
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)

        with open(filepath, 'r') as fh:
            raw = [l.strip() for l in fh if l.strip()]
        lines = raw[skip_header:]
        if max_lines is not None:
            lines = lines[:max_lines]
        total = len(lines)

        records = []
        skipped = 0

        for idx, line in enumerate(lines):
            parts = line.split()
            if len(parts) <= max(col_energy_gev, col_x, col_y, col_z, col_cosz):
                skipped += 1
                continue
            try:
                energy_gev = float(parts[col_energy_gev])
                x_cm  = float(parts[col_x])
                y_cm  = float(parts[col_y])
                z_cm  = float(parts[col_z])
                cosz  = float(parts[col_cosz])

                energy_mev = energy_gev * 1000.0
                cosz = np.clip(cosz, -1.0, 1.0)
                if energy_mev <= 0:
                    skipped += 1; continue

                angle_deg    = 90.0 - np.degrees(np.arccos(cosz))
                etching_time = time_etching_ref * abs(z_cm) / abs(z_ref) if z_ref != 0 else time_etching_ref
                if etching_time <= 0:
                    skipped += 1; continue

                records.append((energy_mev, angle_deg, x_cm, y_cm, z_cm,
                                 cosz, etching_time))
            except (ValueError, IndexError):
                skipped += 1

            if progress_callback and (idx + 1) % max(1, total // 50) == 0:
                progress_callback((idx + 1) / total)

        if progress_callback:
            progress_callback(1.0)

        if not records:
            return pd.DataFrame()

        rec_arr = np.array(records)
        energies = rec_arr[:, 0]
        angles   = rec_arr[:, 1]

        # Batch LUT query
        lut_res = self.query(energies, angles)

        df = pd.DataFrame({
            'energy_MeV':    energies,
            'angle_deg':     angles,
            'x_cm':          rec_arr[:, 2],
            'y_cm':          rec_arr[:, 3],
            'z_cm':          rec_arr[:, 4],
            'cosz':          rec_arr[:, 5],
            'etching_time_h': rec_arr[:, 6],
            **{k: lut_res[k] for k in ['major_axis_um', 'minor_axis_um',
                                        'depth_um', 'black_part',
                                        'total_length_um',
                                        'total_surface', 'projected_surface',
                                        'mean_brightness',
                                        'developed']},
        })
        df['skipped_total'] = skipped
        return df

    # ------------------------------------------------------------------
    # 3. Inverse problem: measured axes → (E, angle) candidates
    # ------------------------------------------------------------------

    def inverse_lookup(self, major_um: float, minor_um: float,
                       n_solutions: int = 5,
                       energy_hints=None,
                       angle_hints=None) -> pd.DataFrame:
        """
        Inverse problem: given measured track axes from microscope images,
        estimate the proton energy and angle.

        Uses a two-stage approach:
          Stage 1 — nearest-neighbour scan of the LUT to find coarse candidates
          Stage 2 — local optimisation around each candidate

        Parameters
        ----------
        major_um    : float — measured major axis (µm)
        minor_um    : float — measured minor axis (µm)
        n_solutions : int   — number of candidate solutions to return
        energy_hints, angle_hints : array-like or None — starting points for
                      the optimisation (overrides the automatic scan)

        Returns
        -------
        pd.DataFrame with columns:
            energy_MeV, angle_deg, major_axis_um, minor_axis_um,
            residual_um, confidence
        Sorted by residual (best match first).
        """
        dev_mask = self._developed.values
        dev_df   = self._df[dev_mask].copy()

        # Stage 1: score every LUT point by Euclidean distance in (major, minor) space
        dist = np.sqrt(
            (dev_df['major_axis_um'].values - major_um)**2 +
            (dev_df['minor_axis_um'].values - minor_um)**2)

        # Take top-K coarse candidates (spread across E-angle space)
        n_coarse = min(20, len(dev_df))
        top_idx  = np.argsort(dist)[:n_coarse]
        candidates = dev_df.iloc[top_idx][['energy_MeV', 'angle_deg']].values

        if energy_hints is not None and angle_hints is not None:
            hints = np.column_stack([np.atleast_1d(energy_hints),
                                     np.atleast_1d(angle_hints)])
            candidates = np.vstack([candidates, hints])

        # Stage 2: local optimisation from each coarse candidate
        e_min, e_max = self.energy_range
        a_min, a_max = self.angle_range

        def objective(x):
            e, a = x
            if not (e_min <= e <= e_max and a_min <= a <= a_max):
                return 1e9
            res = self.query(e, a)
            return (res['major_axis_um'] - major_um)**2 + \
                   (res['minor_axis_um'] - minor_um)**2

        solutions = []
        seen = []
        for c0 in candidates:
            try:
                opt = minimize(objective, c0,
                               method='Nelder-Mead',
                               options={'xatol': 0.01, 'fatol': 0.001,
                                        'maxiter': 500})
                e_sol, a_sol = opt.x
                # Clip to valid range
                e_sol = np.clip(e_sol, e_min, e_max)
                a_sol = np.clip(a_sol, a_min, a_max)
                res   = opt.fun

                # De-duplicate (within 0.1 MeV / 0.5°)
                duplicate = any(
                    abs(e_sol - s[0]) < 0.1 and abs(a_sol - s[1]) < 0.5
                    for s in seen)
                if not duplicate:
                    lut_q = self.query(e_sol, a_sol)
                    solutions.append({
                        'energy_MeV':    round(e_sol, 3),
                        'angle_deg':     round(a_sol, 2),
                        'major_axis_um': round(float(lut_q['major_axis_um']), 3),
                        'minor_axis_um': round(float(lut_q['minor_axis_um']), 3),
                        'residual_um':   round(float(np.sqrt(res)), 4),
                        'developed':     bool(lut_q['developed']),
                    })
                    seen.append((e_sol, a_sol))
            except Exception:
                pass

        if not solutions:
            return pd.DataFrame()

        sol_df = pd.DataFrame(solutions).sort_values('residual_um').head(n_solutions)
        # Confidence: normalised inverse residual
        r_max = sol_df['residual_um'].max()
        sol_df['confidence'] = (1.0 - sol_df['residual_um'] / (r_max + 1e-9)).round(3)
        return sol_df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # 4. Coverage / efficiency map
    # ------------------------------------------------------------------

    def coverage_map(self, n_energy: int = 80, n_angle: int = 45) -> dict:
        """
        Build a 2-D map showing which (E, θ) cells produce developed tracks.

        Returns
        -------
        dict with keys:
            E_grid    : (n_energy, n_angle)  energy values (MeV)
            A_grid    : (n_energy, n_angle)  angle values (deg)
            developed : (n_energy, n_angle)  bool array
            efficiency : float  — fraction of cells that develop
            major_grid : (n_energy, n_angle)  major axis µm (NaN where not developed)
            depth_grid : (n_energy, n_angle)  depth µm
            black_grid : (n_energy, n_angle)  black fraction
        """
        e_min, e_max = self.energy_range
        a_min, a_max = self.angle_range

        E = np.linspace(e_min, e_max, n_energy)
        A = np.linspace(a_min, a_max, n_angle)
        EG, AG = np.meshgrid(E, A, indexing='ij')   # (n_energy, n_angle)

        res = self.query(EG.ravel(), AG.ravel())

        dev_grid   = res['developed'].reshape(n_energy, n_angle)
        major_grid = res['major_axis_um'].reshape(n_energy, n_angle).astype(float)
        depth_grid = res['depth_um'].reshape(n_energy, n_angle).astype(float)
        black_grid = res['black_part'].reshape(n_energy, n_angle).astype(float)

        # Mask non-developed cells
        major_grid[~dev_grid] = np.nan
        depth_grid[~dev_grid] = np.nan
        black_grid[~dev_grid] = np.nan

        return {
            'E_grid':     EG,
            'A_grid':     AG,
            'developed':  dev_grid,
            'efficiency': float(dev_grid.mean()),
            'major_grid': major_grid,
            'depth_grid': depth_grid,
            'black_grid': black_grid,
        }

    # ------------------------------------------------------------------
    # 5. Uncertainty propagation (Monte Carlo)
    # ------------------------------------------------------------------

    def propagate_uncertainty(self,
                              energy: float,
                              angle: float,
                              sigma_energy: float = 0.05,
                              sigma_angle: float  = 1.0,
                              n_samples: int      = 2000,
                              seed: int           = 42) -> dict:
        """
        Monte-Carlo uncertainty propagation.

        Draws n_samples from Gaussian distributions around (energy, angle)
        with standard deviations (sigma_energy, sigma_angle) and queries
        the LUT for each sample.

        Parameters
        ----------
        energy, angle        : float — nominal values
        sigma_energy         : float — 1-σ energy uncertainty (MeV)
        sigma_angle          : float — 1-σ angle uncertainty (degrees)
        n_samples            : int   — Monte-Carlo sample count
        seed                 : int   — RNG seed for reproducibility

        Returns
        -------
        dict with keys:
            nominal         : dict of nominal LUT output
            samples         : pd.DataFrame of all MC samples
            statistics      : dict of {param: {mean, std, p5, p50, p95}}
            developed_fraction : float
        """
        rng = np.random.default_rng(seed)

        e_samples = rng.normal(energy, sigma_energy, n_samples)
        a_samples = rng.normal(angle,  sigma_angle,  n_samples)

        # Clip to LUT valid range
        e_min, e_max = self.energy_range
        a_min, a_max = self.angle_range
        e_samples = np.clip(e_samples, e_min, e_max)
        a_samples = np.clip(a_samples, a_min, a_max)

        res = self.query(e_samples, a_samples)
        nominal = self.query(energy, angle)

        samples_df = pd.DataFrame({
            'energy_MeV': e_samples,
            'angle_deg':  a_samples,
            **{k: res[k] for k in ['major_axis_um', 'minor_axis_um',
                                    'depth_um', 'black_part',
                                    'total_length_um',
                                    'total_surface', 'developed']},
        })

        # Statistics on developed samples only
        dev = samples_df[samples_df['developed']]
        params = ['major_axis_um', 'minor_axis_um', 'depth_um',
                  'black_part', 'total_surface']
        stats = {}
        for p in params:
            if p in dev.columns and len(dev) > 0:
                v = dev[p].values
                stats[p] = {
                    'mean': float(np.mean(v)),
                    'std':  float(np.std(v)),
                    'p5':   float(np.percentile(v,  5)),
                    'p50':  float(np.percentile(v, 50)),
                    'p95':  float(np.percentile(v, 95)),
                }
            else:
                stats[p] = {'mean': 0, 'std': 0, 'p5': 0, 'p50': 0, 'p95': 0}

        return {
            'nominal':             nominal,
            'samples':             samples_df,
            'statistics':          stats,
            'developed_fraction':  float(samples_df['developed'].mean()),
            'n_samples':           n_samples,
        }

    # ------------------------------------------------------------------
    # 6. Summary statistics for any result DataFrame
    # ------------------------------------------------------------------

    @staticmethod
    def statistics(df: pd.DataFrame) -> dict:
        """
        Compute summary statistics for a batch result DataFrame.

        Parameters
        ----------
        df : pd.DataFrame — output from query_dataframe() or process_fluka_file()

        Returns
        -------
        dict  {column_name → {mean, std, min, p25, p50, p75, max, n}}
        """
        params = ['major_axis_um', 'minor_axis_um', 'depth_um',
                  'black_part', 'total_length_um', 'total_surface', 'projected_surface']
        out = {}
        for p in params:
            if p not in df.columns:
                continue
            v = df[p].dropna().values
            if len(v) == 0:
                continue
            out[p] = {
                'n':   len(v),
                'mean': float(np.mean(v)),
                'std':  float(np.std(v)),
                'min':  float(np.min(v)),
                'p25':  float(np.percentile(v, 25)),
                'p50':  float(np.percentile(v, 50)),
                'p75':  float(np.percentile(v, 75)),
                'max':  float(np.max(v)),
            }
        # developed fraction
        if 'developed' in df.columns:
            out['developed_fraction'] = float(df['developed'].mean())
        return out

    # ------------------------------------------------------------------
    # 7. Export
    # ------------------------------------------------------------------

    @staticmethod
    def export_csv(df: pd.DataFrame, path: str):
        """Save a result DataFrame to CSV."""
        df.to_csv(path, index=False)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self):
        if not self.is_loaded:
            return "LUTEngine(not loaded)"
        return (f"LUTEngine(n={self.n_points}, "
                f"E={self.energy_range[0]:.2f}-{self.energy_range[1]:.2f} MeV, "
                f"θ={self.angle_range[0]:.1f}-{self.angle_range[1]:.1f}°, "
                f"developed={self.n_developed})")
