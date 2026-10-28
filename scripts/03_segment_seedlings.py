"""Segment seedlings in every harvested cube and compute per-seedling features.

Writes (resumable, one file per cube):
  cache/seedlings/<cube_id>.npz        per-seedling mean spectra (local cache)
  results/seedlings/<cube_id>.csv      per-seedling position, size, saturation and features
and, after all cubes are present, results/seedlings_all.csv.gz.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, REPO, RESULTS  # noqa: E402
from pathofluor.segment import load, seedling_features, seedlings  # noqa: E402

HARV = REPO / "cache" / "harvest"
CACHE = REPO / "cache" / "seedlings"
OUT = RESULTS / "seedlings"


def main(force=False):
    cm = pd.read_csv(META / "cube_manifest.csv").set_index("cube_id")
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    done = 0
    for npz in sorted(HARV.glob("*.npz")):
        cid = npz.stem
        out_csv = OUT / f"{cid}.csv"
        if out_csv.exists() and not force:
            continue
        if not (RESULTS / "cube_qc" / f"{cid}.json").exists():
            continue  # the harvester writes the QC json after the npz: npz may be incomplete
        r = cm.loc[cid]
        if r.role not in ("sample", "bacteria_scan"):
            continue
        h = load(npz)
        _, segs = seedlings(h)
        rows, specs, specs_all = [], [], []
        for d in segs:
            f = seedling_features(h["wl"], d, r.tint_s)
            rows.append(dict(cube_id=cid, **{k: r[k] for k in ("set", "hour", "treatment", "plate", "row", "laser", "orientation")},
                             tint_s=r.tint_s, **{k: v for k, v in d.items() if not k.startswith("mean_spectrum")}, **f))
            specs.append(d["mean_spectrum"])
            specs_all.append(d["mean_spectrum_all"])
        pd.DataFrame(rows).to_csv(out_csv, index=False)
        np.savez_compressed(CACHE / f"{cid}.npz", wl=h["wl"], spectra=np.array(specs), spectra_all=np.array(specs_all))
        done += 1
    print(f"segmented {done} new cubes")
    parts = [pd.read_csv(p) for p in sorted(OUT.glob("*.csv"))]
    if parts:
        allr = pd.concat(parts, ignore_index=True)
        allr.to_csv(RESULTS / "seedlings_all.csv.gz", index=False)
        print(allr.groupby(["set", "hour", "treatment"]).size().unstack())


if __name__ == "__main__":
    main(force="--force" in sys.argv)
