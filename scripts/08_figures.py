"""Manuscript figures (PNG + PDF) with captions in figures/CAPTIONS.md.

Palette: reference categorical slots 1-3 (treatments) and 1-5 (genotypes), validated with the
dataviz validator (light surface; all-pairs for 3, adjacent for 5). Slots with contrast
below 3:1 get relief: direct labels plus distinct markers, and every panel's numbers are in
tables/.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import FIGURES, META, RESULTS, TABLES  # noqa: E402

SURFACE = "#fcfcfb"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
TRT = {"Control": "#2a78d6", "flg22": "#eb6834", "Pathogen": "#1baf7a"}
TRT_MARK = {"Control": "o", "flg22": "s", "Pathogen": "^"}
GENO = {"Col-0": "#2a78d6", "fls2-17": "#eb6834", "fls2-101": "#1baf7a", "cml24-2": "#eda100", "cml24-4": "#e87ba4"}
GENO_MARK = {"Col-0": "o", "fls2-17": "s", "fls2-101": "D", "cml24-2": "^", "cml24-4": "v"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "xtick.labelsize": 8,
    "ytick.labelsize": 8, "legend.fontsize": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.6, "lines.markersize": 5.5, "legend.frameon": False,
})
CAPTIONS = {}


def save(fig, name, caption):
    FIGURES.mkdir(exist_ok=True)
    place_labels(fig)
    fig.savefig(FIGURES / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    CAPTIONS[name] = caption


_PENDING_LABELS = {}


def label_end(ax, x, y, text, color):
    """Queue a direct label at a line's end; place_labels() spaces them so none overlap."""
    _PENDING_LABELS.setdefault(ax, []).append((x, y, text))


def place_labels(fig, min_gap_pt=9):
    fig.canvas.draw()
    for ax, items in _PENDING_LABELS.items():
        to_disp = ax.transData.transform
        pts = sorted(((*to_disp((x, y)), x, y, t) for x, y, t in items), key=lambda r: r[1])
        gap = min_gap_pt * fig.dpi / 72
        ys = [p[1] for p in pts]
        for i in range(1, len(ys)):
            ys[i] = max(ys[i], ys[i - 1] + gap)
        for (dx, dy, x, y, t), ny in zip(pts, ys):
            ax.annotate(t, (x, y), xytext=(4, (ny - dy) * 72 / fig.dpi), textcoords="offset points",
                        va="center", fontsize=7.5, color=INK2)
    _PENDING_LABELS.clear()


def fig_exposure(F, cm):
    """Raw vs exposure-corrected peak intensity of Control hand ROIs, by timepoint."""
    R = pd.read_parquet(RESULTS / "roi_spectra_A.parquet")
    wcols = [c for c in R.columns if c.startswith("I_")]
    wl = np.array([float(c[2:]) for c in wcols])
    m = (wl >= 680) & (wl <= 690)
    R = R.assign(peak=R[wcols].values[:, m].mean(1))
    t = cm[(cm["set"] == "A") & (cm.role == "sample")].groupby(["hour", "treatment", "plate"]).tint_s
    tint = t.agg(lambda x: x.mean()).rename("tint_mean")
    tint_unique = t.nunique().rename("n_tints")
    R = R.join(tint, on=["hour", "treatment", "plate"]).join(tint_unique, on=["hour", "treatment", "plate"])
    R["peak_cps"] = R.peak / R.tint_mean
    d = R[R.treatment == "Control"]
    s = d.groupby("hour").agg(raw=("peak", "median"), cps=("peak_cps", "median"), tint=("tint_mean", "mean"),
                              n=("peak", "size"), mixed=("n_tints", "max")).reset_index()
    s.to_csv(TABLES / "fig1_exposure_artefact.csv", index=False)
    hours = s.hour.astype(int).astype(str).values
    x = np.arange(len(s))
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.4))
    ax[0].bar(x, s.tint, color="#86b6ef", width=0.6)
    ax[0].set_xticks(x, hours)
    ax[0].set_xlabel("Timepoint (h)")
    ax[0].set_ylabel("Exposure time (s)")
    ax[0].set_title("a  Camera exposure")
    ax[1].plot(x, s.raw, marker="o", color=INK2)
    ax[1].set_xticks(x, hours)
    ax[1].set_xlabel("Timepoint (h)")
    ax[1].set_ylabel("Median F$_{685}$ (counts)")
    ax[1].set_title("b  As plotted in 2016")
    ax[2].plot(x, s.cps / 1000, marker="o", color=TRT["Control"])
    ax[2].set_xticks(x, hours)
    ax[2].set_xlabel("Timepoint (h)")
    ax[2].set_ylabel("Median F$_{685}$ (10$^3$ counts s$^{-1}$)")
    ax[2].set_title("c  Exposure-corrected")
    for a in ax:
        a.set_ylim(bottom=0)
    fig.tight_layout()
    save(fig, "fig1_exposure_artefact",
         "Exposure time changed between timepoints (a; plate-mean exposure of the Control plates, so hour 0 "
         "mixes 0.305 s scans with the 0.203 s rescan of Control-4). The 2016 summary graphs plotted raw intensity (b), so "
         "part of their apparent fall after hour 0 is a camera setting. Dividing by each cube's exposure (c) "
         "removes that step. Control plates only, set A, median 683-687 nm emission of the 2016 hand-drawn "
         "ROIs. Hour 24 mixed exposures within plates (0.222-0.268 s), so its plate-mean exposure is used. "
         "Data: results/roi_spectra_A.parquet, metadata/cube_manifest.csv; table: tables/fig1_exposure_artefact.csv.")


