"""Primary statistics on the 2016 hand-ROI spectra (exposure-invariant shape features).

The hand ROIs carry the 2016 annotator's genotype, plate and plant labels, so this analysis
does not depend on our seedling segmentation or label transfer.

Model, per set x hour x feature (plant-level data, plate random intercept):
    feature ~ C(treatment, Control) * C(genotype, Col-0) + (1 | plate)
Treatment is applied per plate, so the plate is the unit for treatment effects. Genotype
lanes are within plates. Pre-specified contrasts, from the fixed effects:
    flg22 vs Control in Col-0;  Pathogen vs Control in Col-0;
    flg22 x fls2-17, flg22 x fls2-101 (FLS2 dependence);  flg22 x cml24-2, flg22 x cml24-4;
    Pathogen x each mutant.
Benjamini-Hochberg FDR across all features x hours x contrasts within a set.
Hour 0 (pre-treatment) is tested too: any 'effect' there is a plate or placement artefact
and bounds what later effects can be attributed to treatment.

Writes tables/stats_contrasts.csv and tables/stats_plate_means.csv.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import RESULTS, TABLES  # noqa: E402

FEATURES = ["f685_f740", "red_peak_nm", "red_fwhm_nm", "centroid_nm", "farred_fraction",
            "shortwave_fraction"]
warnings.filterwarnings("ignore")


def fit(d, feat):
    d = d.assign(y=d[feat], plate_id=d.treatment + "_" + d.plate.astype(int).astype(str))
    d = d[np.isfinite(d.y)]
    sd = d.y.std()
    d = d.assign(y=(d.y - d.y.mean()) / sd)   # standardise so effects are comparable (in SD units)
    f = "y ~ C(treatment, Treatment('Control')) * C(genotype, Treatment('Col-0'))"
    try:
        m = smf.mixedlm(f, d, groups=d.plate_id).fit(reml=True, method="lbfgs")
    except Exception:
        return None, sd
    return m, sd


def name_term(t):
    t = t.replace("C(treatment, Treatment('Control'))[T.", "trt:").replace(
        "C(genotype, Treatment('Col-0'))[T.", "geno:").replace("]", "")
    return t


def main():
    F = pd.read_csv(RESULTS / "roi_features.csv.gz")
    TABLES.mkdir(exist_ok=True)
    rows = []
    for (s, hr), d in F.groupby(["set", "hour"]):
        if d.treatment.nunique() < 2:
            continue
        for feat in FEATURES:
            m, sd = fit(d, feat)
            if m is None:
                continue
            for term in m.params.index:
                if not (term.startswith("C(treatment") or ":" in term and "treatment" in term):
                    continue
                t = name_term(term)
                if ":" not in t.replace("trt:", "", 1):
                    contrast = f"{t.split(':')[1]} vs Control (Col-0)"
                else:
                    a, b = t.split(":geno:")
                    contrast = f"{a.replace('trt:', '')} x {b}"
                rows.append(dict(set=s, hour=hr, feature=feat, contrast=contrast,
                                 effect_sd=m.params[term], se_sd=m.bse[term], p=m.pvalues[term],
                                 effect_raw=m.params[term] * sd, n_plants=int(m.nobs),
                                 n_plates=d.treatment.str.cat(d.plate.astype(str)).nunique()))
    C = pd.DataFrame(rows)
    C["q"] = np.nan
    for s, idx in C.groupby("set").groups.items():
        C.loc[idx, "q"] = multipletests(C.loc[idx, "p"], method="fdr_bh")[1]
    C.to_csv(TABLES / "stats_contrasts.csv", index=False)

    pm = F.groupby(["set", "hour", "treatment", "plate", "genotype"])[FEATURES].mean().reset_index()
    pm.to_csv(TABLES / "stats_plate_means.csv", index=False)

    # ---- Baseline-adjusted (sensitivity): change from the same plate x genotype at hour 0.
    # Plate numbers are assumed to denote the same physical plate at every timepoint.
    # Set A Control-4 and flg22-2 are dropped: part or all of their hour-0 scans were the
    # upright "NI" rescans, so their baseline geometry differs from the other plates.
    base = pm[pm.hour == 0].drop(columns="hour")
    dl = pm[pm.hour > 0].merge(base, on=["set", "treatment", "plate", "genotype"], suffixes=("", "_h0"))
    for f in FEATURES:
        dl[f] = dl[f] - dl[f + "_h0"]
    ni = (dl["set"] == "A") & (((dl.treatment == "Control") & (dl.plate == 4)) |
                              ((dl.treatment == "flg22") & (dl.plate == 2)))
    dl = dl[~ni]
    rows = []
    for (s, hr), d in dl.groupby(["set", "hour"]):
        if d.treatment.nunique() < 2:
            continue
        for feat in FEATURES:
            m, sd = fit(d, feat)
            if m is None:
                continue
            for term in m.params.index:
                if "treatment" not in term:
                    continue
                t = name_term(term)
                contrast = (f"{t.split(':')[1]} vs Control (Col-0)" if ":geno:" not in t
                            else f"{t.split(':geno:')[0].replace('trt:', '')} x {t.split(':geno:')[1]}")
                rows.append(dict(set=s, hour=hr, feature=feat, contrast=contrast,
                                 effect_sd=m.params[term], se_sd=m.bse[term], p=m.pvalues[term],
                                 effect_raw=m.params[term] * sd, n_plate_genotypes=int(m.nobs)))
    B = pd.DataFrame(rows)
    B["q"] = np.nan
    for s, idx in B.groupby("set").groups.items():
        B.loc[idx, "q"] = multipletests(B.loc[idx, "p"], method="fdr_bh")[1]
    B.to_csv(TABLES / "stats_contrasts_baseline_adjusted.csv", index=False)
    for s in ("A", "B"):
        c = B[(B["set"] == s) & (B.q < 0.05)].sort_values(["contrast", "hour"])
        print(f"\n=== baseline-adjusted, set {s}: {len(c)} at q < 0.05 (of {int((B['set'] == s).sum())}) ===")
        print(c[["hour", "feature", "contrast", "effect_sd", "effect_raw", "q"]].round(4).to_string(index=False))
        top = B[B["set"] == s].sort_values("p").head(8)
        print("  smallest p:\n", top[["hour", "feature", "contrast", "effect_sd", "p", "q"]].round(4).to_string(index=False))

    pd.set_option("display.width", 200)
    for s in ("A", "B"):
        c = C[(C["set"] == s) & (C.q < 0.05)].sort_values(["contrast", "hour", "q"])
        print(f"\n=== set {s}: {len(c)} contrasts at q < 0.05 (of {int((C['set'] == s).sum())}) ===")
        print(c[["hour", "feature", "contrast", "effect_sd", "effect_raw", "q"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
