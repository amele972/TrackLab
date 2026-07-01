"""
workers.py — TrackLab v1.0 GUI Background Workers
=======================================================
All QThread workers for long-running calculations.
"""

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class TrackWorker(QThread):
    """Calculate a single track in the background."""

    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.running = True

    def run(self):
        try:
            self.status_update.emit("Loading physics engine…")
            self.progress.emit(10)

            from tracklab.calculate_track_parameter import calculate_track_parameters
            from tracklab.load_srim_data import load_srim_data
            from tracklab.vt_multiion import get_model
            from tracklab.vt_utils import build_vrint_interpolator

            ion = self.params.get("ion", "protons")
            energy = self.params["energy"]
            vb = self.params["vb"]

            interps, _ = load_srim_data()
            range_interp = interps.get(ion)
            if range_interp is None:
                self.error.emit(f"No SRIM data for ion '{ion}'")
                return

            vt_model = get_model()
            F_interp = build_vrint_interpolator(
                vt_model=vt_model, ion=ion, energy=energy, vb=vb
            )

            self.status_update.emit("Computing track…")
            self.progress.emit(40)

            res = calculate_track_parameters(
                energy=energy,
                angle_deg=self.params["angle"],
                vb=vb,
                time_etching=self.params["time"],
                range_interpolator=range_interp,
                F_interp=F_interp,
                ion=ion,
                vt_model=vt_model,
            )

            self.progress.emit(100)
            self.status_update.emit("Done!")
            self.result_ready.emit(res)

        except Exception as e:
            import traceback

            traceback.print_exc()
            self.error.emit(str(e))


