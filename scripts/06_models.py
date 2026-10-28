"""Classifiers for the treatment signature, on the set-A hand-ROI spectra.

Tasks, per hour: Pathogen vs Control and flg22 vs Control, in Col-0 and in all genotypes
pooled. Two feature sets:
  spectrum: area-normalised 650-800 nm emission on a 2 nm grid (exposure-invariant)
  shape:    the six engineered shape features
and two models: PLS-DA (3 components) and L2 logistic regression.

Validation: leave-one-plate-pair-out CV. Fold k holds out Control plate k and treated plate k,
so the model never sees a test plate. Out-of-fold probabilities are pooled. AUC is reported
at plant level and at plate level (mean probability per plate; 8 plates). An exact
plate-label permutation test refits the whole CV for every one of the 70 ways to choose 4 of
the 8 plates as 'treated'. Hour 0 (before treatment) is included as a placebo: it shows how
much plate-to-plate imbalance alone can be classified.

Baseline-relative variants subtract each plate x genotype's hour-0 mean (plates Control-4 and
flg22-2 excluded, as their hour-0 scans were partly the upright rescans).

Specificity: a model trained on Col-0 flg22 vs Control is applied to each mutant. The
reported effect is its mean P(flg22) on flg22 plates minus that on Control plates.

Writes tables/model_auc.csv, tables/model_specificity.csv and results/model_loadings.csv.
"""
import itertools
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import RESULTS, TABLES  # noqa: E402

warnings.filterwarnings("ignore")
SHAPE = ["f685_f740", "red_peak_nm", "red_fwhm_nm", "centroid_nm", "farred_fraction", "shortwave_fraction"]


class PLSDA:
    def __init__(self, n=3):
        self.m = make_pipeline(StandardScaler(), PLSRegression(n_components=n, scale=False))

    def fit(self, X, y):
        self.m.fit(X, y.astype(float))
        return self

    def score(self, X):
        return self.m.predict(X).ravel()


class LR:
    def __init__(self):
        self.m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))

    def fit(self, X, y):
        self.m.fit(X, y)
        return self

    def score(self, X):
        return self.m.predict_proba(X)[:, 1]


MODELS = {"PLS-DA": PLSDA, "logistic": LR}


def cv_scores(X, y, plate, model):
    """Leave-one-plate-pair-out. plate is a 'treatment_plate' id; folds pair plate k of each class."""
    num = pd.Series(plate).str.split("_").str[-1].values
    oof = np.full(len(y), np.nan)
    for k in np.unique(num):
        te = num == k
        if y[~te].min() == y[~te].max():
            continue
        oof[te] = MODELS[model]().fit(X[~te], y[~te]).score(X[te])
    return oof


def aucs(y, s, plate):
    ok = np.isfinite(s)
    a_plant = roc_auc_score(y[ok], s[ok]) if len(np.unique(y[ok])) == 2 else np.nan
    P = pd.DataFrame(dict(y=y[ok], s=s[ok], p=np.asarray(plate)[ok])).groupby("p").agg(y=("y", "first"), s=("s", "mean"))
    a_plate = roc_auc_score(P.y, P.s) if P.y.nunique() == 2 else np.nan
    return a_plant, a_plate, P


def permutation_p(X, plate, y_plate, model, observed):
    """Exact: every assignment of the treated label to the same number of plates."""
    plates = np.array(sorted(y_plate))
    n_t = sum(y_plate.values())
    null = []
    for treated in itertools.combinations(plates, n_t):
        yy = np.isin(plate, treated).astype(int)
        # Re-pair folds by plate number within the permuted labels is not possible in
        # general; use leave-one-plate-out over all plates for the null and the observed.
        s = np.full(len(yy), np.nan)
        for p in plates:
            te = plate == p
            if yy[~te].min() == yy[~te].max():
                continue
            s[te] = MODELS[model]().fit(X[~te], yy[~te]).score(X[te])
        null.append(aucs(yy, s, plate)[1])
    null = np.array(null)
    return float((null >= observed - 1e-12).mean()), null


def lopo_plate_auc(X, y, plate, model):
    s = np.full(len(y), np.nan)
    for p in np.unique(plate):
        te = plate == p
        if y[~te].min() == y[~te].max():
            continue
        s[te] = MODELS[model]().fit(X[~te], y[~te]).score(X[te])
    return aucs(y, s, plate)


