# Progress state (resumable)

Update this file as each stage lands, so work can resume from the filesystem (ABAI L026).

| Stage | Script | Status | Output |
|---|---|---|---|
| 0 inventory | scripts/00_inventory.py | done 2026-10-28 (0 unparsed names) | metadata/*.csv |
| 1 hand-ROI import | scripts/01_import_rois.py | done 2026-10-28 | results/roi_*.parquet, roi_features.csv.gz |
| 2 harvest raw cubes | scripts/02_harvest_cubes.py | done 2026-10-28 (400/400, 0 failures) | cache/harvest/, results/cube_qc/ |
| 3 segment seedlings | scripts/03_segment_seedlings.py | done | results/seedlings/ |
| 4 assign labels | scripts/04_assign_labels.py | works; per-plate direction from hand ROIs | results/seedlings_labelled.csv.gz, label_validation.md |
| 5 primary stats (hand ROIs) | scripts/05_stats.py | done 2026-10-28 | tables/stats_contrasts*.csv |
| 5b MCR-ALS | scripts/05b_mcr.py | done (all set-A cubes) | results/mcr_*.csv |
| 5c seedling stats | scripts/05c_seedling_stats.py | done | tables/seedling_*.csv |
| 5d set-B controls | scripts/05d_setb_controls.py | done | tables/setb_control_scans.csv |
| 6 models | scripts/06_models.py | done (hand ROIs) | tables/model_*.csv |
| 7 numbers | scripts/07_numbers.py | done | manuscript/numbers.tex |
| 8 figures | scripts/08_figures.py | figs 1-6 + S1 done | figures/ |
| 9 site | scripts/09_site_data.py | done (renders docs/index.html) | docs/ |
| 10 Zenodo | scripts/10_package_zenodo.py pack/verify/plan; zenodo_upload.py (Richard runs) | not run | staging next to source folder |
| manuscript / slides | make -C manuscript draft; make -C slides | drafts build | *_draft.pdf, *_slides.pdf |
| push | - | not yet; needs /abai check + Richard-facing review | |

Raw data: /Volumes/Barker_2016/Hyperspectral_UW-Botany_July 2016 (set PATHOFLUOR_SRC to override).
