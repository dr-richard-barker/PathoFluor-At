"""Spectral features of chlorophyll-fluorescence emission spectra.

Shape features are ratios or wavelength positions, so they do not depend on exposure time,
excitation power or plant size. They can be compared across cubes whose camera settings
differ (see metadata/FACTS_PENDING.md and the data-quality section of the manuscript).
"""
import numpy as np
from scipy.signal import savgol_filter

GRID = np.arange(650.0, 800.0 + 1e-9, 2.0)   # common grid for modelling, both sets


def _band_mean(wl, y, lo, hi):
    m = (wl >= lo) & (wl <= hi)
    return y[..., m].mean(axis=-1)


def _integral(wl, y, lo, hi):
    m = (wl >= lo) & (wl <= hi)
    return np.trapezoid(y[..., m], wl[m], axis=-1)


def _peak(wl, y, lo, hi):
    """Peak wavelength in [lo, hi] with parabolic sub-band interpolation (1-D only)."""
    m = np.nonzero((wl >= lo) & (wl <= hi))[0]
    k = m[np.argmax(y[m])]
    if 0 < k < len(y) - 1:
        a, b, c = y[k - 1], y[k], y[k + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if den != 0 else 0.0
        return wl[k] + off * (wl[k + 1] - wl[k - 1]) / 2
    return wl[k]


def _fwhm(wl, y, k_peak):
    half = y[k_peak] / 2
    left = k_peak
    while left > 0 and y[left] > half:
        left -= 1
    right = k_peak
    while right < len(y) - 1 and y[right] > half:
        right += 1
    if left == 0 or right == len(y) - 1:
        return np.nan
    xl = np.interp(half, [y[left], y[left + 1]], [wl[left], wl[left + 1]])
    xr = np.interp(half, [y[right], y[right - 1]], [wl[right], wl[right - 1]])
    return xr - xl


def smooth(y, window=7):
    return savgol_filter(y, window, 2, axis=-1)


def shape_features(wl, y):
    """Scale-invariant features of one dark-subtracted emission spectrum."""
    y = smooth(np.asarray(y, dtype=float))
    total = _integral(wl, y, 650, 800)
    f685 = _band_mean(wl, y, 683, 687)
    f740 = _band_mean(wl, y, 736, 744)
    red = _peak(wl, y, 670, 700)
    kred = int(np.argmin(np.abs(wl - red)))
    m = (wl >= 650) & (wl <= 800)
    return dict(
        f685_f740=f685 / f740 if f740 > 0 else np.nan,
        red_peak_nm=red,
        farred_peak_nm=_peak(wl, y, 720, 760),
        red_fwhm_nm=_fwhm(wl, y, kred),
        centroid_nm=float((wl[m] * y[m]).sum() / y[m].sum()) if y[m].sum() > 0 else np.nan,
        farred_fraction=_integral(wl, y, 710, 800) / total if total > 0 else np.nan,
        # Emission below the chlorophyll band relative to it: the vendor's "broad
        # autofluorescence" (and, for 405 nm excitation, blue-green fluorescence).
        shortwave_fraction=_integral(wl, y, 500, 640) / total if total > 0 else np.nan,
    )


def intensity_features(wl, y, tint_s):
    """Exposure-normalised intensities (counts per second). Only valid when tint is known."""
    y = smooth(np.asarray(y, dtype=float))
    return dict(
        f685_cps=_band_mean(wl, y, 683, 687) / tint_s,
        f740_cps=_band_mean(wl, y, 736, 744) / tint_s,
        total_650_800_cps=_integral(wl, y, 650, 800) / tint_s,
    )


def to_grid(wl, y, grid=GRID, normalise=True):
    """Resample onto the common grid; optionally area-normalise over 650-800 nm."""
    g = np.interp(grid, wl, smooth(np.asarray(y, dtype=float)))
    if normalise:
        s = np.trapezoid(g, grid)
        g = g / s if s > 0 else g * np.nan
    return g
