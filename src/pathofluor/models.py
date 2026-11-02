"""Classifiers and plate-level cross-validation shared by scripts/06_models.py and
scripts/11_field_analyses.py.

The plate is the experimental unit: every fold holds out whole plates, and AUC is reported at
plate level (mean score per plate) as well as at plant level.
"""
import itertools

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SHAPE = ["f685_f740", "red_peak_nm", "red_fwhm_nm", "centroid_nm", "farred_fraction", "shortwave_fraction"]

# Plates whose hour-0 scans were partly the upright rescans; excluded from baseline-relative work.
BASELINE_EXCLUDED = (("Control", 4), ("flg22", 2))


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


def baseline_relative(F, feats):
    """Subtract each plate x genotype's hour-0 mean from its later spectra (hour > 0 rows only)."""
    base = F[F.hour == 0].groupby(["treatment", "plate", "genotype"])[feats].mean()
    Fb = F[F.hour > 0].merge(base.add_suffix("_h0").reset_index(), on=["treatment", "plate", "genotype"])
    for c in feats:
        Fb[c] = Fb[c] - Fb[c + "_h0"]
    excl = np.zeros(len(Fb), bool)
    for trt, pl in BASELINE_EXCLUDED:
        excl |= (Fb.treatment == trt).values & (Fb.plate == pl).values
    return Fb[~excl].dropna(subset=feats)


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
