import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os

# ============================================================================
# BPL MODEL & FITTING HELPER (From your vt_multiion.py)
# ============================================================================

def vt_bpl(y, A, y0, alpha, beta):
    """
    Broken Power Law:  V(y) = 1 + A*y^alpha / (1 + (y/y0)^(alpha+beta))
    """
    y = np.asarray(y, dtype=float)
    y = np.maximum(y, 1e-9)
    numerator = A * (y ** alpha)
    ratio = np.clip((y / y0) ** (alpha + beta), 0.0, 1e10)
    return 1.0 + numerator / (1.0 + ratio)


def _fit_bpl_to_v(y_data, v_data):
    """
    Fit BPL to (y, V) data where V = VT/VB_FIT.
    Returns dict with keys A, y0, alpha, beta, r2, rmse, or None on failure.
    """
    mask = (v_data >= 1.0) & np.isfinite(v_data) & np.isfinite(y_data) & (y_data > 0)
    y = y_data[mask]
    v = v_data[mask]

    if len(y) < 5:
        return None

    peak_idx = int(v.argmax())
    peak_v   = float(v[peak_idx]) - 1.0
    peak_y   = float(y[peak_idx])

    bounds = ([0.01, 0.05, 0.1, 0.1], [5000.0, 50.0, 3.0, 15.0])

    best = None
    for alpha0 in (0.5, 1.0, 1.5):
        for beta0 in (1.0, 2.0, 3.5):
            p0 = [max(peak_v, 0.1), peak_y, alpha0, beta0]
            try:
                popt, _ = curve_fit(
                    vt_bpl, y, v, p0=p0, bounds=bounds,
                    maxfev=20000, method='trf'
                )
                v_pred  = vt_bpl(y, *popt)
                ss_res  = np.sum((v - v_pred) ** 2)
                ss_tot  = np.sum((v - np.mean(v)) ** 2)
                r2      = 1.0 - ss_res / ss_tot if ss_tot > 0 else -999.0
                rmse    = np.sqrt(ss_res / len(y))
                
                if best is None or r2 > best['r2']:
                    best = {
                        'A': float(popt[0]), 'y0': float(popt[1]),
                        'alpha': float(popt[2]), 'beta': float(popt[3]),
                        'r2': float(r2), 'rmse': float(rmse),
                        'popt': popt # Keep the raw parameters for plotting
                    }
            except Exception:
                pass

    return best


# ============================================================================
# MAIN PLOTTING SCRIPT
# ============================================================================

def main():
    # 1. Define the file path
    data_path = r"K:\Mele\Software\TRACK_P\Original\Track_p_website_version\old\Backup 6.10 - updated track optics + Github package\Git_package-WIP-Mar2026\combined\tracklab_unified\tracklab\data\Data_ions.xlsx"
    
    # Check if file exists, if not, try to load it from the local directory 
    # (useful if you move the script around)
    if not os.path.exists(data_path):
        print(f"Warning: Could not find path {data_path}.")
        data_path = "Data_ions.xlsx"
        print(f"Attempting to load from local directory: {data_path}")

    # 2. Load and prep data
    try:
        df = pd.read_excel(data_path)
    except Exception as e:
        print(f"Error loading Excel file: {e}")
        return

    # Normalize H to protons if necessary
    df['Ion'] = df['Ion'].replace({'H': 'protons'})
    
    # Calculate Etch Rate Ratio V
    df['V'] = df['VT'] #/ df['VB']

    # Get unique ions
    ions = sorted(df['Ion'].unique().tolist())
    
    print(f"Found data for ions: {ions}")

    # Set up basic matplotlib style
    plt.rcParams.update({'font.size': 12, 'figure.autolayout': True})

    # 3. Process and plot each ion
    for ion in ions:
        ion_df = df[df['Ion'] == ion]
        energies = sorted(ion_df['Energy'].unique())
        
        # Create a new figure for the current ion
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Setup a colormap to distinguish different energies
        colors = plt.cm.plasma(np.linspace(0, 0.9, len(energies)))

        print(f"\nProcessing Ion: {ion}")
        
        for idx, energy in enumerate(energies):
            subset = ion_df[ion_df['Energy'] == energy]
            y_vals = subset['R-x'].values.astype(float)
            v_vals = subset['V'].values.astype(float)
            
            # Plot the experimental data points
            color = colors[idx]
            ax.scatter(y_vals, v_vals, color=color, label=f"{energy} MeV", s=30, alpha=0.8, edgecolors='k', zorder=3)
            
            # Fit the BPL model
            result = _fit_bpl_to_v(y_vals, v_vals)
            
            if result:
                # Generate a smooth array of y values for plotting the fit line
                y_smooth = np.linspace(min(y_vals)*0.9, max(y_vals)*1.1, 500)
                v_fit = vt_bpl(y_smooth, *result['popt'])
                
                # Plot the fitted line
                ax.plot(y_smooth, v_fit, color=color, linestyle='-', linewidth=2, zorder=2)
                print(f"  {energy:6.2f} MeV: Fit OK (R2 = {result['r2']:.4f})")
            else:
                print(f"  {energy:6.2f} MeV: Fit FAILED")

        # 4. Formatting the plot
        ax.set_title(f"Track Etch Rate for {ion} Ion", fontsize=14, fontweight='bold')
        ax.set_xlabel(r"Residual Range $y$ ($\mu$m)", fontsize=12)
        ax.set_ylabel(r"Track Etch Rate $V_T$ ($\mu$m/h)", fontsize=12)
        
        ax.grid(True, linestyle='--', alpha=0.6, zorder=0)
        
        # Move legend outside the plot if there are many energies
        ax.legend(title="Energy", loc='upper right')
        
        # Save the figure locally
        output_filename = f"Fit_Plot_{ion}.png"
        plt.savefig(output_filename, dpi=300, bbox_inches='tight')
        print(f"Saved plot as {output_filename}")
        
        # Display the plot
        plt.show()

if __name__ == '__main__':
    main()
