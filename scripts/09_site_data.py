"""Export docs/data/spectra.json for the Pages spectrum explorer, and copy figures and PDFs
into docs/. Values are means of the 2016 hand-ROI area-normalised spectra (set A) per
genotype x treatment x hour; the change-from-hour-0 view is computed in the page.
"""
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import FIGURES, REPO, RESULTS  # noqa: E402

DOCS = REPO / "docs"


def main():
    F = pd.read_csv(RESULTS / "roi_features.csv.gz")
    F = F[F["set"] == "A"]
    grid = [c for c in F.columns if c.startswith("n") and c[1:].isdigit()]
    out = {"wavelength_nm": [float(c[1:]) for c in grid], "units": "area-normalised emission (per nm, x1000)",
           "source": "results/roi_features.csv.gz (set A, 2016 hand-drawn ROIs)", "series": []}
    for (g, t, h), d in F.groupby(["genotype", "treatment", "hour"]):
        out["series"].append(dict(genotype=g, treatment=t, hour=int(h), n=len(d),
                                  n_plates=int(d.plate.nunique()),
                                  y=[round(v * 1000, 4) for v in d[grid].mean().values]))
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "data" / "spectra.json").write_text(json.dumps(out, separators=(",", ":")))
    export_field_tables()
    (DOCS / "figures").mkdir(exist_ok=True)
    for p in FIGURES.glob("*.png"):
        shutil.copy2(p, DOCS / "figures" / p.name)
    for src, dst in ((REPO / "manuscript" / "PathoFluor-At_draft.pdf", "PathoFluor-At_draft.pdf"),
                     (REPO / "slides" / "PathoFluor-At_slides.pdf", "PathoFluor-At_slides.pdf")):
        if src.exists():
            shutil.copy2(src, DOCS / dst)
    render_page()
    print(f"{len(out['series'])} series; figures and PDFs copied; docs/index.html rendered")


def export_field_tables():
    """docs/data/alarm.json and bands.json from scripts/11_field_analyses.py's tables."""
    from pathofluor.config import TABLES
    A = pd.read_csv(TABLES / "alarm_replay.csv")
    rows = [dict(treatment=r.treatment, plate=int(r.plate), hour=int(r.hour),
                 p=None if pd.isna(r.p_infected) else float(r.p_infected),
                 n=int(r.n_rois), scoring=r.scoring) for r in A.itertuples()]
    (DOCS / "data" / "alarm.json").write_text(json.dumps(dict(
        threshold=0.5, source="tables/alarm_replay.csv (scripts/11_field_analyses.py)", cells=rows),
        separators=(",", ":")))
    B = pd.read_csv(TABLES / "band_sets_auc.csv")
    (DOCS / "data" / "bands.json").write_text(json.dumps(dict(
        source="tables/band_sets_auc.csv (scripts/11_field_analyses.py)",
        rows=[dict(hour=int(r.hour), contrast=r.contrast, band_set=r.band_set, bands_nm=r.bands_nm,
                   auc=round(float(r.auc_plate), 3), p=round(float(r.perm_p_plate), 3)) for r in B.itertuples()]),
        separators=(",", ":")))


def render_page():
    """Fill docs/index.template.html with the numbers.tex macros and the figure captions."""
    import html
    import re
    vals = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", (REPO / "manuscript" / "numbers.tex").read_text()))
    vals = {k: v.replace("\\times10^{", "×10^").replace("{", "").replace("}", "") for k, v in vals.items()}
    caps = dict(re.findall(r"^\*\*(\w+)\*\* — (.*)$", (FIGURES / "CAPTIONS.md").read_text(), re.M))
    for k, v in caps.items():
        vals[f"cap_{k}"] = html.escape(v)
    t = (DOCS / "index.template.html").read_text()
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", t)) - set(vals))
    if missing:
        raise SystemExit(f"index template needs undefined values: {missing}")
    (DOCS / "index.html").write_text(re.sub(r"\{\{(\w+)\}\}", lambda m: vals[m.group(1)], t))


if __name__ == "__main__":
    main()
