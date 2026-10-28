"""Single sequential pass over every raw cube (about 2.7 h at 41 MB/s on the USB drive).

For each cube this
  * hashes the raw file (SHA-256) while reading it,
  * estimates the per-band dark level and noise from background pixels,
  * keeps every pixel above a liberal 685 nm threshold (dilated by 1 px) with its raw
    spectrum over 640-812 nm, its maximum raw value across all bands (saturation check)
    and its mean over the 420-620 nm dark window,
  * keeps full-resolution raw 685 nm and 740 nm images for segmentation and figures.

Outputs (resumable; a cube is skipped when both exist):
  cache/harvest/<cube_id>.npz   local working cache, not committed (about 4 GB in total)
  results/cube_qc/<cube_id>.json  committed per-cube QC + SHA-256

Usage: python scripts/02_harvest_cubes.py [--only CUBE_ID ...] [--limit N]
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, REPO, RESULTS, SRC  # noqa: E402
from pathofluor.envi import read_cube  # noqa: E402

CACHE = REPO / "cache" / "harvest"
QC = RESULTS / "cube_qc"
SPEC_WINDOW = (460.0, 812.0)  # 488 nm excitation; 500-800 nm emission per the 2016 vendor report
SAT = 4095  # 12-bit camera mode for every cube in this study


def band(wl, target):
    return int(np.argmin(np.abs(wl - target)))


def harvest(row):
    h = hashlib.sha256()
    t0 = time.time()
    hd, cube = read_cube(SRC / row.relpath_hdr, sha256=h)
    t_read = time.time() - t0
    wl = hd["wavelength"]
    L, B, S = cube.shape

    i685, i740 = band(wl, 685), band(wl, 740)
    img685 = np.ascontiguousarray(cube[:, i685, :])
    img740 = np.ascontiguousarray(cube[:, i740, :])

    # Background = pixels whose 685 nm value sits in the dark-level distribution.
    f = img685.astype(np.float32)
    med = float(np.median(f))
    sig = max(float(np.median(np.abs(f - med))) * 1.4826, 1.0)
    bg = f < med + 3 * sig
    # Per-band dark level and noise from a random background subsample.
    ys, xs = np.nonzero(bg)
    rng = np.random.default_rng(0)
    pick = rng.choice(len(ys), size=min(len(ys), 200_000), replace=False)
    bgspec = cube[ys[pick], :, xs[pick]].astype(np.float32)          # (n, B)
    dark = np.median(bgspec, axis=0)
    dark_sd = bgspec.std(axis=0)

    # Liberal foreground: 685 nm above 5 sigma, dilated by 1 px to keep leaf edges.
    fg = ndimage.binary_dilation(f > med + 5 * sig, iterations=1)
    py, px = np.nonzero(fg)
    sel = (wl >= SPEC_WINDOW[0]) & (wl <= SPEC_WINDOW[1])
    spectra = cube[py, :, px][:, sel]                                 # (n, b) uint16
    pixmax = cube[py, :, px].max(axis=1)                              # saturation check
    darkwin = (wl >= 420) & (wl <= 620)
    pix_dark_mean = cube[py, :, px][:, darkwin].mean(axis=1).astype(np.float32)

    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        CACHE / f"{row.cube_id}.npz",
        wl_all=wl, wl=wl[sel], dark=dark, dark_sd=dark_sd,
        img685=img685, img740=img740, y=py.astype(np.int16), x=px.astype(np.int16),
        spectra=spectra, pixmax=pixmax, pix_dark_mean=pix_dark_mean,
        bg_median685=np.float32(med), bg_sigma685=np.float32(sig))

    qc = dict(
        cube_id=row.cube_id, relpath_raw=row.relpath_raw, sha256_raw=h.hexdigest(),
        lines=L, bands=B, samples=S, read_seconds=round(t_read, 1),
        bg_median685=med, bg_sigma685=sig,
        dark_mean_420_620=float(dark[darkwin].mean()), dark_sd_420_620=float(dark_sd[darkwin].mean()),
        n_fg_pixels=int(fg.sum()), fg_fraction=float(fg.mean()),
        n_saturated_fg_pixels=int((pixmax >= SAT).sum()),
        cube_max=int(cube.max()),
        fg_mean_minus_dark_in_420_620=float((pix_dark_mean - dark[darkwin].mean()).mean()) if len(py) else None,
        harvested_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    QC.mkdir(parents=True, exist_ok=True)
    (QC / f"{row.cube_id}.json").write_text(json.dumps(qc, indent=1))
    return qc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    cm = pd.read_csv(META / "cube_manifest.csv")
    cm = cm[cm["set"].isin(["A", "B"])]
    # Set A samples first (the primary analysis), then set B, then references/artefacts.
    order = {"sample": 0, "bacteria_scan": 1, "reference": 2, "reference_chroma": 2, "artefact_scan": 3}
    cm = cm.assign(_o=cm.role.map(order), _s=cm["set"]).sort_values(["_s", "_o", "hour", "treatment", "plate", "row"])
    if a.only:
        cm = cm[cm.cube_id.isin(a.only)]
    todo = [r for r in cm.itertuples()
            if not ((CACHE / f"{r.cube_id}.npz").exists() and (QC / f"{r.cube_id}.json").exists())]
    if a.limit:
        todo = todo[:a.limit]
    log = QC / "_progress.log"
    QC.mkdir(parents=True, exist_ok=True)
    print(f"{len(todo)} cubes to harvest ({len(cm) - len(todo)} already done)", flush=True)
    t0 = time.time()
    done_bytes = 0
    for i, r in enumerate(todo, 1):
        try:
            qc = harvest(r)
            done_bytes += r.raw_bytes
            rate = done_bytes / 1e6 / (time.time() - t0)
            msg = (f"[{i}/{len(todo)}] {r.cube_id}: fg {qc['n_fg_pixels']} px, "
                   f"sat {qc['n_saturated_fg_pixels']}, {rate:.0f} MB/s")
        except Exception as e:  # keep going; failures are listed in the log
            msg = f"[{i}/{len(todo)}] {r.cube_id}: FAILED {type(e).__name__}: {e}"
        print(msg, flush=True)
        with open(log, "a") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")


if __name__ == "__main__":
    main()
