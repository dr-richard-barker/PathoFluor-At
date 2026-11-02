"""Field-oriented analyses of the set-A hand-ROI spectra. Pre-specified: this script, with the
choices below, was committed before it was first run (see git history).

Both analyses use Col-0, the baseline-relative features of scripts/06_models.py (each plate x
genotype's hour-0 mean subtracted; plates Control-4 and flg22-2 excluded), the L2 logistic
model and leave-one-plate-out validation.

A. Alarm replay. "If a scanner had watched these plates, which would it have flagged, and
   when?" For each hour with hand ROIs after treatment (1, 2, 3, 24 h), the Pathogen-vs-Control
   model is fitted without the held-out plate and scores that plate's ROIs. The plate's score
   is the mean held-out P(infected); a plate is flagged when it exceeds THRESHOLD. flg22 plates
   are scored by the model fitted on all Pathogen and Control plates at that hour (they are
   never in training), which asks whether the alarm also fires on the elicitor alone.
   Pathogen 48 h has no hand ROIs, so the replay ends at 24 h.

B. Band sets. "Could a filter camera with a few bands do this?" Each ROI spectrum (offset-
   corrected by its own sub-excitation mean, as in scripts/01_import_rois.py) is reduced to
   the mean signal in BANDWIDTH-wide boxcar filters at the BANDS centres, then to log ratios
   against the 685 nm band (exposure- and size-invariant, as a filter camera's would be).
   Each band set is compared with the full area-normalised spectrum by plate AUC and the exact
   plate-label permutation test, for Pathogen vs Control and flg22 vs Control.

Writes tables/alarm_replay.csv and tables/band_sets_auc.csv.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import RESULTS, TABLES  # noqa: E402
from pathofluor.features import filter_bands  # noqa: E402
from pathofluor.models import LR, BASELINE_EXCLUDED, baseline_relative, lopo_plate_auc, permutation_p  # noqa: E402

warnings.filterwarnings("ignore")

HOURS = (1, 2, 3, 24)
THRESHOLD = 0.5
BANDWIDTH = 10.0  # nm, full width of each boxcar filter
REF_BAND = 685
BANDS = {"B2": (685, 740), "B3": (670, 685, 700), "B4": (670, 685, 700, 740)}
GENOTYPE = "Col-0"


def load():
    F = pd.read_csv(RESULTS / "roi_features.csv.gz")
    F = F[F["set"] == "A"].copy()
    F["plate_id"] = F.treatment + "_" + F.plate.astype(int).astype(str)
    grid = [c for c in F.columns if c.startswith("n") and c[1:].isdigit()]
    return F, grid


def alarm_replay(Fb, grid):
    rows = []
    for hr in HOURS:
        d = Fb[(Fb.hour == hr) & (Fb.genotype == GENOTYPE)]
        dpc = d[d.treatment.isin(["Control", "Pathogen"])]
        y = (dpc.treatment == "Pathogen").astype(int).values
        _, a_plate, P = lopo_plate_auc(dpc[grid].values, y, dpc.plate_id.values, "logistic")
        n = dpc.groupby("plate_id").size()
        for pid, r in P.iterrows():
            rows.append(dict(hour=hr, treatment=pid.split("_")[0], plate=int(pid.split("_")[1]),
                             p_infected=r.s, n_rois=int(n[pid]), scoring="held out (leave-one-plate-out)"))
        m = LR().fit(dpc[grid].values, y)
        dfl = d[d.treatment == "flg22"]
        for pid, g in dfl.groupby("plate_id"):
            rows.append(dict(hour=hr, treatment="flg22", plate=int(pid.split("_")[1]),
                             p_infected=float(m.score(g[grid].values).mean()), n_rois=len(g),
                             scoring="Pathogen-vs-Control model, all plates"))
        for trt, pl in BASELINE_EXCLUDED:
            rows.append(dict(hour=hr, treatment=trt, plate=pl, p_infected=np.nan, n_rois=0,
                             scoring="excluded: hour-0 scans partly upright rescans"))
    A = pd.DataFrame(rows)
    A["alarm"] = A.p_infected > THRESHOLD
    return A.sort_values(["treatment", "plate", "hour"]).reset_index(drop=True)


def band_features(F):
    R = pd.read_parquet(RESULTS / "roi_spectra_A.parquet")
    wcols = [c for c in R.columns if c.startswith("I_")]
    wl = np.array([float(c[2:]) for c in wcols])
    Y = R[wcols].values - R.dark_residual.values[:, None]
    centres = sorted({c for s in BANDS.values() for c in s})
    B = filter_bands(wl, Y, centres, BANDWIDTH)
    cols = {}
    for k, c in enumerate(centres):
        if c != REF_BAND:
            with np.errstate(divide="ignore", invalid="ignore"):
                cols[f"lr{c}"] = np.log(B[:, k] / B[:, centres.index(REF_BAND)])
    out = pd.DataFrame(cols).assign(spectrum_id=R.spectrum_id.values)
    ok = np.isfinite(out.drop(columns="spectrum_id")).all(axis=1) & (B > 0).all(axis=1)
    print(f"band features: {int((~ok).sum())} of {len(out)} spectra dropped (a band <= 0)")
    return F.merge(out[ok], on="spectrum_id")


def band_sets(F, grid):
    Fx = band_features(F)
    lr = [c for c in Fx.columns if c.startswith("lr")]
    Fb = baseline_relative(Fx, grid + lr)
    sets = {"full spectrum": grid, **{k: [f"lr{c}" for c in v if c != REF_BAND] for k, v in BANDS.items()}}
    rows = []
    for hr in HOURS:
        for trt in ("Pathogen", "flg22"):
            d = Fb[(Fb.hour == hr) & (Fb.genotype == GENOTYPE) & Fb.treatment.isin(["Control", trt])]
            if d.treatment.nunique() < 2:
                continue
            y = (d.treatment == trt).astype(int).values
            plate = d.plate_id.values
            y_plate = {p: int(p.startswith(trt)) for p in np.unique(plate)}
            for name, cols in sets.items():
                X = d[cols].values
                _, a_plate, _ = lopo_plate_auc(X, y, plate, "logistic")
                p, null = permutation_p(X, plate, y_plate, "logistic", a_plate)
                rows.append(dict(hour=hr, contrast=f"{trt} vs Control", band_set=name,
                                 bands_nm=" ".join(str(c) for c in BANDS[name]) if name in BANDS else "650-800 (2 nm grid)",
                                 n_features=len(cols), n_plants=len(y), n_plates=len(y_plate),
                                 auc_plate=a_plate, perm_p_plate=p, n_perm=len(null)))
    return pd.DataFrame(rows)


def main():
    F, grid = load()
    Fb = baseline_relative(F, grid)
    A = alarm_replay(Fb, grid)
    A.to_csv(TABLES / "alarm_replay.csv", index=False)
    print(A.pivot_table(index=["treatment", "plate"], columns="hour", values="p_infected").round(2).to_string())
    S = band_sets(F, grid)
    S.to_csv(TABLES / "band_sets_auc.csv", index=False)
    print(S.pivot_table(index=["contrast", "band_set"], columns="hour", values="auc_plate").round(2).to_string())
    print(S.pivot_table(index=["contrast", "band_set"], columns="hour", values="perm_p_plate").round(3).to_string())


if __name__ == "__main__":
    main()
