"""Assign genotype lane and plant number to every segmented seedling.

Layout (checked against the 2016 hand ROIs; see results/label_validation.md): each row-scan
images one row of seedlings along the scan (line) axis. Genotype lanes are columns along that
axis, shared by the plate's three rows: five lanes in set A (A..E, two seedlings per lane per
row) and three in set B (Col-0, fls2-17, fls2-101, three per lane per row; vendor report V2).
Seedlings were placed by hand, so positions jitter by tens of pixels and some are missing.

Per plate x timepoint, the pooled seedling line positions of the three rows are clustered
into lanes (optimal 1-D k-means). Plant numbers are the reading order within a lane (row 1
to 3, then along the line), which is how the 2016 hand ROIs are numbered. The scan direction
(lane A at low or high line numbers) is chosen per set x timepoint by agreement with the hand
ROIs, which are matched to seedlings on spectral shape and intensity.

Writes results/seedlings_labelled.csv.gz, results/label_validation.md and
results/label_validation_pairs.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import LANES_A, LANES_B, REPO, RESULTS  # noqa: E402

N_LANES = {"A": 5, "B": 3}
LETTERS = {"A": "ABCDE", "B": "ABC"}
LANE_MAP = {"A": LANES_A, "B": LANES_B}


def kmeans_1d(x, k):
    """Exact 1-D k-means by dynamic programming on sorted values. Returns labels 0..k-1
    in increasing order of position."""
    order = np.argsort(x)
    xs = np.asarray(x, float)[order]
    n = len(xs)
    k = min(k, n)
    c1, c2 = np.concatenate([[0], np.cumsum(xs)]), np.concatenate([[0], np.cumsum(xs ** 2)])

    def sse(i, j):  # cost of xs[i:j]
        s, s2, m = c1[j] - c1[i], c2[j] - c2[i], j - i
        return s2 - s * s / m

    D = np.full((k + 1, n + 1), np.inf)
    B = np.zeros((k + 1, n + 1), dtype=int)
    D[0, 0] = 0
    for c in range(1, k + 1):
        for j in range(c, n + 1):
            for i in range(c - 1, j):
                v = D[c - 1, i] + sse(i, j)
                if v < D[c, j]:
                    D[c, j], B[c, j] = v, i
    lab_sorted = np.zeros(n, dtype=int)
    j = n
    for c in range(k, 0, -1):
        i = B[c, j]
        lab_sorted[i:j] = c - 1
        j = i
    lab = np.empty(n, dtype=int)
    lab[order] = lab_sorted
    return lab


def assign(S):
    out = []
    for (s, hr, trt, pl), g in S.groupby(["set", "hour", "treatment", "plate"]):
        g = g.copy()
        g["lane_idx"] = kmeans_1d(g.line_c.values, N_LANES[s])
        for direction in ("fwd", "rev"):
            li = g.lane_idx if direction == "fwd" else N_LANES[s] - 1 - g.lane_idx
            g[f"lane_{direction}"] = [LETTERS[s][i] for i in li]
            key = g.line_c if direction == "fwd" else -g.line_c
            g[f"plant_{direction}"] = (g.assign(_k=key).sort_values(["row", "_k"])
                                       .groupby(f"lane_{direction}").cumcount() + 1).reindex(g.index)
        out.append(g)
    return pd.concat(out)


def direction_scores(L):
    """Per set-A plate x timepoint: agreement between the 2016 hand ROIs and the seedlings that
    each scan direction would assign to them. Score = mean of within-plate Spearman
    correlations (ROI vs assigned seedling) of F685/F740, red-peak FWHM and peak intensity."""
    from scipy.stats import spearmanr
    F = pd.read_csv(RESULTS / "roi_features.csv.gz")
    F = F[F["set"] == "A"]
    R = pd.read_parquet(RESULTS / "roi_spectra_A.parquet")
    wcols = [c for c in R.columns if c.startswith("I_")]
    F = F.merge(R[["spectrum_id"]].assign(roi_peak=R[wcols].max(axis=1).values), on="spectrum_id")
    rows = []
    for (hr, trt, pl), g in L[L["set"] == "A"].groupby(["hour", "treatment", "plate"]):
        f = F[(F.hour == hr) & (F.treatment == trt) & (F.plate == pl)]
        rec = dict(set="A", hour=hr, treatment=trt, plate=pl, n_roi=len(f), n_seedlings=len(g))
        for d in ("fwd", "rev"):
            m = f.merge(g, left_on=["lane", "plant"], right_on=[f"lane_{d}", f"plant_{d}"],
                        suffixes=("_roi", "_seed"))
            rec[f"n_pairs_{d}"] = len(m)
            if len(m) >= 8:
                rs = [spearmanr(m.f685_f740_roi, m.f685_f740_seed).statistic,
                      spearmanr(m.red_fwhm_nm_roi, m.red_fwhm_nm_seed).statistic,
                      spearmanr(m.roi_peak, m.f685_cps).statistic]
                rec[f"score_{d}"] = float(np.nanmean(rs))
            else:
                rec[f"score_{d}"] = np.nan
        rows.append(rec)
    D = pd.DataFrame(rows)
    D["direction"] = np.where(D.score_fwd >= D.score_rev, "fwd", "rev")
    D.loc[D[["score_fwd", "score_rev"]].isna().all(axis=1), "direction"] = None
    D["margin"] = (D.score_fwd - D.score_rev).abs()
    D.to_csv(RESULTS / "label_direction_scores.csv", index=False)
    return D


def main():
    S = pd.read_csv(RESULTS / "seedlings_all.csv.gz")
    S = S[S.plate.notna()].copy()
    L = assign(S)
    D = direction_scores(L)
    key = ["set", "hour", "treatment", "plate"]
    L = L.merge(D[key + ["direction", "margin", "score_fwd", "score_rev"]], on=key, how="left")
    # Set B ROIs are per leaf, so set-B direction follows the vendor's stated order (Col-0
    # first in each image), taken as fwd pending confirmation (FACTS R9).
    L.loc[L["set"] == "B", "direction"] = "fwd"
    has = L.direction.notna()
    L["lane"] = np.where(L.direction == "fwd", L.lane_fwd, np.where(L.direction == "rev", L.lane_rev, None))
    L["plant"] = np.where(L.direction == "fwd", L.plant_fwd, np.where(L.direction == "rev", L.plant_rev, np.nan))
    L["genotype"] = [LANE_MAP[s].get(l) if isinstance(l, str) else None for s, l in zip(L["set"], L.lane)]
    med = L.groupby("cube_id").n_px.transform("median")
    L["possibly_merged"] = L.n_px > 1.7 * med
    L.to_csv(RESULTS / "seedlings_labelled.csv.gz", index=False)

    Da = D[D["set"] == "A"]
    notes = ["# Label assignment and validation\n",
             "Genotype lanes are found per plate x timepoint by 1-D k-means on seedling positions "
             "(three row-scans pooled). Plates were not always placed in the same orientation, so the "
             "direction (lane A at low or high line number) is chosen per plate x timepoint as the one "
             "whose assigned seedlings best track the 2016 hand ROIs (within-plate Spearman correlation "
             "of F685/F740, red-peak width and peak intensity; mean of the three).\n",
             f"- Plate x timepoints with hand ROIs: {int(Da.direction.notna().sum())} of {len(Da)}; "
             f"direction fwd {int((Da.direction == 'fwd').sum())}, rev {int((Da.direction == 'rev').sum())}.",
             f"- Score of the chosen direction: median {np.nanmedian(np.maximum(Da.score_fwd, Da.score_rev)):.2f}; "
             f"of the rejected one: median {np.nanmedian(np.minimum(Da.score_fwd, Da.score_rev)):.2f}.",
             f"- Low-confidence choices (margin < 0.2): {int((Da.margin < 0.2).sum())}.",
             "- Plates without hand ROIs (set A Pathogen 48 h) get no genotype label; they enter only "
             "treatment-level analyses.\n",
             Da[["hour", "treatment", "plate", "n_roi", "n_seedlings", "score_fwd", "score_rev", "direction",
                 "margin"]].round(2).to_markdown(index=False),
             f"\nSeedlings labelled: {int(L.genotype.notna().sum())} of {len(L)}; possibly merged "
             f"neighbours: {int(L.possibly_merged.sum())}."]
    (RESULTS / "label_validation.md").write_text("\n".join(notes) + "\n")
    print("\n".join(notes[:7]))
    print(notes[-1])


if __name__ == "__main__":
    main()
