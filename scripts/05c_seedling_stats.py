"""Secondary statistics on the cube-derived seedlings (all plates, incl. set-A Pathogen 48 h and
the plate-replicated set B).

Unit: the plate. For each plate x hour the seedling features are averaged over all seedlings
(genotypes pooled; set-A Pathogen 48 h has no genotype labels), then expressed as change from
the same plate at hour 0. Set-A plates Control-4 and flg22-2 are excluded (partly upright hour-0
rescans). Set B is analysed per laser setting. Treated vs Control plates are compared per hour
with Welch's t-test on the plate-level changes; Benjamini-Hochberg FDR within each set x laser.

Writes tables/seedling_plate_changes.csv and tables/seedling_stats.csv.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import RESULTS, TABLES  # noqa: E402

warnings.filterwarnings("ignore")
FEATS = ["f685_f740", "red_fwhm_nm", "centroid_nm", "farred_fraction", "shortwave_fraction",
         "f685_cps", "total_650_800_cps", "ratio_px_sd", "shortwave_px_p90", "n_px"]


def main():
    L = pd.read_csv(RESULTS / "seedlings_labelled.csv.gz")
    mcr = RESULTS / "mcr_seedling_scores.csv.gz"
    feats = list(FEATS)
    if mcr.exists():
        M = pd.read_csv(mcr)
        L = L.merge(M, on=["cube_id", "seedling"], how="left")
        feats += [c for c in M.columns if c.endswith("_frac")]
    L["laser"] = L.laser.fillna(0).astype(int)
    keys = ["set", "laser", "treatment", "plate"]
    pm = L.groupby(keys + ["hour"])[feats].mean().reset_index()
    base = pm[pm.hour == 0].drop(columns="hour").set_index(keys).add_suffix("_h0")
    d = pm[pm.hour > 0].merge(base.reset_index(), on=keys)
    for f in feats:
        d[f] = d[f] - d[f + "_h0"]
    d = d[~((d["set"] == "A") & (((d.treatment == "Control") & (d.plate == 4)) |
                                ((d.treatment == "flg22") & (d.plate == 2))))]
    d[keys + ["hour"] + feats].to_csv(TABLES / "seedling_plate_changes.csv", index=False)

    rows = []
    for (s, las, hr), g in d.groupby(["set", "laser", "hour"]):
        for trt in ("flg22", "Pathogen"):
            a, b = g[g.treatment == trt], g[g.treatment == "Control"]
            if len(a) < 2 or len(b) < 2:
                continue
            for f in feats:
                t = ttest_ind(a[f], b[f], equal_var=False)
                rows.append(dict(set=s, laser=las or None, hour=hr, contrast=f"{trt} vs Control", feature=f,
                                 delta=a[f].mean() - b[f].mean(), n_treated=len(a), n_control=len(b),
                                 t=t.statistic, p=t.pvalue))
    R = pd.DataFrame(rows)
    R["q"] = np.nan
    for _, idx in R.groupby(["set", "laser"], dropna=False).groups.items():
        R.loc[idx, "q"] = multipletests(R.loc[idx, "p"].fillna(1), method="fdr_bh")[1]
    R.to_csv(TABLES / "seedling_stats.csv", index=False)
    pd.set_option("display.width", 200)
    print(R[R.q < 0.1].sort_values(["set", "laser", "contrast", "hour"])
          [["set", "laser", "hour", "contrast", "feature", "delta", "n_treated", "n_control", "p", "q"]]
          .round(4).to_string(index=False))


if __name__ == "__main__":
    main()
