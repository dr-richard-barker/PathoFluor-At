# Label assignment and validation

Genotype lanes are found per plate x timepoint by 1-D k-means on seedling positions (three row-scans pooled). Plates were not always placed in the same orientation, so the direction (lane A at low or high line number) is chosen per plate x timepoint as the one whose assigned seedlings best track the 2016 hand ROIs (within-plate Spearman correlation of F685/F740, red-peak width and peak intensity; mean of the three).

- Plate x timepoints with hand ROIs: 23 of 23; direction fwd 12, rev 11.
- Score of the chosen direction: median 0.34; of the rejected one: median -0.02.
- Low-confidence choices (margin < 0.2): 7.
- Plates without hand ROIs (set A Pathogen 48 h) get no genotype label; they enter only treatment-level analyses.

|   hour | treatment   |   plate |   n_roi |   n_seedlings |   score_fwd |   score_rev | direction   |   margin |
|-------:|:------------|--------:|--------:|--------------:|------------:|------------:|:------------|---------:|
|      0 | Control     |       1 |      29 |            28 |        0.78 |       -0.36 | fwd         |     1.14 |
|      0 | Control     |       2 |      30 |            27 |        0.5  |        0.48 | fwd         |     0.02 |
|      0 | Control     |       3 |      30 |            23 |        0.28 |        0.17 | fwd         |     0.11 |
|      0 | Control     |       4 |      28 |            23 |       -0.06 |       -0.61 | fwd         |     0.55 |
|      0 | Pathogen    |       1 |      27 |            24 |        0.44 |        0.04 | fwd         |     0.4  |
|      0 | Pathogen    |       2 |      26 |            29 |       -0.32 |        0.58 | rev         |     0.9  |
|      0 | Pathogen    |       3 |      27 |            26 |       -0.1  |        0.35 | rev         |     0.45 |
|      0 | Pathogen    |       4 |      30 |            28 |        0.27 |        0.06 | fwd         |     0.21 |
|      0 | flg22       |       1 |      29 |            28 |        0.84 |        0.37 | fwd         |     0.47 |
|      0 | flg22       |       2 |      30 |            23 |        0.07 |        0.28 | rev         |     0.21 |
|      0 | flg22       |       3 |      30 |            28 |        0.22 |        0.24 | rev         |     0.02 |
|      0 | flg22       |       4 |      29 |            22 |       -0.1  |        0.04 | rev         |     0.14 |
|      1 | Control     |       1 |      29 |            25 |        0.13 |        0.46 | rev         |     0.34 |
|      1 | Control     |       2 |      30 |            24 |        0.47 |       -0.08 | fwd         |     0.54 |
|      1 | Control     |       3 |      30 |            21 |       -0.29 |        0.19 | rev         |     0.48 |
|      1 | Control     |       4 |      28 |            23 |        0.12 |       -0.47 | fwd         |     0.59 |
|      1 | Pathogen    |       1 |      28 |            19 |        0.04 |        0.32 | rev         |     0.28 |
|      1 | Pathogen    |       2 |      29 |            26 |        0.83 |        0.09 | fwd         |     0.74 |
|      1 | Pathogen    |       3 |      29 |            23 |       -0.02 |        0.01 | rev         |     0.02 |
|      1 | Pathogen    |       4 |      26 |            20 |       -0.33 |        0.34 | rev         |     0.67 |
|      1 | flg22       |       1 |      29 |            28 |        0.21 |        0.38 | rev         |     0.17 |
|      1 | flg22       |       2 |      29 |            23 |        0.44 |       -0.03 | fwd         |     0.46 |
|      1 | flg22       |       3 |      29 |            19 |       -0.05 |       -0.21 | fwd         |     0.16 |

Seedlings labelled: 560 of 560; possibly merged neighbours: 91.
