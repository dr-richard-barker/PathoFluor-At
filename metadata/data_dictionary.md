# Data dictionary

## Identifiers
- **set**: `A` = July 2016 time course (488 nm excitation); `B` = November 2016 replicate (405 nm);
  `pilot` = Feb–Mar 2016 leaf-area pilot.
- **cube_id**: `<set>_H<hour>_<treatment>_P<plate>_R<row>[_L<laser>]`, e.g. `A_H01_Control_P1_R1`.
  Non-sample cubes are `<set>_<role>_<name>`.
- **hour**: hours after treatment. In set A, `0` is the pre-treatment baseline (FACTS R6).
- **treatment**: `Control` (mock), `flg22`, `Pathogen` (*P. syringae*).
- **plate**: plate number within a treatment (1–4 in set A). Assumed to be the same physical plate at
  every timepoint.
- **row**: row-scan within a plate (1–3). Each row-scan images one row of seedlings.
- **lane**: genotype lane letter from the 2016 file names. Set A: A..E = Col-0, fls2-17, fls2-101,
  cml24-2, cml24-4. Set B: A..C = Col-0, fls2-17, fls2-101 (positional, FACTS R9).
- **plant**: plant number within a lane on a plate, in reading order (2016 hand-ROI numbering).
- **spectrum_id**: first 16 hex digits of the ROI CSV's SHA-256 (identical copies share it).

## `metadata/cube_manifest.csv`
One row per ENVI cube: design keys above; `orientation` (`inverted`/`not_inverted`, set-A hour 0
only labelled); `camera_serial`; `scan_start`/`scan_end` (local time, ISO 8601, from the header);
`tint_s` (exposure, s); `samples`/`lines`/`bands`; `wl_min`/`wl_max` (nm); camera ROI and binning;
`sha256_raw` (filled from `results/cube_qc/` after the harvest pass).

## `results/roi_features.csv.gz` (one row per unique hand-ROI spectrum)
| Column | Meaning |
|---|---|
| `f685_f740` | mean 683–687 nm / mean 736–744 nm emission (smoothed) |
| `red_peak_nm` | wavelength of the red emission maximum (670–700 nm), parabolic interpolation |
| `farred_peak_nm` | wavelength of the far-red maximum/shoulder (720–760 nm) |
| `red_fwhm_nm` | full width at half maximum of the red peak |
| `centroid_nm` | intensity-weighted mean wavelength over 650–800 nm |
| `farred_fraction` | ∫710–800 / ∫650–800 |
| `shortwave_fraction` | ∫500–640 / ∫650–800 (broad autofluorescence; FACTS V1) |
| `n650` … `n800` | spectrum on a 2 nm grid, area-normalised over 650–800 nm (per nm) |
| `tag` | 2016 annotator's ROI note (bright / norm / dark / side …; meaning pending, FACTS P6) |
| `in_use_subset` | the spectrum also appears in a 2016 `… USE` folder |
| `key_conflict` | another, different spectrum has the same design key (re-drawn ROI) |

## `results/seedlings_labelled.csv.gz` (one row per segmented seedling)
Position (`line_c`, `sample_c` in pixels), size (`n_px`), saturated pixels (`n_sat_px`), the shape
features above computed on the mean unsaturated seedling spectrum, exposure-normalised intensities
(`*_cps`, counts s⁻¹), per-pixel heterogeneity (`ratio_px_sd`, `ratio_px_p10`, `shortwave_px_p90`),
and assigned `lane`/`plant`/`genotype` with the plate's chosen scan `direction` and its `margin`
(see `results/label_validation.md`).
