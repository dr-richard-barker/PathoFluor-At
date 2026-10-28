"""Import the 2016 hand-drawn ROI spectra and compute exposure-invariant shape features.

Reads the copies in data/original_2016/ (identical to the drive; see roi_manifest.csv sha256).

Writes
  results/roi_spectra.parquet   one row per unique spectrum: design keys, provenance, raw values
  results/roi_features.csv      shape features + area-normalised spectrum on the common grid
  results/pilot_leaf_area.csv   the Feb-Mar 2016 pilot tables in tidy form
  results/roi_import_report.md  counts, duplicates and key conflicts
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import LANES_B, META, REPO, RESULTS  # noqa: E402
from pathofluor.features import GRID, shape_features, to_grid  # noqa: E402

ORIG = REPO / "data" / "original_2016"
KEY = ["set", "hour", "treatment", "plate", "lane", "plant"]
LOC_PREF = {"timepoint_export": 0, "setB_export": 0, "genotype_sorted": 1, "use_subset": 2}


def read_spectrum(rel):
    a = np.loadtxt(ORIG / rel, delimiter=",")
    return a[:, 0], a[:, 1]


def main():
    rm = pd.read_csv(META / "roi_manifest.csv")
    report = []

    # ---- pilot tables (not spectra)
    pil = rm[rm["set"] == "pilot"]
    rows = []
    for r in pil.itertuples():
        t = pd.read_csv(ORIG / r.relpath, header=None)
        for _, row in t.iterrows():
            for j, v in enumerate(row.iloc[1:], start=1):
                rows.append(dict(genotype=r.genotype, treatment=r.treatment, day=int(row.iloc[0]),
                                 column=j, leaf_area_cm2_as_tabulated=v, source=r.relpath))
    pd.DataFrame(rows).to_csv(RESULTS / "pilot_leaf_area.csv", index=False)
    report.append(f"Pilot: {len(pil)} tables, {len(rows)} values (units: see FACTS_PENDING R10/P12).")

    # ---- spectra: one row per unique content hash, best-provenance copy first
    sp = rm[rm["set"].isin(["A", "B"])].copy()
    sp["_pref"] = sp.location.map(LOC_PREF)
    in_use = sp[sp.location == "use_subset"].groupby("spectrum_id").size().rename("n_use_copies")
    sp = sp.sort_values(["spectrum_id", "_pref"])
    uniq = sp.drop_duplicates("spectrum_id").drop(columns="_pref").set_index("spectrum_id")
    uniq["in_use_subset"] = uniq.index.isin(in_use.index)
    uniq["n_copies"] = sp.groupby("spectrum_id").size()
    report.append(f"Spectra: {len(sp)} files -> {len(uniq)} unique "
                  f"(A {int((uniq['set'] == 'A').sum())}, B {int((uniq['set'] == 'B').sum())}).")

    # Same design key, different content = a real conflict (re-drawn ROI); keep both, flag.
    conflict = uniq.groupby(KEY).filter(lambda g: len(g) > 1)
    uniq["key_conflict"] = uniq.index.isin(conflict.index)
    report.append(f"Design-key conflicts (same hour/treatment/plate/lane/plant, different spectrum): "
                  f"{len(conflict)} spectra in {conflict.groupby(KEY).ngroups} keys.")
    uniq.loc[uniq["set"] == "B", "genotype"] = uniq.loc[uniq["set"] == "B", "lane"].map(LANES_B)

    wl_ref, vals, feats, grids = {}, [], [], []
    for sid, r in uniq.iterrows():
        wl, y = read_spectrum(r.relpath)
        wl_ref.setdefault(r["set"], wl)
        if len(wl) != len(wl_ref[r["set"]]) or not np.allclose(wl, wl_ref[r["set"]], atol=0.02):
            raise SystemExit(f"wavelength axis differs in {r.relpath}")
        vals.append(y)
        feats.append(shape_features(wl, y))
        grids.append(to_grid(wl, y))

    meta_cols = ["set", "hour", "treatment", "plate", "lane", "genotype", "plant", "tag",
                 "file_copy", "relpath", "location", "in_use_subset", "n_copies", "key_conflict"]
    meta = uniq[meta_cols].reset_index()

    # Raw spectra, per set (axes differ: 324 bands in A, 406 in B).
    for s in ("A", "B"):
        idx = np.nonzero(meta["set"].values == s)[0]
        wl = wl_ref[s]
        cols = {f"I_{w:.2f}": np.array([vals[i] for i in idx])[:, k] for k, w in enumerate(wl)}
        pd.concat([meta.iloc[idx].reset_index(drop=True), pd.DataFrame(cols)], axis=1) \
          .to_parquet(RESULTS / f"roi_spectra_{s}.parquet", index=False)

    F = pd.concat([meta, pd.DataFrame(feats),
                   pd.DataFrame(np.array(grids), columns=[f"n{g:.0f}" for g in GRID])], axis=1)
    F.to_csv(RESULTS / "roi_features.csv.gz", index=False)

    report.append("\nSpectra per set x hour x treatment:\n")
    report.append(F.groupby(["set", "hour", "treatment"]).size().unstack().to_markdown())
    report.append("\nSpectra per set x genotype:\n")
    report.append(F.groupby(["set", "genotype"]).size().to_frame("n").to_markdown())
    report.append("\nROI quality tags (set A):\n")
    report.append(F[F["set"] == "A"].tag.fillna("(none)").value_counts().to_frame("n").to_markdown())
    (RESULTS / "roi_import_report.md").write_text("# ROI import report\n\n" + "\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
