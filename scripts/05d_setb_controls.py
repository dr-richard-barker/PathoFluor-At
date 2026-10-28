"""Set-B control scans: bacteria-only scans and the daily reference scans.

* Bacteria-only scans ("HrN Bacteria LaserNN"): does the bacterial suspension/plate fluoresce
  by itself under 405 nm excitation, and with what spectrum? If it does, short-wavelength
  emission on Pathogen plates may be bacterial rather than plant-derived.
* Reference scans (one pair per imaging day): emission of the same reference target each day,
  as a check on day-to-day drift of excitation power or detector response.

For every scan: pixels above the liberal harvest threshold are 'signal' (none may exist in a
bacteria-only scan); the reported spectrum is their mean minus the per-band dark level, divided
by exposure. Writes tables/setb_control_scans.csv and results/setb_control_spectra.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, REPO, RESULTS, TABLES  # noqa: E402


def main():
    cm = pd.read_csv(META / "cube_manifest.csv")
    cm = cm[(cm["set"] == "B") & cm.role.isin(["bacteria_scan", "reference"])]
    rows, spec_rows = [], []
    for r in cm.itertuples():
        npz = REPO / "cache" / "harvest" / f"{r.cube_id}.npz"
        if not npz.exists():
            print(f"not harvested yet: {r.cube_id}")
            continue
        z = np.load(npz)
        wl = z["wl"]
        dark = z["dark"][np.isin(z["wl_all"], wl)]
        n = len(z["y"])
        mean = (z["spectra"].astype(np.float32).mean(0) - dark) / r.tint_s if n else np.full(len(wl), np.nan)
        sw = (wl >= 430) & (wl <= 640)
        ch = (wl >= 650) & (wl <= 800)
        rows.append(dict(cube_id=r.cube_id, role=r.role, hour=r.hour, laser=r.laser, scan_start=r.scan_start,
                         tint_s=r.tint_s, n_signal_px=n, signal_fraction=n / (r.lines * r.samples),
                         peak_nm=float(wl[np.nanargmax(mean)]) if n else np.nan,
                         sw_cps=float(np.nanmean(mean[sw])) if n else np.nan,
                         chl_cps=float(np.nanmean(mean[ch])) if n else np.nan))
        spec_rows += [dict(cube_id=r.cube_id, wl=float(w), cps=float(v)) for w, v in zip(wl, mean)]
    T = pd.DataFrame(rows)
    T.to_csv(TABLES / "setb_control_scans.csv", index=False)
    pd.DataFrame(spec_rows).to_csv(RESULTS / "setb_control_spectra.csv", index=False)
    pd.set_option("display.width", 200)
    print(T.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