def baseline_relative(F, feats):
    pm = F.groupby(["set", "hour", "treatment", "plate", "genotype"])[feats].mean().reset_index()
    base = pm[pm.hour == 0].drop(columns="hour").set_index(["set", "treatment", "plate", "genotype"])
    d = pm[pm.hour > 0].merge(base.add_suffix("_h0").reset_index(), on=["set", "treatment", "plate", "genotype"])
    for f in feats:
        d[f] = d[f] - d[f + "_h0"]
    ni = (d["set"] == "A") & (((d.treatment == "Control") & (d.plate == 4)) |
                             ((d.treatment == "flg22") & (d.plate == 2)))
    return d[~ni]


def fig_spectra(F):
    """Baseline-relative change in the area-normalised spectrum, treated minus Control, Col-0."""
    grid = [c for c in F.columns if c.startswith("n") and c[1:].isdigit()]
    wl = np.array([float(c[1:]) for c in grid])
    d = baseline_relative(F[(F["set"] == "A") & (F.genotype == "Col-0")], grid)
    hours = [1, 2, 3, 24, 48]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
    rows = []
    cmap = plt.get_cmap("Blues")
    for a, trt in zip(ax, ("Pathogen", "flg22")):
        for i, hr in enumerate(hours):
            t = d[(d.hour == hr) & (d.treatment == trt)][grid].mean().values
            c = d[(d.hour == hr) & (d.treatment == "Control")][grid].mean().values
            if np.isnan(t).all():
                continue
            diff = (t - c) * 1000
            col = cmap(0.35 + 0.65 * i / (len(hours) - 1))
            a.plot(wl, diff, color=col, label=f"{hr} h")
            rows += [dict(treatment=trt, hour=hr, wl=w, diff_x1000=v) for w, v in zip(wl, diff)]
        a.axhline(0, color=INK2, lw=0.8)
        a.set_xlabel("Wavelength (nm)")
        a.set_title(f"{'a' if trt == 'Pathogen' else 'b'}  {trt} minus Control")
        a.legend(title="Time after treatment", ncol=1, loc="lower right", title_fontsize=7.5)
    ax[0].set_ylabel("Change in normalised emission\n(×10$^{-3}$ nm$^{-1}$, from hour 0)")
    fig.tight_layout()
    pd.DataFrame(rows).to_csv(TABLES / "fig2_spectral_change.csv", index=False)
    save(fig, "fig2_spectral_change",
         "Treatment-induced change in emission-spectrum shape, Col-0, set A. Each spectrum is area-normalised "
         "over 650-800 nm (so exposure and seedling size cancel), averaged per plate, and expressed relative to "
         "the same plate at hour 0. Curves show treated minus Control at each time after treatment. No hand "
         "ROIs exist for Pathogen at 48 h. Data: results/roi_features.csv.gz; "
         "table: tables/fig2_spectral_change.csv.")


