"""Write manuscript/numbers.tex: every number quoted in the manuscript and slides, as a LaTeX
macro computed from the committed tables (ABAI L007: no hard-coded results).
A missing selector raises, so a stale or renamed table cannot silently drop a number.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, REPO, RESULTS, TABLES  # noqa: E402

OUT = {}


def put(name, value, fmt="{:.2f}"):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        raise SystemExit(f"numbers: {name} is missing")
    OUT[name] = fmt.format(value) if not isinstance(value, str) else value


def one(df, **sel):
    d = df
    for k, v in sel.items():
        d = d[d[k] == v]
    if len(d) != 1:
        raise SystemExit(f"numbers: selector {sel} matched {len(d)} rows")
    return d.iloc[0]


def pfmt(p):
    return f"{p:.3f}" if p >= 0.001 else f"{p:.1e}".replace("e-0", "\\times10^{-") + "}"


def main():
    inv = pd.read_csv(META / "file_inventory.csv")
    cm = pd.read_csv(META / "cube_manifest.csv")
    rm = pd.read_csv(META / "roi_manifest.csv")
    put("nFiles", len(inv), "{:,}")
    put("nCubes", int(cm["set"].isin(["A", "B"]).sum()), "{:,}")
    put("nCubesA", int(((cm["set"] == "A") & (cm.role == "sample")).sum()), "{:,}")
    put("nCubesB", int(((cm["set"] == "B") & (cm.role == "sample")).sum()), "{:,}")
    put("nRoiFiles", int(rm["set"].isin(["A", "B"]).sum()), "{:,}")
    put("nRoiUnique", int(rm[rm["set"].isin(["A", "B"])].spectrum_id.nunique()), "{:,}")
    put("nRoiA", int(rm[rm["set"] == "A"].spectrum_id.nunique()), "{:,}")
    put("nRoiB", int(rm[rm["set"] == "B"].spectrum_id.nunique()), "{:,}")
    put("rawGB", inv[inv.category.isin(["set_A", "set_B"])].bytes.sum() / 1e9, "{:.0f}")

    e = pd.read_csv(TABLES / "fig1_exposure_artefact.csv").set_index("hour")
    put("rawFzero", e.loc[0, "raw"], "{:,.0f}")
    put("rawFone", e.loc[1, "raw"], "{:,.0f}")
    put("rawDropPct", 100 * (1 - e.loc[1, "raw"] / e.loc[0, "raw"]), "{:.0f}")
    put("cpsDiffPct", 100 * abs(e.loc[[1, 2, 3], "cps"].mean() / e.loc[0, "cps"] - 1), "{:.0f}")

    qc = [json.loads(p.read_text()) for p in (RESULTS / "cube_qc").glob("A_H00_*.json")]
    if qc:
        sat = np.array([q["n_saturated_fg_pixels"] for q in qc]) / np.array([q["n_fg_pixels"] for q in qc])
        put("satHzeroMaxPct", 100 * sat.max(), "{:.0f}")
        put("satHzeroMedPct", 100 * np.median(sat), "{:.1f}")

    B = pd.read_csv(TABLES / "stats_contrasts_baseline_adjusted.csv")
    for hr, tag in ((1, "One"), (2, "Two")):
        r = one(B, set="A", hour=hr, feature="red_fwhm_nm", contrast="Pathogen vs Control (Col-0)")
        put(f"pathFwhm{tag}SD", r.effect_sd)
        put(f"pathFwhm{tag}nm", r.effect_raw)
        put(f"pathFwhm{tag}q", pfmt(r.q), "{}")
    r = one(B, set="A", hour=2, feature="shortwave_fraction", contrast="Pathogen vs Control (Col-0)")
    put("pathSwTwoSD", r.effect_sd)
    put("pathSwTwoq", pfmt(r.q), "{}")
    put("nBaselineTests", int((B["set"] == "A").sum()), "{:,}")
    put("nBaselineSig", int(((B["set"] == "A") & (B.q < 0.05)).sum()), "{:d}")

    C = pd.read_csv(TABLES / "stats_contrasts.csv")
    r = one(C, set="A", hour=0, feature="red_fwhm_nm", contrast="flg22 vs Control (Col-0)")
    put("hzeroFlgFwhmSD", r.effect_sd)
    put("hzeroFlgFwhmq", pfmt(r.q), "{}")
    r = one(C, set="B", hour=6, feature="f685_f740", contrast="flg22 x fls2-17")
    put("setBinterSD", r.effect_sd)
    put("setBinterq", pfmt(r.q), "{}")
    put("setBinterN", int(((C["set"] == "B") & (C.hour == 6) & (C.q < 0.05)).sum()), "{:d}")

    A = pd.read_csv(TABLES / "model_auc.csv")
    sel = dict(genotypes="Col-0", model="logistic", features="spectrum")
    for hr, tag in ((1, "One"), (2, "Two"), (24, "TwentyFour")):
        r = one(A, variant="baseline-relative", hour=hr, contrast="Pathogen vs Control", **sel)
        put(f"aucPath{tag}", r.auc_plate)
        put(f"pPath{tag}", r.perm_p_plate, "{:.3f}")
    r = one(A, variant="absolute", hour=0, contrast="flg22 vs Control", **sel)
    put("aucPlaceboFlg", r.auc_plate)
    put("pPlaceboFlg", r.perm_p_plate, "{:.3f}")
    r = one(A, variant="absolute", hour=0, contrast="Pathogen vs Control", **sel)
    put("aucPlaceboPath", r.auc_plate)
    fl = A[(A.variant == "baseline-relative") & (A.contrast == "flg22 vs Control") & (A.hour.isin([1, 2, 3]))
           & (A.genotypes == "Col-0") & (A.model == "logistic") & (A.features == "spectrum")]
    put("aucFlgEarlyMin", fl.auc_plate.min())
    put("aucFlgEarlyMax", fl.auc_plate.max())
    put("pFlgEarlyMin", fl.perm_p_plate.min(), "{:.2f}")
    put("nPermFlgBase", int(fl.n_perm.iloc[0]), "{:d}")

    S = pd.read_csv(TABLES / "model_specificity.csv")
    s = S[(S.variant == "baseline-relative") & (S.contrast == "flg22 vs Control") & (S.hour.isin([1, 2, 3]))]
    piv = s.groupby("genotype").delta_p.mean()
    put("specFlgColO", piv["Col-0"])
    put("specFlgFlsSeventeen", piv["fls2-17"])
    put("specFlgFlsOneOhOne", piv["fls2-101"])

    lines = ["% Generated by scripts/07_numbers.py from tables/ and metadata/. Do not edit by hand."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in OUT.items()]
    (REPO / "manuscript" / "numbers.tex").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
