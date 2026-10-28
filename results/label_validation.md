# Label assignment and validation

Genotype lanes are found per plate x timepoint by 1-D k-means on seedling positions (three row-scans pooled). Plates were not always placed in the same orientation, so the direction (lane A at low or high line number) is chosen per plate x timepoint as the one whose assigned seedlings best track the 2016 hand ROIs (within-plate Spearman correlation of F685/F740, red-peak width and peak intensity; mean of the three).

- Plate x timepoints with hand ROIs: 68 of 72; direction fwd 34, rev 34.
- Score of the chosen direction: median 0.28; of the rejected one: median -0.06.
- Low-confidence choices (margin < 0.2): 16.
- Plates without hand ROIs (set A Pathogen 48 h) get no genotype label; they enter only treatment-level analyses.

|   hour | treatment   |   plate |   n_roi |   n_seedlings |   score_fwd |   score_rev | direction   |   margin |
|-------:|:------------|--------:|--------:|--------------:|------------:|------------:|:------------|---------:|
|      0 | Control     |       1 |      29 |            28 |        0.78 |       -0.36 | fwd         |     1.14 |
|      0 | Control     |       2 |      30 |            27 |        0.5  |        0.48 | fwd         |     0.02 |
|      0 | Control     |       3 |      30 |            23 |        0.28 |        0.17 | fwd         |     0.11 |
|      0 | Control     |       4 |      28 |            23 |       -0.06 |       -0.61 | fwd         |     0.55 |
|      0 | Pathogen    |       1 |      27 |            24 |        0.44 |        0.05 | fwd         |     0.39 |
|      0 | Pathogen    |       2 |      26 |            29 |       -0.32 |        0.58 | rev         |     0.91 |
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
|      1 | Pathogen    |       3 |      29 |            23 |       -0.02 |        0.01 | rev         |     0.03 |
|      1 | Pathogen    |       4 |      26 |            20 |       -0.33 |        0.34 | rev         |     0.67 |
|      1 | flg22       |       1 |      29 |            28 |        0.21 |        0.38 | rev         |     0.17 |
|      1 | flg22       |       2 |      29 |            23 |        0.44 |       -0.03 | fwd         |     0.47 |
|      1 | flg22       |       3 |      29 |            28 |        0.01 |       -0.06 | fwd         |     0.07 |
|      1 | flg22       |       4 |      30 |            21 |        0.36 |       -0.07 | fwd         |     0.42 |
|      2 | Control     |       1 |      30 |            24 |        0.15 |        0.29 | rev         |     0.14 |
|      2 | Control     |       2 |      30 |            24 |        0.63 |       -0.06 | fwd         |     0.69 |
|      2 | Control     |       3 |      30 |            21 |       -0.21 |        0.28 | rev         |     0.49 |
|      2 | Control     |       4 |      29 |            22 |       -0.16 |       -0.43 | fwd         |     0.27 |
|      2 | Pathogen    |       1 |      30 |            19 |       -0.25 |        0.27 | rev         |     0.53 |
|      2 | Pathogen    |       2 |      29 |            26 |        0.82 |       -0.14 | fwd         |     0.96 |
|      2 | Pathogen    |       3 |      30 |            23 |       -0.16 |       -0.2  | fwd         |     0.04 |
|      2 | Pathogen    |       4 |      26 |            21 |       -0.06 |        0.42 | rev         |     0.48 |
|      2 | flg22       |       1 |      26 |            26 |        0.05 |        0.73 | rev         |     0.68 |
|      2 | flg22       |       2 |      30 |            22 |        0.18 |       -0.23 | fwd         |     0.41 |
|      2 | flg22       |       3 |      30 |            27 |        0.07 |        0.08 | rev         |     0.01 |
|      2 | flg22       |       4 |      30 |            21 |        0.23 |       -0.07 | fwd         |     0.3  |
|      3 | Control     |       1 |      30 |            24 |        0.19 |        0.38 | rev         |     0.19 |
|      3 | Control     |       2 |      30 |            25 |        0.67 |        0.01 | fwd         |     0.66 |
|      3 | Control     |       3 |      29 |            22 |       -0.21 |        0.12 | rev         |     0.33 |
|      3 | Control     |       4 |      28 |            22 |        0.19 |       -0.18 | fwd         |     0.38 |
|      3 | Pathogen    |       1 |      30 |            19 |       -0.32 |        0.28 | rev         |     0.6  |
|      3 | Pathogen    |       2 |      30 |            25 |        0.37 |       -0.13 | fwd         |     0.5  |
|      3 | Pathogen    |       3 |      30 |            23 |       -0.1  |        0.23 | rev         |     0.33 |
|      3 | Pathogen    |       4 |      28 |            20 |        0.27 |        0.07 | fwd         |     0.2  |
|      3 | flg22       |       1 |      29 |            26 |       -0.04 |        0.36 | rev         |     0.4  |
|      3 | flg22       |       2 |      30 |            22 |        0.32 |       -0.06 | fwd         |     0.38 |
|      3 | flg22       |       3 |      28 |            26 |        0.05 |        0.12 | rev         |     0.07 |
|      3 | flg22       |       4 |      30 |            21 |        0.26 |       -0.12 | fwd         |     0.38 |
|     24 | Control     |       1 |      30 |            19 |        0.03 |        0.26 | rev         |     0.23 |
|     24 | Control     |       2 |      30 |            22 |        0.45 |       -0    | fwd         |     0.45 |
|     24 | Control     |       3 |      30 |            19 |       -0.24 |        0.01 | rev         |     0.25 |
|     24 | Control     |       4 |      29 |            20 |        0.13 |       -0.18 | fwd         |     0.31 |
|     24 | Pathogen    |       1 |      30 |            20 |       -0.38 |        0.19 | rev         |     0.57 |
|     24 | Pathogen    |       2 |      29 |            24 |        0.6  |       -0.18 | fwd         |     0.79 |
|     24 | Pathogen    |       3 |      29 |            24 |       -0.13 |        0.24 | rev         |     0.37 |
|     24 | Pathogen    |       4 |      25 |            18 |       -0    |       -0.02 | fwd         |     0.01 |
|     24 | flg22       |       1 |      30 |            23 |        0.01 |        0.47 | rev         |     0.46 |
|     24 | flg22       |       2 |      30 |            15 |        0.39 |       -0.02 | fwd         |     0.41 |
|     24 | flg22       |       3 |      30 |            21 |       -0.1  |       -0.05 | rev         |     0.05 |
|     24 | flg22       |       4 |      30 |            21 |        0.01 |        0.08 | rev         |     0.07 |
|     48 | Control     |       1 |      30 |            16 |       -0.03 |        0.33 | rev         |     0.36 |
|     48 | Control     |       2 |      30 |            20 |        0.5  |       -0.3  | fwd         |     0.8  |
|     48 | Control     |       3 |      30 |            13 |        0.08 |       -0.17 | fwd         |     0.24 |
|     48 | Control     |       4 |      28 |            18 |       -0.12 |        0.02 | rev         |     0.14 |
|     48 | Pathogen    |       1 |       0 |            21 |      nan    |      nan    | nan         |   nan    |
|     48 | Pathogen    |       2 |       0 |            27 |      nan    |      nan    | nan         |   nan    |
|     48 | Pathogen    |       3 |       0 |            26 |      nan    |      nan    | nan         |   nan    |
|     48 | Pathogen    |       4 |       0 |            21 |      nan    |      nan    | nan         |   nan    |
|     48 | flg22       |       1 |      28 |            24 |       -0.01 |        0.21 | rev         |     0.22 |
|     48 | flg22       |       2 |      30 |            15 |        0.31 |       -0.34 | fwd         |     0.65 |
|     48 | flg22       |       3 |      31 |            17 |        0.5  |        0.2  | fwd         |     0.29 |
|     48 | flg22       |       4 |      30 |            18 |        0.08 |        0.28 | rev         |     0.2  |

Seedlings labelled: 2662 of 2757; possibly merged neighbours: 436.

Set B (vendor lane order taken as fwd): on plate 1, where leaf ROIs exist, fwd agrees better in 21 of 24 hour x treatment x laser comparisons (mean score fwd 0.72, rev 0.14). Plates 2-3: assumed.
