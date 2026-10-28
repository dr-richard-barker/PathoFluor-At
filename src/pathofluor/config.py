"""Paths and fixed study constants."""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# The 2016 source drive. Override with PATHOFLUOR_SRC if it is mounted elsewhere.
SRC = Path(os.environ.get(
    "PATHOFLUOR_SRC", "/Volumes/Barker_2016/Hyperspectral_UW-Botany_July 2016"))

META = REPO / "metadata"
RESULTS = REPO / "results"
FIGURES = REPO / "figures"
TABLES = REPO / "tables"

# Lane letter -> genotype for the July 2016 set (set A). Taken from the 2016
# Results/<treatment>/<genotype>/ folders, whose CSVs carry exactly one lane letter each.
LANES_A = {"A": "Col-0", "B": "fls2-17", "C": "fls2-101", "D": "cml24-2", "E": "cml24-4"}

# Lane letter -> genotype for the November 2016 set (set B). Positional: the vendor report
# states "First 3 plants in each image is the wild type (Col-0), followed by FLS2-17 and
# FLS2-101". Pending confirmation from Richard (metadata/FACTS_PENDING.md, R9).
LANES_B = {"A": "Col-0", "B": "fls2-17", "C": "fls2-101"}

# Excitation wavelength per set (vendor reports V1/V2 in metadata/FACTS_PENDING.md).
EXCITATION_NM = {"A": 488, "B": 405}

# Treatment codes used in the 2016 file names.
TREATMENT_CODE = {"C": "Control", "F": "flg22", "P": "Pathogen"}

# Spectral window holding the chlorophyll-fluorescence signal; 400-640 nm is dark level.
CHLF_WINDOW = (650.0, 800.0)
DARK_WINDOW = (420.0, 620.0)
