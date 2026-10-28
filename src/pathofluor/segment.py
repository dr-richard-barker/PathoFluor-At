"""Seedling segmentation on the harvested 685 nm image, and per-seedling spectra.

A seedling is two cotyledons plus a hypocotyl, often separate connected components, so
components are grouped after a dilation large enough to bridge one seedling's parts but not
neighbouring seedlings (about 100 px apart along the scan line in these plates).
"""
import numpy as np
from scipy import ndimage

from .features import intensity_features, shape_features

SAT = 4095


def load(npz_path):
    z = np.load(npz_path)
    return {k: z[k] for k in z.files}


def seedlings(h, thresh_sigma=10.0, min_px=40, group_px=12, frag_frac=0.25, frag_dist=60,
              min_seedling_px=300):
    """Return (labels image, list of per-seedling dicts) for one harvested cube.

    Components are grouped in 2-D after a group_px dilation (bridges a seedling's cotyledons
    and hypocotyl but not its neighbours). Groups smaller than frag_frac of the cube's median
    group, lying within frag_dist px of a larger group, are fragments and are absorbed into
    it; remaining groups under min_seedling_px are dropped as debris.
    """
    img = h["img685"].astype(np.float32) - float(h["bg_median685"])
    fg = img > thresh_sigma * float(h["bg_sigma685"])
    fg = ndimage.binary_opening(fg, iterations=1)
    lab, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, lab, index=np.arange(1, n + 1))
    keep = np.isin(lab, 1 + np.nonzero(sizes >= min_px)[0])
    grouped, ng = ndimage.label(ndimage.binary_dilation(keep, iterations=group_px))
    lab = np.where(keep, grouped, 0)
    if ng:
        gid = np.arange(1, ng + 1)
        gsz = np.bincount(lab.ravel(), minlength=ng + 1)[1:]
        cen = np.array(ndimage.center_of_mass(lab > 0, lab, gid))
        big = gsz >= frag_frac * np.median(gsz[gsz > 0]) if (gsz > 0).any() else gsz > 0
        remap = np.arange(ng + 1)
        for i in np.nonzero(~big & (gsz > 0))[0]:
            if big.any():
                d = np.hypot(*(cen[big] - cen[i]).T)
                j = np.argmin(d)
                if d[j] <= frag_dist:
                    remap[i + 1] = gid[big][j]
        lab = remap[lab]
        gsz = np.bincount(lab.ravel(), minlength=ng + 1)
        lab[np.isin(lab, np.nonzero((gsz < min_seedling_px) & (np.arange(ng + 1) > 0))[0])] = 0

    # Map harvested pixels (y, x) to seedling ids.
    py, px = h["y"].astype(int), h["x"].astype(int)
    pid = lab[py, px]
    dark = h["dark"][np.isin(h["wl_all"], h["wl"])] if h["dark"].shape[0] != h["wl"].shape[0] else h["dark"]
    wl = h["wl"]
    out = []
    for s in range(1, ng + 1):
        sel = pid == s
        if not sel.any():
            continue
        raw = h["spectra"][sel].astype(np.float32)
        sat = h["pixmax"][sel] >= SAT
        spec = raw - dark
        unsat = spec[~sat] if (~sat).sum() >= 10 else spec
        mean_all = spec.mean(axis=0)
        mean_unsat = unsat.mean(axis=0)
        # Per-pixel shape metrics for spatial heterogeneity.
        b685 = (wl >= 683) & (wl <= 687)
        b740 = (wl >= 736) & (wl <= 744)
        bsw = (wl >= 500) & (wl <= 640)
        bch = (wl >= 650) & (wl <= 800)
        f685 = spec[:, b685].mean(1)
        f740 = np.clip(spec[:, b740].mean(1), 1, None)
        ratio = f685 / f740
        sw = spec[:, bsw].sum(1) / np.clip(spec[:, bch].sum(1), 1, None)
        ys, xs = py[sel], px[sel]
        out.append(dict(
            seedling=s, n_px=int(sel.sum()), n_sat_px=int(sat.sum()),
            line_c=float(ys.mean()), sample_c=float(xs.mean()),
            line_min=int(ys.min()), line_max=int(ys.max()),
            ratio_px_sd=float(ratio.std()), ratio_px_p10=float(np.percentile(ratio, 10)),
            shortwave_px_p90=float(np.percentile(sw, 90)),
            mean_spectrum=mean_unsat, mean_spectrum_all=mean_all,
        ))
    return lab, out


def seedling_features(wl, d, tint_s):
    f = shape_features(wl, d["mean_spectrum"])
    f.update(intensity_features(wl, d["mean_spectrum"], tint_s))
    return f