class BatchWorker(QThread):
    """Generate reference dataset (energy × angle sweep)."""

    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.running = True

    def run(self):
        try:
            self.status_update.emit("Loading physics engine…")
            self.progress.emit(5)

            from tracklab.calculate_track_parameter import calculate_track_parameters
            from tracklab.load_srim_data import load_srim_data
            from tracklab.vt_multiion import get_model
            from tracklab.vt_utils import build_vrint_interpolator

            ion = self.params.get("ion", "protons")
            vb = self.params["vb"]

            interps, _ = load_srim_data()
            range_interp = interps.get(ion)
            if range_interp is None:
                self.error.emit(f"No SRIM data for ion '{ion}'")
                return

            vt_model = get_model()

            energies = np.linspace(
                self.params["e_min"], self.params["e_max"], int(self.params["e_steps"])
            )
            angles = np.linspace(
                self.params["a_min"], self.params["a_max"], int(self.params["a_steps"])
            )
            total = len(energies) * len(angles)
            results = []
            count = 0

            self.status_update.emit(f"Computing {total} tracks…")
            self.progress.emit(10)

            for energy in energies:
                if not self.running:
                    break
                F_interp = build_vrint_interpolator(
                    vt_model=vt_model, ion=ion, energy=energy, vb=vb
                )

                for angle in angles:
                    if not self.running:
                        break
                    res = calculate_track_parameters(
                        energy=energy,
                        angle_deg=angle,
                        vb=vb,
                        time_etching=self.params["time"],
                        range_interpolator=range_interp,
                        F_interp=F_interp,
                        ion=ion,
                        vt_model=vt_model,
                    )
                    results.append(
                        {
                            "ion": ion,
                            "energy_MeV": energy,
                            "angle_deg": angle,
                            "depth_um": res.get("depth_um", 0.0),
                            "major_axis_um": res.get("major_axis_um", 0.0),
                            "minor_axis_um": res.get("minor_axis_um", 0.0),
                            "total_length_um": res.get("total_length_um", 0.0),
                            "black_part": res.get("black_part", 0.0),
                            "total_surface": res.get("total_surface", 0.0),
                            "projected_surface": res.get("projected_surface", 0.0),
                            "mean_brightness": res.get("mean_brightness", 0.0),
                            "status": res.get("status", "unknown"),
                        }
                    )
                    count += 1
                    self.progress.emit(10 + int(80 * count / total))
                    if count % max(1, total // 10) == 0:
                        self.status_update.emit(f"Computed {count}/{total} tracks…")

            if self.running:
                developed = sum(1 for r in results if r["status"] == "Developed")
                self.result_ready.emit(
                    {
                        "results": results,
                        "total": total,
                        "developed": developed,
                        "energies": energies.tolist(),
                        "angles": angles.tolist(),
                    }
                )
                self.progress.emit(100)
                self.status_update.emit("Complete!")
            else:
                self.status_update.emit("Cancelled")

        except Exception as e:
            import traceback

            traceback.print_exc()
            self.error.emit(str(e))


class FlukaWorker(QThread):
    """Process FLUKA phase-space file."""

    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.running = True

    def run(self):
        try:
            from tracklab.calculate_track_parameter import calculate_track_parameters
            from tracklab.load_srim_data import load_srim_data
            from tracklab.utils import compute_etching_time
            from tracklab.vt_multiion import get_model
            from tracklab.vt_utils import build_vrint_interpolator

            self.status_update.emit("Loading physics engine…")
            self.progress.emit(5)

            ion = self.params.get("ion", "protons")
            vb = self.params["vb"]
            time_etching_ref = self.params.get("time", 2.83)

            interps, _ = load_srim_data()
            range_interp = interps.get(ion)
            if range_interp is None:
                self.error.emit(f"No SRIM data for ion '{ion}'")
                return

            vt_model = get_model()

            self.status_update.emit("Reading FLUKA file…")
            with open(self.params["file"], "r") as f:
                lines = [line.strip() for line in f if line.strip()]
            lines = lines[self.params.get("skip_header", 1) :]
            total = len(lines)

            print(f"[FlukaWorker] Processing file: {self.params['file']}")
            print(f"[FlukaWorker] Total particles to simulate: {total}")

            results, processed, developed, skipped = [], 0, 0, 0
            col = self.params.get(
                "col_map", {"energy": 1, "x": 2, "y": 3, "z": 4, "cosz": 7}
            )

            self.status_update.emit(f"Processing {total} particles…")
            self.progress.emit(10)

            for idx, line in enumerate(lines):
                if not self.running:
                    break
                try:
                    parts = line.split()
                    if len(parts) < 8:
                        skipped += 1
                        continue

                    energy_gev = float(parts[col["energy"]])
                    z_val = float(parts[col["z"]])
                    cosz = float(parts[col["cosz"]])

                    energy_mev = energy_gev * 1000.0
                    cosz = np.clip(cosz, -1.0, 1.0)
                    if energy_mev <= 0:
                        skipped += 1
                        continue

                    angle_deg = 90.0 - np.degrees(np.arccos(abs(cosz)))
                    etching_time = compute_etching_time(z_val, vb=vb, t_ref=time_etching_ref, cosz=cosz)
                    if etching_time <= 0:
                        skipped += 1
                        continue

                    F_interp = build_vrint_interpolator(
                        vt_model=vt_model, ion=ion, energy=energy_mev, vb=vb
                    )

                    res = calculate_track_parameters(
                        energy=energy_mev,
                        angle_deg=angle_deg,
                        vb=vb,
                        time_etching=etching_time,
                        range_interpolator=range_interp,
                        F_interp=F_interp,
                        ion=ion,
                        vt_model=vt_model,
                        is_bottom_track=(cosz < 0),
                    )
                    results.append(
                        {
                            "energy_MeV": energy_mev,
                            "beam_energy_MeV": self.params.get(
                                "beam_energy_MeV", energy_mev
                            ),
                            "angle_deg": angle_deg,
                            "z_cm": z_val,
                            "etching_time_h": etching_time,
                            "depth_um": res.get("depth_um", 0.0),
                            "major_axis_um": res.get("major_axis_um", 0.0),
                            "minor_axis_um": res.get("minor_axis_um", 0.0),
                            "total_length_um": res.get("total_length_um", 0.0),
                            "black_part": res.get("black_part", 0.0),
                            "total_surface": res.get("total_surface", 0.0),
                            "projected_surface": res.get("projected_surface", 0.0),
                            "mean_brightness": res.get("mean_brightness", 0.0),
                            "status": res.get("status", "unknown"),
                        }
                    )
                    processed += 1
                    if res.get("indicator", -1) == 1:
                        developed += 1
                except Exception:
                    skipped += 1

                if (idx + 1) % max(1, total // 20) == 0:
                    self.progress.emit(10 + int(80 * (idx + 1) / total))

            if self.running:
                self.result_ready.emit(
                    {
                        "results": results,
                        "processed": processed,
                        "developed": developed,
                        "skipped": skipped,
                        "total": total,
                    }
                )
                self.progress.emit(100)

        except Exception as e:
            import traceback

            traceback.print_exc()
            self.error.emit(str(e))


class GenericWorker(QThread):
    """Generic worker that runs any callable."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(float)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kw = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kw)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class FlukaMultiIonWorker(QThread):
    """Process FLUKA advanced phase-space file (Beta: Multi-Ion Mode)."""

    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.running = True

    def run(self):
        try:
            from tracklab.calculate_track_parameter import calculate_track_parameters
            from tracklab.load_srim_data import load_srim_data
            from tracklab.utils import compute_etching_time
            from tracklab.vt_multiion import get_model
            from tracklab.vt_utils import build_vrint_interpolator

            self.status_update.emit("Loading physics engine for Multi-Ion…")
            self.progress.emit(5)

            # Global VB fallback, but we use ion-specific ones internally if needed
            vb_global = self.params.get("vb", 4.7)
            time_etching_ref = self.params.get("time", 2.83)

            interps, _ = load_srim_data()
            vt_model = get_model()

            # Z to Ion mapping
            z_to_ion = {
                1: "protons",
                2: "alpha",
                3: "Li",
                6: "C",
                8: "O"
            }

            self.status_update.emit("Reading advanced FLUKA file…")
            with open(self.params["file"], "r") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            skip_header = self.params.get("skip_header", 1)
            # if the file had comment headers, we might have already skipped them.
            # but let's be safe:
            if len(lines) > skip_header and "EVENT" in lines[0].upper():
                lines = lines[skip_header:]

            total = len(lines)
            print(f"[FlukaMultiIonWorker] Processing file: {self.params['file']}")
            print(f"[FlukaMultiIonWorker] Total particles found (excl headers): {total}")

            results, processed, developed, skipped = [], 0, 0, 0

            self.status_update.emit(f"Processing {total} particles…")
            self.progress.emit(10)

            for idx, line in enumerate(lines):
                if not self.running:
                    break
                try:
                    parts = line.split()
                    if len(parts) < 9:
                        skipped += 1
                        continue
                    
                    # New format:
                    # 1:EVENT 2:TYPE 3:PART_NAME 4:Z 5:A 6:EKIN_GEV 7:Z_POS 8:CZ_DIR 9:COMMENT
                    ncase = int(parts[0])
                    event_type = int(parts[1])
                    part_name = parts[2]
                    z_val_ion = int(parts[3])
                    a_val_ion = int(parts[4])
                    ekin_gev = float(parts[5])
                    z_pos = float(parts[6])
                    cz_dir = float(parts[7])
                    comment = parts[8]

                    # 1. Skip stopping events (we only care about track start)
                    if event_type == 4 or comment == 'STOPPING_TRK':
                        skipped += 1
                        continue

                    # 2. Map to supported ion
                    ion_name = z_to_ion.get(z_val_ion)
                    if not ion_name or ion_name not in interps:
                        skipped += 1
                        continue

                    range_interp = interps[ion_name]
                    
                    # Note: No deduplication logic needed here! The file correctly outputs 
                    # multiple particles per event when they physically occur.

                    energy_mev = ekin_gev * 1000.0
                    cosz = np.clip(cz_dir, -1.0, 1.0)
                    if energy_mev <= 0:
                        skipped += 1
                        continue

                    angle_deg = 90.0 - np.degrees(np.arccos(abs(cosz)))
                    etching_time = compute_etching_time(z_pos, vb=vb_global, t_ref=time_etching_ref, cosz=cosz)
                    
                    if etching_time <= 0:
                        skipped += 1
                        continue

                    F_interp = build_vrint_interpolator(
                        vt_model=vt_model, ion=ion_name, energy=energy_mev, vb=vb_global
                    )

                    res = calculate_track_parameters(
                        energy=energy_mev,
                        angle_deg=angle_deg,
                        vb=vb_global,
                        time_etching=etching_time,
                        range_interpolator=range_interp,
                        F_interp=F_interp,
                        ion=ion_name,
                        vt_model=vt_model,
                        is_bottom_track=(cosz < 0),
                    )
                    
                    results.append(
                        {
                            "ion": ion_name,
                            "energy_MeV": energy_mev,
                            "beam_energy_MeV": self.params.get("beam_energy_MeV", energy_mev),
                            "angle_deg": angle_deg,
                            "z_cm": z_pos,
                            "etching_time_h": etching_time,
                            "depth_um": res.get("depth_um", 0.0),
                            "major_axis_um": res.get("major_axis_um", 0.0),
                            "minor_axis_um": res.get("minor_axis_um", 0.0),
                            "total_length_um": res.get("total_length_um", 0.0),
                            "black_part": res.get("black_part", 0.0),
                            "total_surface": res.get("total_surface", 0.0),
                            "projected_surface": res.get("projected_surface", 0.0),
                            "mean_brightness": res.get("mean_brightness", 0.0),
                            "status": res.get("status", "unknown"),
                        }
                    )
                    processed += 1
                    if res.get("indicator", -1) == 1:
                        developed += 1
                except Exception:
                    skipped += 1

                if (idx + 1) % max(1, total // 20) == 0:
                    self.progress.emit(10 + int(80 * (idx + 1) / total))

            if self.running:
                self.result_ready.emit(
                    {
                        "results": results,
                        "processed": processed,
                        "developed": developed,
                        "skipped": skipped,
                        "total": total,
                    }
                )
                self.progress.emit(100)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