def fig_timecourse(F):
    feats = {"red_fwhm_nm": "Red-peak FWHM (nm)", "shortwave_fraction": "500-640 nm / 650-800 nm",
             "f685_f740": "F$_{685}$/F$_{740}$"}
    d = baseline_relative(F[(F["set"] == "A") & (F.genotype == "Col-0")], list(feats))
    hours = [1, 2, 3, 24, 48]
    xpos = {h: i for i, h in enumerate(hours)}
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6))
    rows = []
    for a, (f, lab), letter in zip(ax, feats.items(), "abc"):
        for trt in ("Control", "flg22", "Pathogen"):
            g = d[d.treatment == trt].groupby("hour")[f].agg(["mean", "sem", "size"]).reset_index()
            x = [xpos[h] for h in g.hour]
            a.errorbar(x, g["mean"], yerr=g["sem"], color=TRT[trt], marker=TRT_MARK[trt], capsize=2,
                       label=trt, lw=1.6, elinewidth=0.9)
            if len(g):
                label_end(a, x[-1], g["mean"].iloc[-1], trt, TRT[trt])
            rows += [dict(feature=f, treatment=trt, hour=h, mean=m_, sem=s_, n_plates=n_)
                     for h, m_, s_, n_ in zip(g.hour, g["mean"], g["sem"], g["size"])]
        a.axhline(0, color=INK2, lw=0.8)
        a.set_xticks(range(len(hours)), [str(h) for h in hours])
        a.set_xlim(-0.4, len(hours) - 0.2)
        a.set_xlabel("Hours after treatment")
        a.set_title(f"{letter}  Δ {lab}", fontsize=8.5)
    ax[0].legend(loc="upper left")
    fig.tight_layout()
    pd.DataFrame(rows).to_csv(TABLES / "fig3_timecourse.csv", index=False)
    save(fig, "fig3_timecourse",
         "Change from hour 0 in three emission-shape features, Col-0, set A. Points are means over plates "
         "(n = 3-4 plates per treatment; the plate is the treated unit) ± s.e.m.; each plate value is the mean "
         "of its Col-0 hand-ROI spectra minus the same plate's hour-0 mean. Time axis is categorical (1, 2, 3, "
         "24, 48 h). Plates Control-4 and flg22-2 are excluded because their hour-0 scans were partly upright "
         "rescans. Data: results/roi_features.csv.gz; table: tables/fig3_timecourse.csv. Statistics: "
         "tables/stats_contrasts_baseline_adjusted.csv.")


def fig_auc():
    A = pd.read_csv(TABLES / "model_auc.csv")
    A = A[(A.genotypes == "Col-0") & (A.model == "logistic") & (A.features == "spectrum")]
    hours = [0, 1, 2, 3, 24, 48]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.6), sharey=True)
    for a, variant, letter in zip(ax, ("absolute", "baseline-relative"), "ab"):
        for trt in ("Pathogen", "flg22"):
            g = A[(A.variant == variant) & (A.contrast == f"{trt} vs Control")].set_index("hour").reindex(hours)
            x = np.arange(len(hours))
            a.plot(x, g.auc_plate, color=TRT[trt], marker=TRT_MARK[trt], label=trt)
            for xi, (auc, p) in enumerate(zip(g.auc_plate, g.perm_p_plate)):
                if np.isfinite(p) and p <= 0.05:
                    a.annotate("*", (xi, auc), xytext=(0, 3), textcoords="offset points", ha="center",
                               fontsize=10, color=INK)
        a.axhline(0.5, color=INK2, lw=0.8, ls="--")
        a.set_xticks(np.arange(len(hours)), [str(h) for h in hours])
        a.set_ylim(-0.05, 1.1)
        a.set_xlabel("Hours after treatment (0 = before)")
        a.set_title(f"{letter}  {'Absolute spectra' if variant == 'absolute' else 'Change from hour 0'}")
    ax[0].set_ylabel("Plate-level AUC (leave-plate-out)")
    ax[0].legend(loc="lower left")
    fig.tight_layout()
    A.to_csv(TABLES / "fig4_auc.csv", index=False)
    save(fig, "fig4_auc",
         "Can a plate's treatment be told from its seedlings' emission spectra? Logistic regression on the "
         "area-normalised 650-800 nm spectrum of Col-0 hand ROIs, evaluated by leave-one-plate-out "
         "cross-validation. AUC is computed on plate means (8 plates; 6 for the change-from-hour-0 variant). "
         "* exact plate-label permutation p ≤ 0.05. Hour 0 is before treatment: the high hour-0 AUC in (a) "
         "shows that plates differ before treatment, so only (b) is evidence of a treatment effect. "
         "Data: tables/model_auc.csv.")


