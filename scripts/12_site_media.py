"""Images and 3-D data for the project page, rendered from the cached raw cubes.

Needs cache/harvest/ (written by 02_harvest_cubes.py from the raw drive). Writes

  docs/media/plates/<layer>_<treatment>_P<plate>_H<hh>.webp   set-A plate composites
  docs/data/plates.json        image index: lane labels, colour scales, notes
  docs/data/cube/*.bin + docs/data/cube.json   binned plant-pixel spectra for the 3-D viewer
  docs/data/trajectories.json  plate-level change from hour 0 (tables/seedling_plate_changes.csv)
  docs/media/hero.webp, docs/thumb.png
  figures/figS4_hypercube.png  static view of one cube (supplement and no-WebGL fallback)

Plate composite: the three row-scans of a plate stacked top to bottom, each rotated so the
scan (line) axis runs left to right. Each row-scan is cropped to CROP samples centred on its
seedlings (hour-0 scans used a wider camera window), and flipped when the label direction for
that plate x hour is 'rev', so lane A (Col-0) is on the left. Pixels are binned BIN x BIN.

Layers:
  cps    685 nm emission, dark-subtracted and divided by exposure (counts/s), one fixed linear scale
  raw    685 nm counts per exposure as recorded (dark-subtracted, NOT exposure-corrected), linear
  ratio  F685/F740 per binned block of plant pixels, log2 relative to the Control median
Plates are not registered across time; seedlings were repositioned between scans.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import FIGURES, LANES_A, META, REPO, RESULTS, TABLES  # noqa: E402

HARV = REPO / "cache" / "harvest"
DOCS = REPO / "docs"
BIN = 4
CROP = 708           # samples kept per row-scan, centred on the seedlings
WIDTH = 1820         # lines; every row-scan is padded to this so all composites match
HOURS = [0, 1, 2, 3, 24, 48]
TREATMENTS = ["Control", "flg22", "Pathogen"]
CUBE_TRT = ["Control", "Pathogen"]   # 3-D viewer: plate 1, row 1
CUBE_WL = np.arange(500.0, 800.0 + 1e-9, 5.0)

# Colour ramps (validated with the dataviz palette validator, see README).
RAMP_INTENSITY = ["#000000", "#3b0a0c", "#7f1416", "#c42a1f", "#ef6a3c", "#fbb28f", "#fff1e8"]
RAMP_RATIO = ["#5e3c99", "#9e8ac8", "#9a9a9a", "#f2a65a", "#d95f02"]


def ramp(stops, n=256):
    c = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in stops], float)
    x = np.linspace(0, 1, len(stops))
    t = np.linspace(0, 1, n)
    return np.stack([np.interp(t, x, c[:, k]) for k in range(3)], 1).astype(np.uint8)


LUT_I, LUT_R = ramp(RAMP_INTENSITY), ramp(RAMP_RATIO)


def band(wl, w):
    return int(np.argmin(np.abs(np.asarray(wl) - w)))


def binned(a, b=BIN, how="mean"):
    H, W = (a.shape[0] // b) * b, (a.shape[1] // b) * b
    v = a[:H, :W].reshape(H // b, b, W // b, b)
    return v.mean(axis=(1, 3)) if how == "mean" else v.sum(axis=(1, 3))


def orient(img, centre, direction):
    """(lines, samples) -> (CROP, WIDTH) display array: samples cropped round `centre`,
    transposed so lines run left to right, flipped for 'rev', padded on the right."""
    lo = int(np.clip(centre - CROP // 2, 0, max(img.shape[1] - CROP, 0)))
    a = img[:, lo:lo + CROP].T
    if a.shape[0] < CROP:
        a = np.pad(a, ((0, CROP - a.shape[0]), (0, 0)))
    if direction == "rev":
        a = a[:, ::-1]
    return np.pad(a[:, :WIDTH], ((0, 0), (0, max(WIDTH - a.shape[1], 0)))), lo


def plant_mask(f):
    med = float(np.median(f))
    sig = max(float(np.median(np.abs(f - med))) * 1.4826, 1.0)
    return f > med + 5 * sig, sig


def row_layers(cid, tint):
    h = np.load(HARV / f"{cid}.npz")
    wl_all, dark = h["wl_all"], h["dark"]
    f685 = h["img685"].astype(np.float32) - dark[band(wl_all, 685)]
    f740 = h["img740"].astype(np.float32) - dark[band(wl_all, 740)]
    mask, _ = plant_mask(h["img685"].astype(np.float32))
    centre = float(np.median(h["x"])) if len(h["x"]) else h["img685"].shape[1] / 2
    return dict(raw=f685, cps=f685 / tint, f740=f740, mask=mask.astype(np.float32)), centre


def composites(cm, L):
    """Binned display arrays per (treatment, plate, hour) and lane-label positions.
    Per block: raw and cps means; num/den = summed F685/F740 counts over plant pixels; m = plant fraction."""
    dirs = L[L["set"] == "A"].groupby(["hour", "treatment", "plate"]).direction.first()
    out, labels = {}, {}
    for trt in TREATMENTS:
        for p in range(1, 5):
            for hr in HOURS:
                d = dirs.get((float(hr), trt, float(p)))
                d = d if isinstance(d, str) else None
                rows, lab = [], []
                for r in (1, 2, 3):
                    cid = f"A_H{hr:02d}_{trt}_P{p}_R{r}"
                    lay, centre = row_layers(cid, cm.loc[cid].tint_s)
                    o = {k: orient(v, centre, d)[0] for k, v in lay.items()}
                    rows.append(dict(raw=binned(o["raw"]), cps=binned(o["cps"]), m=binned(o["mask"]),
                                     num=binned(o["raw"] * o["mask"], how="sum"),
                                     den=binned(o["f740"] * o["mask"], how="sum")))
                    nlines = lay["cps"].shape[0]
                    s = L[L.cube_id == cid]
                    if d and len(s):
                        x = (nlines - 1 - s.line_c) if d == "rev" else s.line_c
                        lab.append(pd.DataFrame(dict(lane=s.lane.values, x=x.values)))
                out[(trt, p, hr)] = {k: np.vstack([rw[k] for rw in rows]).astype(np.float32) for k in rows[0]}
                if lab:
                    lx = pd.concat(lab).groupby("lane").x.median()
                    labels[(trt, p, hr)] = [dict(x=round(float(v) / WIDTH, 4), lane=k, text=LANES_A[k]) for k, v in lx.items()]
                else:
                    labels[(trt, p, hr)] = []
    return out, labels


def log_ratio(a, ref):
    ok = (a["m"] >= 0.5) & (a["den"] > 0) & (a["num"] > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.log2(a["num"] / a["den"] / ref)
    return np.where(ok, lr, np.nan)


def to_rgb(layer, a, scale):
    if layer in ("cps", "raw"):
        t = np.clip(a[layer] / scale, 0, 1)
        return LUT_I[(t * 255).astype(np.uint8)]
    lr = log_ratio(a, scale["ref"])
    t = np.clip(lr / scale["lim"] / 2 + 0.5, 0, 1)
    rgb = LUT_R[(np.nan_to_num(t, nan=0.5) * 255).astype(np.uint8)]
    rgb[~np.isfinite(lr)] = 0
    return rgb


def main():
    cm = pd.read_csv(META / "cube_manifest.csv").set_index("cube_id")
    L = pd.read_csv(RESULTS / "seedlings_labelled.csv.gz")
    comp, labels = composites(cm, L)

    # Shared scales over plant blocks (>= half plant pixels) of every composite: 99.5th
    # percentile for intensities; ratio reference = median F685/F740 of Control plant blocks
    # (all hours); ratio limit = 95th percentile of |log2(ratio / reference)|.
    def plant(k, layer):
        return comp[k][layer][comp[k]["m"] >= 0.5]
    scale_cps = float(np.percentile(np.concatenate([plant(k, "cps") for k in comp]), 99.5))
    scale_raw = float(np.percentile(np.concatenate([plant(k, "raw") for k in comp]), 99.5))
    ctrl = np.concatenate([plant(k, "num") / np.maximum(plant(k, "den"), 1e-9) for k in comp if k[0] == "Control"])
    ref = float(np.median(ctrl[np.isfinite(ctrl) & (ctrl > 0)]))
    lr = np.concatenate([log_ratio(comp[k], ref).ravel() for k in comp])
    lim = float(np.percentile(np.abs(lr[np.isfinite(lr)]), 95))

    pdir = DOCS / "media" / "plates"
    pdir.mkdir(parents=True, exist_ok=True)
    for (trt, p, hr), a in comp.items():
        for layer, sc in (("cps", scale_cps), ("raw", scale_raw), ("ratio", dict(ref=ref, lim=lim))):
            Image.fromarray(to_rgb(layer, a, sc)).save(pdir / f"{layer}_{trt}_P{p}_H{hr:02d}.webp",
                                                       quality=82, method=6)
    H, W = comp[next(iter(comp))]["cps"].shape
    index = dict(
        width=W, height=H, hours=HOURS, treatments=TREATMENTS, plates=[1, 2, 3, 4],
        layers=dict(
            cps=dict(label="Exposure-corrected", units="counts/s at 685 nm",
                     max=round(scale_cps, 1), ramp=RAMP_INTENSITY),
            raw=dict(label="As recorded", units="counts per exposure at 685 nm",
                     max=round(scale_raw, 1), ramp=RAMP_INTENSITY),
            ratio=dict(label="F685/F740 ratio", units="log2 of F685/F740 relative to the Control median",
                       ref=round(ref, 3), lim=round(lim, 3), ramp=RAMP_RATIO)),
        labels={f"{t}_P{p}_H{h:02d}": v for (t, p, h), v in labels.items()},
        tint_s={f"{t}_P{p}_H{h:02d}": sorted({float(cm.loc[f'A_H{h:02d}_{t}_P{p}_R{r}'].tint_s) for r in (1, 2, 3)})
                for (t, p, h) in comp},
        source="cache/harvest (raw cubes); scripts/12_site_media.py")
    (DOCS / "data").mkdir(exist_ok=True)
    (DOCS / "data" / "plates.json").write_text(json.dumps(index, separators=(",", ":")))
    hero(comp, scale_cps)
    cubes(cm, L)
    trajectories()
    print(f"{len(comp)} plate composites x 3 layers ({W}x{H} px); cps max {scale_cps:.0f}, raw max {scale_raw:.0f}, "
          f"ratio ref {ref:.3f}, lim {lim:.3f}")


def hero(comp, scale):
    """Control | flg22 | Pathogen, plate 1, 24 h, exposure-corrected."""
    ims = [to_rgb("cps", comp[(t, 1, 24)], scale) for t in TREATMENTS]
    gap = np.zeros((ims[0].shape[0], 8, 3), np.uint8)
    strip = np.hstack([ims[0], gap, ims[1], gap, ims[2]])
    Image.fromarray(strip).save(DOCS / "media" / "hero.webp", quality=85, method=6)
    # Card thumbnail: the top two row-scans of the Control plate, 16:9, so seedlings stay legible.
    ctrl = Image.fromarray(ims[0])
    w = ctrl.size[0]
    ctrl.crop((0, 0, w, w * 9 // 16)).resize((320, 180), Image.LANCZOS).save(DOCS / "thumb.png")


def cubes(cm, L):
    """Plate 1, row 1: binned plant-pixel spectra (counts/s) on a 5 nm grid, uint8 sqrt scale."""
    dirs = L[L["set"] == "A"].groupby(["hour", "treatment", "plate"]).direction.first()
    recs, vals = [], []
    for trt in CUBE_TRT:
        for hr in HOURS:
            cid = f"A_H{hr:02d}_{trt}_P1_R1"
            h = np.load(HARV / f"{cid}.npz")
            wl, dark = h["wl"], h["dark"][np.isin(h["wl_all"], h["wl"])]
            tint = float(cm.loc[cid].tint_s)
            S = (h["spectra"].astype(np.float32) - dark) / tint
            G = np.stack([S[:, np.abs(wl - c) <= 2.5].mean(1) for c in CUBE_WL], 1)
            nlines = h["img685"].shape[0]
            d = dirs.get((float(hr), trt, 1.0))
            d = d if isinstance(d, str) else None
            centre = float(np.median(h["x"]))
            lo = int(np.clip(centre - CROP // 2, 0, max(h["img685"].shape[1] - CROP, 0)))
            keep = (h["x"] >= lo) & (h["x"] < lo + CROP)
            line = np.where(d == "rev", nlines - 1 - h["y"], h["y"]).astype(int)[keep]
            samp = (h["x"].astype(int) - lo)[keep]
            df = pd.DataFrame(G[keep]).assign(X=line // BIN, Y=samp // BIN)
            B = df.groupby(["X", "Y"]).mean().reset_index()
            recs.append(dict(treatment=trt, hour=hr, direction=d, tint_s=tint, B=B))
            vals.append(B[list(range(len(CUBE_WL)))].values.ravel())
    vmax = float(np.percentile(np.concatenate(vals), 99.5))
    cdir = DOCS / "data" / "cube"
    cdir.mkdir(parents=True, exist_ok=True)
    meta = []
    for r in recs:
        B = r.pop("B")
        q = (np.sqrt(np.clip(B[list(range(len(CUBE_WL)))].values / vmax, 0, 1)) * 255).round().astype(np.uint8)
        name = f"{r['treatment']}_P1_R1_H{r['hour']:02d}.bin"
        with open(cdir / name, "wb") as f:
            f.write(B.X.values.astype("<u2").tobytes())
            f.write(B.Y.values.astype("<u2").tobytes())
            f.write(q.tobytes())
        meta.append(dict(r, file=f"data/cube/{name}", n=len(B)))
    (DOCS / "data" / "cube.json").write_text(json.dumps(dict(
        wavelength_nm=CUBE_WL.tolist(), vmax_cps=round(vmax, 2), encoding="uint8 = 255*sqrt(cps/vmax_cps)",
        layout="n x uint16 X (line block), n x uint16 Y (sample block), n x bands uint8, row-major",
        bin_px=BIN, width=WIDTH // BIN, height=CROP // BIN, cubes=meta,
        source="cache/harvest (raw cubes); scripts/12_site_media.py"), separators=(",", ":")))
    figure_cube(meta)


def read_cube_bin(m):
    raw = (DOCS / m["file"]).read_bytes()
    n = m["n"]
    X = np.frombuffer(raw[:2 * n], "<u2")
    Y = np.frombuffer(raw[2 * n:4 * n], "<u2")
    return X, Y, np.frombuffer(raw[4 * n:], np.uint8).reshape(n, len(CUBE_WL))


def figure_cube(meta):
    """Static hypercube: plate 1 row 1 at 24 h as a cloud of (position, wavelength) points."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(LUT_I / 255.0)
    fig = plt.figure(figsize=(7.2, 3.6), dpi=200)
    for i, trt in enumerate(CUBE_TRT):
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        hr = 24
        X, Y, Q = read_cube_bin(next(m for m in meta if m["treatment"] == trt and m["hour"] == hr))
        k = np.nonzero(Q > 60)
        ax.scatter(X[k[0]], Y[k[0]], CUBE_WL[k[1]], c=Q[k], cmap=cmap, vmin=0, vmax=255, s=0.6,
                   linewidths=0, depthshade=False)
        ax.set_xlabel("Along row (px/4)", fontsize=6, labelpad=-6)
        ax.set_ylabel("Across row", fontsize=6, labelpad=-8)
        ax.set_zlabel("Wavelength (nm)", fontsize=6, labelpad=-4)
        ax.set_zlim(500, 800)
        ax.tick_params(labelsize=5, pad=-2)
        ax.set_yticks([])
        ax.set_title(f"{trt}, 24 h (plate 1, row 1)", fontsize=7)
        ax.view_init(elev=18, azim=-60)
        for a in (ax.xaxis, ax.yaxis, ax.zaxis):
            a.set_pane_color((0.04, 0.04, 0.05, 1.0))
            a._axinfo["grid"].update(color=(0.35, 0.35, 0.38, 1.0), linewidth=0.4)
    fig.tight_layout()
    fig.savefig(FIGURES / "figS4_hypercube.png", facecolor="white")
    plt.close(fig)


def trajectories():
    T = pd.read_csv(TABLES / "seedling_plate_changes.csv")
    T = T[(T["set"] == "A")]
    out = []
    for (trt, p), g in T.groupby(["treatment", "plate"]):
        g = g.sort_values("hour")
        pts = [dict(hour=0, fwhm=0.0, f685=0.0, sw=0.0)] + [
            dict(hour=int(r.hour), fwhm=round(r.red_fwhm_nm, 4), f685=round(r.f685_cps, 2),
                 sw=round(r.shortwave_fraction * 1000, 4)) for r in g.itertuples()]
        out.append(dict(treatment=trt, plate=int(p), points=pts))
    (DOCS / "data" / "trajectories.json").write_text(json.dumps(dict(
        axes=dict(fwhm="Change in red-peak width (nm)", f685="Change in 685 nm emission (counts/s)",
                  sw="Change in short-wavelength fraction (x10^-3)"),
        note="Set A; plate means of all segmented seedlings, change from the same plate at hour 0. "
             "Control-4 and flg22-2 excluded (partly upright hour-0 rescans).",
        source="tables/seedling_plate_changes.csv", plates=out), separators=(",", ":")))


if __name__ == "__main__":
    main()
