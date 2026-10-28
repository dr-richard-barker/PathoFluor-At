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
- **[L]** "Pathogen_hyperspectral assay_leaf size.xlsx" (pilot leaf areas). Richard's Google Drive.

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
| R10 | Pilot table values | Per-plant rosette leaf area (cm²) from image pixel counts against a red reference square labelled "4 cm^2"; days 0–3. The sheet has two "leaf area cm^2" columns differing by exactly 4×; the summary tables use the smaller. **Unresolved which is correct.** | L |
| R11 | Pilot genotype codes | "GL3.3-1/-2" and "GL3.4-1/-2" = GLR3.3-1/-2 and GLR3.4-1/-2 (the sheet spells both forms) | L |
| R12 | People named in the 2016 records | Sarah Sapiro, Richard Barker, Gilroy Laboratory (V1, V2). Protocol authors: Richard Barker, Cullen Vens, Aditya Singa, Simon Gilroy (P) | V1, V2, P |

## Pending (Richard to supply)

| # | Question | Notes |
|---|---|---|
| P1 | *P. syringae* pathovar/strain (e.g. DC3000?) and inoculum (OD600) | P plans flood inoculation after Ishiga et al. 2011 at OD600 = 0.4 with 0.025% Silwet L-77. Was that what was done in July/Nov? |
| P2 | flg22 concentration, peptide source, application method | P says plates were flooded with flg22 solution |
| P3 | Mock control | P says Silwet only. Confirm |
| P4 | Seedling age, medium, plate format, growth conditions | P: "½ LS, 0.3%P" on square plates. What is "P" (Phytagel?), and what were light, photoperiod and temperature? |
| P5 | What "(inverted)" / "(NI)" mean for the Hour-0 scans | Inverted plate (imaged through the agar)? |
| P6 | Meaning of the ROI quality tags (bright / norm / dark / side, bright-norm …) and the `… USE` folder selection criteria | |
| P7 | What `Laser50` / `Laser58` mean in the November scans | Laser power setting? Both share tint 3.326 s |
| P8 | What `Chroma.raw` (21 Jul 2016) is | Fluorescence reference slide? |
| P9 | Allele identities and backgrounds: fls2-17, FLS2-101, cml24-2, cml24-4, glr3.3-1/-2, glr3.4-1/-2 | Need the stock/line IDs to cite the right papers |
| P10 | Author list, affiliations, ORCIDs, funding, acknowledgements | Richard's ORCID 0000-0001-5681-9857 (verified). What were Sarah Sapiro's, Cullen Vens' and Aditya Singa's roles? Is the spelling "Singa" or "Singh" (the WARF poster has "Aditya Singh")? Acknowledge H. Jones / Middleton Spectral Vision? |
| P11 | May the two Middleton Spectral Vision reports (V1, V2) be redistributed in the public repo? | Default: cited and summarised only, not redistributed |
| P12 | Pilot leaf-area 4× discrepancy (R10) | Which column is the true cm²? |