def fig_specificity():
    S = pd.read_csv(TABLES / "model_specificity.csv")
    S = S[S.variant == "baseline-relative"]
    hours = [1, 2, 3, 24, 48]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.6), sharey=True)
    for a, trt, letter in zip(ax, ("flg22", "Pathogen"), "ab"):
        for g in GENO:
            d = S[(S.contrast == f"{trt} vs Control") & (S.genotype == g)].set_index("hour").reindex(hours)
            x = np.arange(len(hours))
            a.plot(x, d.delta_p, color=GENO[g], marker=GENO_MARK[g], label=g)
        a.axhline(0, color=INK2, lw=0.8)
        a.set_xticks(np.arange(len(hours)), [str(h) for h in hours])
        a.set_xlabel("Hours after treatment")
        a.set_title(f"{letter}  {trt} signature (Col-0-trained)")
    ax[0].set_ylabel("Δ mean P(treated)\ntreated − Control plates")
    ax[1].legend(loc="upper right", ncol=1)
    fig.tight_layout()
    save(fig, "fig5_specificity",
         "Is the signature genotype-specific? A logistic model trained on Col-0 shape features (change from "
         "hour 0) is applied to every genotype on the same plates. Values are the mean predicted probability "
         "of 'treated' on treated plates minus that on Control plates (Col-0: out-of-fold). An FLS2-dependent "
         "flg22 signature would vanish in fls2-17 and fls2-101; it does not, so the set-A flg22 signal is a "
         "plate-level effect. Data: tables/model_specificity.csv.")


def fig_pilot():
    P = pd.read_csv(RESULTS / "pilot_leaf_area.csv")
    P["genotype"] = P.genotype.str.replace("GL3.", "glr3.", regex=False).str.replace("GLR3.", "glr3.", regex=False) \
        .str.replace("FLS2", "fls2", regex=False)
    genos = sorted(P.genotype.unique(), key=lambda g: (g != "Col-0", g))
    fig, axes = plt.subplots(2, 4, figsize=(7.2, 3.8), sharex=True, sharey=True)
    rows = []
    for a, g in zip(axes.flat, genos):
        for trt in ("Control", "flg22", "Pathogen"):
            d = (P[(P.genotype == g) & (P.treatment == trt)].assign(cm2=lambda x: 4 * x.leaf_area_cm2_as_tabulated)
                 .groupby("day").cm2.agg(["mean", "sem", "size"]))
            if d.empty:
                continue
            a.errorbar(d.index, d["mean"], yerr=d["sem"], color=TRT[trt], marker=TRT_MARK[trt], capsize=1.5,
                       lw=1.4, ms=4, elinewidth=0.8, label=trt)
            rows += [dict(genotype=g, treatment=trt, day=k, mean=m, sem=se, n=n) for k, m, se, n in
                     zip(d.index, d["mean"], d["sem"], d["size"])]
        a.set_title(g, fontsize=8.5, style="italic" if g != "Col-0" else "normal")
        a.set_xticks([0, 1, 2, 3])
    for a in axes[-1]:
        a.set_xlabel("Day")
    for a in axes[:, 0]:
        a.set_ylabel("Leaf area (cm$^2$)")
    axes.flat[0].legend(fontsize=6.5, loc="upper left")
    fig.tight_layout()
    pd.DataFrame(rows).to_csv(TABLES / "figS1_pilot_leaf_area.csv", index=False)
    save(fig, "figS1_pilot_leaf_area",
         "Pilot experiment (February-March 2016): rosette leaf area per plant from images, days 0-3 after "
         "treatment, mean ± s.e.m. of the five values tabulated per genotype x treatment x day, "
         "converted to cm²: the 2016 tables give green-pixel area divided by the area of a 4 cm² red reference "
         "square, so cm² = tabulated value × 4 (FACTS R10, R18; source sheet in data/related_drive_2016/). Genotype "
         "codes GL3.3/GL3.4 in the 2016 files denote glr3.3/glr3.4 alleles (FACTS R11). Data: "
         "data/original_2016/Plant hyperspectral assay/*_hyperspectral_Patho.csv; table: "
         "tables/figS1_pilot_leaf_area.csv.")