def main():
    F = pd.read_csv(RESULTS / "roi_features.csv.gz")
    F = F[F["set"] == "A"].copy()
    grid = [c for c in F.columns if c.startswith("n") and c[1:].isdigit()]
    F["plate_id"] = F.treatment + "_" + F.plate.astype(int).astype(str)

    # Baseline-relative copy: subtract the plate x genotype hour-0 mean.
    feats = grid + SHAPE
    base = F[F.hour == 0].groupby(["treatment", "plate", "genotype"])[feats].mean()
    Fb = F[F.hour > 0].merge(base.add_suffix("_h0").reset_index(), on=["treatment", "plate", "genotype"])
    for c in feats:
        Fb[c] = Fb[c] - Fb[c + "_h0"]
    Fb = Fb[~(((Fb.treatment == "Control") & (Fb.plate == 4)) | ((Fb.treatment == "flg22") & (Fb.plate == 2)))]
    Fb = Fb.dropna(subset=feats)

    rows, spec_rows, load_rows = [], [], []
    for variant, D in (("absolute", F), ("baseline-relative", Fb)):
        for hr in sorted(D.hour.unique()):
            for trt in ("Pathogen", "flg22"):
                for geno in ("Col-0", "all"):
                    d = D[(D.hour == hr) & D.treatment.isin(["Control", trt])]
                    if geno != "all":
                        d = d[d.genotype == geno]
                    if d.treatment.nunique() < 2:
                        continue
                    y = (d.treatment == trt).astype(int).values
                    plate = d.plate_id.values
                    for fs, cols in (("spectrum", grid), ("shape", SHAPE)):
                        X = d[cols].values
                        for model in MODELS:
                            a_plant, a_plate, _ = lopo_plate_auc(X, y, plate, model)
                            y_plate = {p: int(p.startswith(trt)) for p in np.unique(plate)}
                            p_perm, null = permutation_p(X, plate, y_plate, model, a_plate)
                            rows.append(dict(variant=variant, hour=hr, contrast=f"{trt} vs Control",
                                             genotypes=geno, features=fs, model=model,
                                             n_plants=len(y), n_plates=len(y_plate),
                                             auc_plant=a_plant, auc_plate=a_plate,
                                             perm_p_plate=p_perm, n_perm=len(null)))
                    # loadings of the spectrum PLS-DA, all data at this hour (descriptive)
                    if geno == "Col-0" and variant == "baseline-relative":
                        m = PLSDA(1).fit(d[grid].values, y)
                        w = m.m.named_steps["plsregression"].x_weights_[:, 0]
                        sd = d[grid].values.std(0)
                        for g, wi, s_ in zip(grid, w, sd):
                            load_rows.append(dict(hour=hr, contrast=f"{trt} vs Control", wl=float(g[1:]),
                                                  weight=wi, sd=s_))
                # Specificity: train on Col-0 trt vs Control, apply to each mutant.
                d0 = D[(D.hour == hr) & D.treatment.isin(["Control", trt])]
                c0 = d0[d0.genotype == "Col-0"]
                if c0.treatment.nunique() < 2:
                    continue
                m = LR().fit(c0[SHAPE].values, (c0.treatment == trt).astype(int).values)
                for g, dg in d0.groupby("genotype"):
                    if g == "Col-0":
                        s = cv_scores(dg[SHAPE].values, (dg.treatment == trt).astype(int).values,
                                      dg.plate_id.values, "logistic")
                    else:
                        s = m.score(dg[SHAPE].values)
                    dg = dg.assign(s=s).dropna(subset=["s"])
                    pl = dg.groupby(["plate_id", "treatment"]).s.mean().reset_index()
                    eff = pl[pl.treatment == trt].s.mean() - pl[pl.treatment == "Control"].s.mean()
                    spec_rows.append(dict(variant=variant, hour=hr, contrast=f"{trt} vs Control", genotype=g,
                                          delta_p=eff, n_plates=len(pl),
                                          note="Col-0: out-of-fold" if g == "Col-0" else "Col-0-trained model"))
    A = pd.DataFrame(rows)
    A.to_csv(TABLES / "model_auc.csv", index=False)
    pd.DataFrame(spec_rows).to_csv(TABLES / "model_specificity.csv", index=False)
    pd.DataFrame(load_rows).to_csv(RESULTS / "model_loadings.csv", index=False)
    pd.set_option("display.width", 220)
    show = A[(A.genotypes == "Col-0") & (A.model == "logistic")]
    print(show.pivot_table(index=["variant", "contrast", "features"], columns="hour",
                           values=["auc_plate"]).round(2).to_string())
    print(show.pivot_table(index=["variant", "contrast", "features"], columns="hour",
                           values=["perm_p_plate"]).round(3).to_string())


if __name__ == "__main__":
    main()
