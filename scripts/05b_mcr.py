"""Pixel-level multivariate curve resolution (MCR-ALS; de Juan & Tauler 2021) on set-A cubes.

The 2016 vendor analysis (FACTS V1) ran MCR on two plates and reported three components:
two chlorophyll-like ones and a broad autofluorescence component that rose in infected plants.
We refit on pixels from every set-A sample cube so the component can be tested at plate level.

D (pixels x bands, dark-subtracted, divided by exposure) = C S^T, with C, S >= 0.
Initial S: three purest pixels by the SIMPLISMA-style criterion (largest residual norm after
projecting out the previous picks). Then alternating non-negative least squares
(scipy.optimize.nnls row-wise via an active-set solver in blocks), S rows normalised to unit area.

Fit on a random subsample of seedling pixels (unsaturated) from every cube; then every seedling's
mean pixel spectrum is unmixed with the fitted S. Writes
  results/mcr_components.csv          wavelength x component spectra
  results/mcr_seedling_scores.csv.gz  per seedling: component amounts and fractions
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, REPO, RESULTS  # noqa: E402
from pathofluor.segment import load, seedlings  # noqa: E402

K = 3
PIX_PER_CUBE = 1500
WIN = (500.0, 800.0)
rng = np.random.default_rng(1)


def nnls_rows(A, S):
    """Solve min ||a - c S|| for c >= 0 for every row a of A (S: K x bands)."""
    St = S.T
    return np.array([nnls(St, a)[0] for a in A])


def pure_init(D, k):
    picks, R = [], D.copy()
    for _ in range(k):
        i = int(np.argmax(np.linalg.norm(R, axis=1)))
        picks.append(i)
        v = R[i] / np.linalg.norm(R[i])
        R = R - np.outer(R @ v, v)
    return D[picks].copy()


def mcr_als(D, k, iters=60, tol=1e-6):
    S = pure_init(D, k)
    S /= S.sum(1, keepdims=True)
    last = np.inf
    for it in range(iters):
        C = nnls_rows(D, S)
        S = np.array([nnls(C, D[:, j])[0] for j in range(D.shape[1])]).T
        area = S.sum(1, keepdims=True)
        area[area == 0] = 1
        S /= area
        C = nnls_rows(D, S)
        err = np.linalg.norm(D - C @ S) / np.linalg.norm(D)
        if abs(last - err) < tol:
            break
        last = err
    return C, S, err, it + 1


def main():
    cm = pd.read_csv(META / "cube_manifest.csv").set_index("cube_id")
    cubes = [c for c in cm.index if c.startswith("A_H") and (REPO / "cache" / "harvest" / f"{c}.npz").exists()]
    if not cubes:
        raise SystemExit("no harvested set-A cubes")
    samples, wl = [], None
    for c in cubes:
        h = load(REPO / "cache" / "harvest" / f"{c}.npz")
        sel = (h["wl"] >= WIN[0]) & (h["wl"] <= WIN[1])
        wl = h["wl"][sel]
        dark = h["dark"][np.isin(h["wl_all"], h["wl"])][sel]
        lab, _ = seedlings(h)
        inseed = lab[h["y"].astype(int), h["x"].astype(int)] > 0
        ok = np.nonzero(inseed & (h["pixmax"] < 4095))[0]
        take = rng.choice(ok, size=min(PIX_PER_CUBE, len(ok)), replace=False)
        samples.append((h["spectra"][take][:, sel].astype(np.float32) - dark) / cm.loc[c, "tint_s"])
    D = np.clip(np.vstack(samples), 0, None)
    print(f"fitting MCR-ALS on {D.shape[0]} pixels x {D.shape[1]} bands from {len(cubes)} cubes", flush=True)
    C, S, err, n_it = mcr_als(D, K)
    order = np.argsort([wl[np.argmax(s)] for s in S])[::-1]   # longest-wavelength peak first
    S = S[order]
    pd.DataFrame({"wl": wl, **{f"comp{i + 1}": S[i] for i in range(K)}}).to_csv(RESULTS / "mcr_components.csv", index=False)
    print(f"lack of fit {err:.3f} after {n_it} iterations; component peaks (nm):",
          [round(float(wl[np.argmax(s)]), 1) for s in S])

    L = pd.read_csv(RESULTS / "seedlings_labelled.csv.gz")
    rows = []
    for c, g in L[L["set"] == "A"].groupby("cube_id"):
        z = np.load(REPO / "cache" / "seedlings" / f"{c}.npz")
        sel = (z["wl"] >= WIN[0]) & (z["wl"] <= WIN[1])
        Y = np.clip(z["spectra"][:, sel] / cm.loc[c, "tint_s"], 0, None)
        Cs = nnls_rows(Y, S)
        tot = Cs.sum(1, keepdims=True)
        tot[tot == 0] = np.nan
        for (_, r), cc, fr in zip(g.iterrows(), Cs, Cs / tot):
            rows.append(dict(cube_id=c, seedling=r.seedling, **{f"mcr{i + 1}": cc[i] for i in range(K)},
                             **{f"mcr{i + 1}_frac": fr[i] for i in range(K)}))
    pd.DataFrame(rows).to_csv(RESULTS / "mcr_seedling_scores.csv.gz", index=False)
    print(f"scored {len(rows)} seedlings")


if __name__ == "__main__":
    main()
