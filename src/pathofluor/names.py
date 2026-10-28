"""Parse the 2016 file names into structured metadata.

The names are the only record of design for most files, so the parsers are
strict: anything that does not match returns None and is reported, never guessed.
"""
import re

from .config import LANES_A, TREATMENT_CODE

# Set A cubes, e.g. "Hour0 Control1 Row1 (inverted)", "Hour0 FLG22-2 Row1 (NI)",
# "Hour2 Conrol1 Row3" (sic), "Hour24 Pathogen3 Row2".
_CUBE_A = re.compile(
    r"^Hour(?P<hour>\d+)\s+(?P<trt>Control|Conrol|FLG22-?|Pathogen)(?P<plate>\d)\s+"
    r"Row(?P<row>\d)(?:\s*\((?P<orient>inverted|NI)\))?$")

# Set B cubes, e.g. "Hr0 C1 Row1 Laser50", "Hr6 P3 R2 Laser58", "Hr24 Bacteria Laser50".
_CUBE_B = re.compile(
    r"^Hr(?P<hour>\d+)\s+(?:(?P<trt>[CFP])(?P<plate>\d)\s+R(?:ow)?(?P<row>\d)|(?P<bact>Bacteria))"
    r"\s+Laser(?P<laser>\d+)$")
_REF_B = re.compile(r"^reference-(?P<stamp>[\d\-_.]+)\s+Laser(?P<laser>\d+)$")

# Set A ROI spectra, e.g. "Hr0 P1 A Plant1 (dark)", "Hr0 C1 A Plant5 (norm side)",
# "Hr2 F1 A Plant3 (bright) - Copy" (a Windows file-copy duplicate).
_ROI_A = re.compile(
    r"^Hr(?P<hour>\d+)\s+(?P<trt>[CFP])(?P<plate>\d)\s+(?P<lane>[A-E])\s+Plant(?P<plant>\d+)"
    r"(?:\s*\((?P<tag>[^)]*)\))?(?P<copy>\s*-\s*Copy)?$")
# Set B ROI spectra, e.g. "Hr0 P1 A Leaf1", "Hr24 P1 A Leaf11 (dark)", "H48 C1 A Leaf3".
_ROI_B = re.compile(
    r"^Hr?(?P<hour>\d+)\s+(?P<trt>[CFP])(?P<plate>\d)\s+(?P<lane>[A-C])\s+Leaf(?P<plant>\d+)"
    r"(?:\s*\((?P<tag>[^)]*)\))?$")
# Pilot summary tables, e.g. "cml24-2_control_hyperspectral_Patho".
_PILOT = re.compile(r"^(?P<geno>[^_]+)_(?P<trt>control|flg22|pathogen|pahogen)_hyperspectral_Patho$", re.I)

_TRT_WORD = {"control": "Control", "conrol": "Control", "flg22": "flg22", "flg22-": "flg22",
             "pathogen": "Pathogen", "pahogen": "Pathogen", "bacteria": "Pathogen"}


def parse_cube(stem, relpath):
    """Return a dict describing a cube, or None if the name is not understood."""
    top = relpath.split("/")[0]
    if top.startswith("Hour"):
        m = _CUBE_A.match(stem)
        if not m:
            return None
        return dict(set="A", hour=int(m["hour"]), treatment=_TRT_WORD[m["trt"].lower()],
                    plate=int(m["plate"]), row=int(m["row"]),
                    orientation={"inverted": "inverted", "NI": "not_inverted"}.get(m["orient"], "not_inverted"),
                    orientation_labelled=m["orient"] is not None, laser=None, role="sample")
    if top == "Hyper_spectral_work_from_Sarah_Sapiro":
        m = _CUBE_B.match(stem)
        if m:
            if m["bact"]:
                return dict(set="B", hour=int(m["hour"]), treatment="Pathogen", plate=None, row=None,
                            orientation=None, orientation_labelled=False, laser=int(m["laser"]),
                            role="bacteria_scan")
            return dict(set="B", hour=int(m["hour"]), treatment=TREATMENT_CODE[m["trt"]],
                        plate=int(m["plate"]), row=int(m["row"]), orientation=None,
                        orientation_labelled=False, laser=int(m["laser"]), role="sample")
        m = _REF_B.match(stem)
        if m:
            return dict(set="B", hour=None, treatment=None, plate=None, row=None, orientation=None,
                        orientation_labelled=False, laser=int(m["laser"]), role="reference")
        return None
    if stem == "Chroma":
        return dict(set="A", role="reference_chroma")
    if stem == "Weird Dark Line":
        return dict(set="A", role="artefact_scan")
    if top == "KemoQuant":
        return dict(set="excluded", role="instrument_test")
    return None


def parse_roi(stem, relpath):
    """Return a dict describing a hand-ROI spectrum CSV, or None."""
    parts = relpath.split("/")
    if parts[0] == "Hyper_spectral_work_from_Sarah_Sapiro":
        m = _ROI_B.match(stem)
        if not m:
            return None
        return dict(set="B", hour=int(m["hour"]), treatment=TREATMENT_CODE[m["trt"]],
                    plate=int(m["plate"]), lane=m["lane"], genotype=None,
                    plant=int(m["plant"]), tag=m["tag"], file_copy=False)
    if parts[0] == "Plant hyperspectral assay":
        m = _PILOT.match(stem)
        if not m:
            return None
        return dict(set="pilot", hour=None, treatment=_TRT_WORD[m["trt"].lower()], plate=None,
                    lane=None, genotype=m["geno"], plant=None, tag=None, file_copy=False)
    m = _ROI_A.match(stem)
    if not m:
        return None
    return dict(set="A", hour=int(m["hour"]), treatment=TREATMENT_CODE[m["trt"]],
                plate=int(m["plate"]), lane=m["lane"], genotype=LANES_A[m["lane"]],
                plant=int(m["plant"]), tag=(m["tag"] or "").strip() or None,
                file_copy=m["copy"] is not None)