def fig_cubes():
    """Seedling-level (cube-derived) results; skipped until 05b/05c outputs exist."""
    need = [RESULTS / "mcr_components.csv", TABLES / "seedling_plate_changes.csv"]
    if not all(p.exists() for p in need):
        print("fig6 skipped: run 05b and 05c first")
        return
    comp = pd.read_csv(RESULTS / "mcr_components.csv")
    d = pd.read_csv(TABLES / "seedling_plate_changes.csv")
    fig, ax = plt.subplots(1, 4, figsize=(7.4, 2.5))
    cols = [c for c in comp.columns if c.startswith("comp")]
    for c, colr in zip(cols, ("#2a78d6", "#eb6834", "#1baf7a")):
        ax[0].plot(comp.wl, comp[c] * 1000, color=colr, label=c.replace("comp", "C"))
    ax[0].set_xlabel("Wavelength (nm)")
    ax[0].set_ylabel("Component (×10$^{-3}$ nm$^{-1}$)")
    ax[0].set_title("a  MCR components", fontsize=8.5)
    ax[0].legend(fontsize=6.5)
    rows = []
    panels = ((1, "A", 0, "shortwave_fraction", "b  Set A: 500–640 / 650–800 nm"),
              (2, "A", 0, "f685_cps", "c  Set A: F$_{685}$ (s$^{-1}$)"),
              (3, "B", 58, "shortwave_fraction", "d  Set B: 500–640 / 650–800 nm"))
    for i, s_, las, f, title in panels:
        a = ax[i]
        g = d[(d["set"] == s_) & (d.laser.fillna(0).astype(int) == las)]
        hours = sorted(g.hour.unique())
        for trt in ("Control", "flg22", "Pathogen"):
            m = g[g.treatment == trt].groupby("hour")[f].agg(["mean", "sem", "size"]).reindex(hours)
            a.errorbar(range(len(hours)), m["mean"], yerr=m["sem"], color=TRT[trt], marker=TRT_MARK[trt],
                       capsize=2, lw=1.4, ms=4, elinewidth=0.8, label=trt)
            rows += [dict(set=s_, laser=las, feature=f, treatment=trt, hour=h, mean=v, sem=e, n_plates=n)
                     for h, v, e, n in zip(hours, m["mean"], m["sem"], m["size"])]
        a.axhline(0, color=INK2, lw=0.8)
        a.set_xticks(range(len(hours)), [f"{h:g}" for h in hours])
        a.set_xlabel("Hours after treatment")
        a.set_title(title, fontsize=7.5)
    ax[1].legend(fontsize=6.5, loc="upper left")
    fig.tight_layout()
    pd.DataFrame(rows).to_csv(TABLES / "fig6_seedling_level.csv", index=False)
    save(fig, "fig6_seedling_level",
         "Seedling-level analysis of the raw cubes. (a) Spectra of the three MCR-ALS components fitted to "
         "pixels from every set-A cube (results/mcr_components.csv). (b, c) Set A, all genotypes pooled per "
         "plate, change from the same plate at hour 0: short-wavelength fraction and exposure-corrected 685 nm "
         "emission; unlike the hand ROIs, these include Pathogen plates at 48 h. (d) Set B (405 nm excitation), "
         "2-3 plates per treatment, Laser58 scans. Points are plate means ± s.e.m. Data: "
         "tables/seedling_plate_changes.csv; statistics: tables/seedling_stats.csv; table: "
         "tables/fig6_seedling_level.csv.")


def main():
    F = pd.read_csv(RESULTS / "roi_features.csv.gz")
    cm = pd.read_csv(META / "cube_manifest.csv")
    TABLES.mkdir(exist_ok=True)
    fig_exposure(F, cm)
    fig_spectra(F)
    fig_timecourse(F)
    fig_auc()
    fig_specificity()
    fig_pilot()
    fig_cubes()
    lines = ["# Figure captions\n", "Each caption says what the figure shows and where its data come from.\n"]
    for k, v in CAPTIONS.items():
        lines.append(f"**{k}** — {v}\n")
    (FIGURES / "CAPTIONS.md").write_text("\n".join(lines))
    print("\n".join(CAPTIONS))


if __name__ == "__main__":
    main()
