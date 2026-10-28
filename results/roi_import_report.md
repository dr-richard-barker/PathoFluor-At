# ROI import report

Pilot: 24 tables, 476 values (units: see FACTS_PENDING R10/P12).
Spectra: 5842 files -> 2486 unique (A 1982, B 504).
Design-key conflicts (same hour/treatment/plate/lane/plant, different spectrum): 12 spectra in 6 keys.

Spectra per set x hour x treatment:

|             |   Control |   Pathogen |   flg22 |
|:------------|----------:|-----------:|--------:|
| ('A', 0.0)  |       117 |        110 |     118 |
| ('A', 1.0)  |       117 |        112 |     117 |
| ('A', 2.0)  |       119 |        115 |     116 |
| ('A', 3.0)  |       117 |        118 |     117 |
| ('A', 24.0) |       119 |        113 |     120 |
| ('A', 48.0) |       118 |        nan |     119 |
| ('B', 0.0)  |        46 |         46 |      47 |
| ('B', 6.0)  |        37 |         37 |      38 |
| ('B', 24.0) |        40 |         37 |      43 |
| ('B', 48.0) |        48 |         40 |      45 |

Spectra per set x genotype:

|                   |   n |
|:------------------|----:|
| ('A', 'Col-0')    | 402 |
| ('A', 'cml24-2')  | 391 |
| ('A', 'cml24-4')  | 401 |
| ('A', 'fls2-101') | 397 |
| ('A', 'fls2-17')  | 391 |
| ('B', 'Col-0')    | 181 |
| ('B', 'fls2-101') | 167 |
| ('B', 'fls2-17')  | 156 |

ROI quality tags (set A):

| tag                   |    n |
|:----------------------|-----:|
| bright                | 1028 |
| norm                  |  346 |
| bright-norm           |  199 |
| dark                  |  137 |
| norm-bright           |  136 |
| norm-dark             |   41 |
| bright side           |   27 |
| side                  |   16 |
| dark-norm             |   11 |
| norm side             |    8 |
| brightish             |    7 |
| bright but dying      |    7 |
| wobbly                |    6 |
| bright and dying      |    2 |
| bright dying          |    1 |
| bright-side           |    1 |
| tiny and norm         |    1 |
| bright half&dark half |    1 |
| brightish dark        |    1 |
| bright underside      |    1 |
| dark but flat         |    1 |
| darkish-norm          |    1 |
| nomr-bright           |    1 |
| brightish side        |    1 |
| dark side             |    1 |
