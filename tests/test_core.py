import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.envi import open_cube, parse_header, read_cube  # noqa: E402
from pathofluor.features import shape_features, to_grid  # noqa: E402
from pathofluor.names import parse_cube, parse_roi  # noqa: E402


def write_envi(tmp, L=4, B=6, S=5):
    wl = np.linspace(400, 800, B)
    hdr = (f"ENVI\ninterleave = bil\nsamples = {S}\nlines = {L}\nbands = {B}\ndata type = 12\n"
           f"byte order = 0\nheader offset = 0\ntint = 0.203\nWavelength = {{\n"
           + ",\n".join(f"{w:.4f}" for w in wl) + "\n}\n")
    (tmp / "c.hdr").write_text(hdr)
    data = (np.arange(L * B * S, dtype="<u2")).reshape(L, B, S)
    data.tofile(tmp / "c.raw")
    return data, wl


def test_envi_roundtrip(tmp_path):
    data, wl = write_envi(tmp_path)
    h = parse_header(tmp_path / "c.hdr")
    assert (h["lines"], h["bands"], h["samples"]) == data.shape
    assert np.allclose(h["wavelength"], wl, atol=1e-3)
    _, m = open_cube(tmp_path / "c.hdr")
    _, r = read_cube(tmp_path / "c.hdr")
    assert np.array_equal(m, data) and np.array_equal(r, data)


@pytest.mark.parametrize("stem,rel,expect", [
    ("Hour0 Control1 Row1 (inverted)", "Hour0/Control/x", ("A", 0, "Control", 1, 1, "inverted")),
    ("Hour0 FLG22-2 Row1 (NI)", "Hour0/FLG22/x", ("A", 0, "flg22", 2, 1, "not_inverted")),
    ("Hour2 Conrol3 Row2", "Hour2/Control/x", ("A", 2, "Control", 3, 2, "not_inverted")),
    ("Hr6 P3 R2 Laser58", "Hyper_spectral_work_from_Sarah_Sapiro/Hr6/x", ("B", 6, "Pathogen", 3, 2, None)),
])
def test_cube_names(stem, rel, expect):
    d = parse_cube(stem, rel)
    assert (d["set"], d["hour"], d["treatment"], d["plate"], d["row"], d["orientation"]) == expect


@pytest.mark.parametrize("stem,rel,lane,plant,geno", [
    ("Hr0 P1 A Plant1 (dark)", "Hour0/Pathogen/Results/x", "A", 1, "Col-0"),
    ("Hr2 F1 E Plant3 (bright) - Copy", "Results/FLG22/cml24-4/Hr2/x", "E", 3, "cml24-4"),
    ("H48 C1 B Leaf3", "Hyper_spectral_work_from_Sarah_Sapiro/Hr48/Results/Control/x", "B", 3, None),
])
def test_roi_names(stem, rel, lane, plant, geno):
    d = parse_roi(stem, rel)
    assert (d["lane"], d["plant"], d["genotype"]) == (lane, plant, geno)


def test_unknown_names_are_rejected():
    assert parse_cube("random scan", "Hour0/Control/x") is None
    assert parse_roi("notes", "Hour0/Control/Results/x") is None


def chl_spectrum(wl, fwhm_red=22.0):
    s = fwhm_red / 2.3548
    return 3000 * np.exp(-0.5 * ((wl - 685) / s) ** 2) + 900 * np.exp(-0.5 * ((wl - 738) / 14) ** 2)


def test_shape_features_known_peak():
    wl = np.arange(400, 810, 1.23)
    f = shape_features(wl, chl_spectrum(wl))
    assert abs(f["red_peak_nm"] - 685) < 0.5
    assert abs(f["red_fwhm_nm"] - 22) < 1.5   # far-red band widens the measured FWHM slightly


def test_shape_features_are_exposure_invariant():
    wl = np.arange(400, 810, 1.23)
    y = chl_spectrum(wl)
    a, b = shape_features(wl, y), shape_features(wl, 1.5 * y)
    for k in a:
        assert a[k] == pytest.approx(b[k], rel=1e-9, abs=1e-12)
    assert np.allclose(to_grid(wl, y), to_grid(wl, 1.5 * y))
