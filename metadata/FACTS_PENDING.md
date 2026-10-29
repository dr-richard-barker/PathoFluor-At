# Methods facts: resolved and pending

Every methods fact the manuscript states must trace to a row here. **Resolved** rows name their
source. **Pending** rows stay as visible placeholders (`\pending{…}`) in the manuscript until
Richard supplies them. Nothing in this table is inferred from memory.

Sources:
- **[H]** ENVI headers on the 2016 drive (`metadata/cube_manifest.csv`).
- **[N]** 2016 file and folder names (`metadata/roi_manifest.csv`).
- **[V1]** Middleton Spectral Vision report "Arabidopsis Imaging, UW Arabidopsis, msv091416"
  (H. Jones, 14 Sep 2016; analysis of the July set). Held in Richard's Google Drive.
- **[V2]** Middleton Spectral Vision report "Arabidopsis Imaging, October Experiment"
  (H. Jones, PDF dated Jan 2017; analysis of the November set). Held in Richard's Google Drive.
- **[P]** Protocol draft "Hyperspectral & NVDI imaging of pathgen infection"
  (Google Doc, R. Barker et al.; last modified Mar 2019). It describes the *planned* design.
  PDF export in `data/related_drive_2016/`.
- **[RB]** Richard Barker, answers in chat on 2026-10-28 and 2026-10-29 (investigator's statement; not in the 2016 files).
- **[L]** "Pathogen_hyperspectral assay_leaf size.xlsx" (pilot leaf areas). Copy in `data/related_drive_2016/`.

## Resolved

| # | Fact | Value | Source |
|---|---|---|---|
| R1 | Imaging system | MacroPhor™ fluorescence hyperspectral imager (Middleton Spectral Vision), imaging done in the Gilroy Lab, UW-Madison Botany | V1, V2 |
| R2 | Camera | Andor Zyla 5.5 sCMOS, 12-bit low-noise mode; serial VSC-03157 (July), VSC-04393 (Nov) | H |
| R3 | July excitation / emission | 488 nm excitation; 500–800 nm emission | V1 |
| R4 | November excitation / emission | 405 nm excitation; 400–800 nm emission | V2 |
| R5 | Pathogen | *Pseudomonas syringae* (strain and pathovar not stated) | V1, V2, P |
| R6 | July timepoints | Images at 1, 2, 3, 24 and 48 h after infection; `Hour0` scans were taken about 6 h before `Hour1` (11:20–12:26 vs 18:06 on 22 Jul 2016), consistent with a pre-treatment baseline | V1, H |
| R7 | November timepoints | 0, 6, 24 and 48 h after infection | V2, N |
| R8 | July lanes | A = Col-0, B = FLS2-17, C = FLS2-101, D = cml24-2, E = cml24-4 | N (`Results/<treatment>/<genotype>/`) |
| R9 | November lane order | "First 3 plants in each image is the wild type (Col-0), followed by FLS2-17 and FLS2-101", so A/B/C is **taken** as Col-0/FLS2-17/FLS2-101 (positional; confirm) | V2 |
| R10 | Pilot table values | Per-plant rosette size from image pixel counts, days 0–3. In the source sheet, column G = 4 × green/red-reference pixel ratio and column H = the ratio itself; **98.3% of the pilot-table values match column H** (checked in data/related_drive_2016/). With the 4 cm² reference (R18), cm² = column H × 4 | L, R18 |
| R11 | Pilot genotype codes | "GL3.3-1/-2" and "GL3.4-1/-2" = GLR3.3-1/-2 and GLR3.4-1/-2 (the sheet spells both forms) | L |
| R12 | People named in the 2016 records | Sarah Sapiro, Richard Barker, Gilroy Laboratory (V1, V2). Protocol authors: Richard Barker, Cullen Vens, Aditya Singa, Simon Gilroy (P) | V1, V2, P |
| R13 | Hour 0 | Pre-treatment baseline, imaged before bacteria or flg22 were applied | RB; consistent with scan times (H) and V1 |
| R14 | "(inverted)" / "(NI)" | Plate-orientation flag: plate imaged upside down (inverted) or upright (not inverted); exact stage geometry not specified | RB |
| R15 | `Laser50` / `Laser58` | Excitation laser power settings (50% / 58% of maximum output) | RB |
| R16 | Pathogen strain | *P. syringae* pv. tomato DC3000 | RB (the answer also mentioned a possible mutant "if specified"; none is specified in the 2016 files) |
| R17 | flg22 concentration | 1 µM, given as the lab's standard working concentration (range used in the lab 100 nM–1 µM); not recorded with the 2016 data | RB |
| R18 | Pilot reference square | 4 cm² (2.0 × 2.0 cm), so pilot areas in cm² = tabulated value × 4 | RB; label in L |
| R19 | Vendor reports | Not redistributed (they belong to Middleton Spectral Vision); cited, and only derived facts used | RB |
| R20 | Authorship | Sole author: Richard J. Barker (2026-10-29; replaces the earlier "Barker et al." placeholder). Affiliation given as Department of Botany, UW-Madison, where the work was done (R1) | RB |
| R21 | Growth | 7-day seedlings; 0.5× MS/LS basal salts, 0.1% (w/v) sucrose, 0.5 g/L MES pH 5.7, 0.8% Phytagel (chosen by Richard over the protocol draft's "½ LS, 0.3% P") | RB |
| R22 | Inoculum | Pst DC3000 at OD600 0.01 in 10 mM MgCl2, flood inoculation | RB |
| R23 | Mock and flg22 application | Solutions gently decanted onto the plate, submerging the seedlings for about 10 s, then gently poured away | RB (2026-10-29) |
| R24 | Funding | None; the work had no funding support (the grants listed on 2026-10-28 are not acknowledged) | RB (2026-10-29) |

## Pending (Richard to supply)

| # | Question | Notes |
|---|---|---|
| P6 | Meaning of the ROI tags (bright / norm / dark / side …) and the `… USE` selection criteria | **Answer rejected by the data:** it described the tags as acquisition gain/exposure brackets, but ROIs with different tags come from the same cube at a single exposure (e.g. all of Hour0 Pathogen plate 1 at 0.305 s), so the tags annotate the ROI, not the acquisition |
| P8 | What `Chroma.raw` (21 Jul 2016) is | Fluorescence reference slide? |
| P9 | Allele identities and backgrounds | **Answer rejected by the data/literature:** it listed fls2-1 (SALK_141277)/fls2-c, cml24-2 (SALK_073883), cml24-4 (SALK_026046) and glr3.6 lines, but the 2016 files name fls2-17, FLS2-101 and glr3.4 lines; fls2-17 is published as an EMS kinase-domain point mutant from the Gómez-Gómez & Boller screen, and cml24-4 as a TILLING point allele (K124E). Needs the stock records |
| P14 | Growth light, photoperiod and temperature | Not yet supplied |
| P15 | Acknowledgements | Whether to thank anyone named in the 2016 records (R12); author's choice |
