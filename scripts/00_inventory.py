"""Inventory the 2016 source drive (read-only).

Writes
  metadata/file_inventory.csv  every file on the drive: size, category, SHA-256 (small files)
  metadata/cube_manifest.csv   one row per hyperspectral cube, parsed from name + ENVI header
  metadata/roi_manifest.csv    one row per hand-ROI spectrum CSV (all copies, with content hash)
  metadata/unparsed.txt        names the parsers did not recognise (must be reviewed, not guessed)

Raw-cube SHA-256 values are filled in from results/cube_qc/<cube_id>.json, written by
02_extract_cubes.py during its single sequential read of each cube; re-run this script after
that pass to complete the manifest.
"""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, RESULTS, SRC  # noqa: E402
from pathofluor.envi import parse_header  # noqa: E402
from pathofluor.names import parse_cube, parse_roi  # noqa: E402

SMALL = 100 << 20  # hash files up to 100 MB here; raw cubes are hashed in 02


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def category(rel):
    top = rel.split("/")[0]
    if top == "Flood_DRB":
        return "excluded_other_study"
    if top == "KemoQuant":
        return "excluded_instrument_test"
    if Path(rel).name.startswith("._") or Path(rel).name == ".DS_Store":
        return "excluded_os_metadata"
    if top == "Hyper_spectral_work_from_Sarah_Sapiro":
        return "set_B"
    if top == "Plant hyperspectral assay":
        return "pilot"
    return "set_A"


def parse_time(s):
    """Header timestamps as written by the acquisition software. Set-B software sometimes
    writes a 24-hour time with an AM/PM suffix ('16:30:38 PM'); the suffix is then ignored."""
    s = " ".join(str(s).split())
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S %p", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).isoformat()
        except ValueError:
            continue
    return None


def cube_id(info, stem):
    if info.get("role") != "sample" and info.get("role") != "bacteria_scan":
        return f"{info['set']}_{info['role']}_{stem.replace(' ', '_')}"
    parts = [info["set"], f"H{info['hour']:02d}", info["treatment"]]
    if info["plate"] is not None:
        parts += [f"P{info['plate']}", f"R{info['row']}"]
    else:
        parts += ["bacteria"]
    if info["laser"] is not None:
        parts += [f"L{info['laser']}"]
    return "_".join(parts)


def location_kind(rel):
    parts = rel.split("/")
    if parts[0] == "Hyper_spectral_work_from_Sarah_Sapiro":
        return "setB_export"
    if parts[0] == "Plant hyperspectral assay":
        return "pilot_table"
    if any("USE" in p for p in parts[:-1]):
        return "use_subset"
    if parts[0] == "Results":
        return "genotype_sorted"
    if parts[0].startswith("Hour"):
        return "timepoint_export"
    return "other"


def main():
    META.mkdir(exist_ok=True)
    files = sorted(p for p in SRC.rglob("*") if p.is_file())
    print(f"{len(files)} files under {SRC}")

    rows = []
    for p in files:
        rel = p.relative_to(SRC).as_posix()
        rows.append(dict(relpath=rel, bytes=p.stat().st_size,
                         ext=p.suffix.lower().lstrip("."), category=category(rel)))
    inv = pd.DataFrame(rows)
    small = inv[(inv.bytes <= SMALL) & ~inv.category.str.startswith("excluded_os")]
    with ThreadPoolExecutor(8) as ex:
        hashes = dict(zip(small.relpath, ex.map(lambda r: sha256(SRC / r), small.relpath)))
    inv["sha256"] = inv.relpath.map(hashes)

    unparsed = []

    # ---- cubes
    qc_dir = RESULTS / "cube_qc"
    cubes = []
    for rel in inv[(inv.ext == "hdr") & inv.category.isin(["set_A", "set_B", "excluded_instrument_test"])].relpath:
        stem = Path(rel).stem
        info = parse_cube(stem, rel)
        if info is None:
            unparsed.append(f"cube\t{rel}")
            continue
        h = parse_header(SRC / rel)
        wl = h.get("wavelength")
        raw_rel = str(Path(rel).with_suffix(".raw"))
        cid = cube_id(info, stem)
        qc = qc_dir / f"{cid}.json"
        cubes.append(dict(
            cube_id=cid, relpath_hdr=rel, relpath_raw=raw_rel,
            raw_bytes=int(inv.loc[inv.relpath == raw_rel, "bytes"].iloc[0]) if (inv.relpath == raw_rel).any() else None,
            **{k: info.get(k) for k in ("set", "role", "hour", "treatment", "plate", "row",
                                        "orientation", "orientation_labelled", "laser")},
            camera=h.get("camera model"), camera_serial=h.get("serial number"),
            scan_start=parse_time(h.get("scanstarttime", "")),
            scan_end=parse_time(h.get("scanendtime", "")),
            tint_s=float(h["tint"]) if "tint" in h else None,
            framerate=h.get("framerate") or h.get("fps"),
            samples=h["samples"], lines=h["lines"], bands=h["bands"],
            wl_min=float(wl.min()) if wl is not None else None,
            wl_max=float(wl.max()) if wl is not None else None,
            roi_left=h.get("roi left"), roi_width=h.get("roi width"),
            roi_top=h.get("roi top"), roi_height=h.get("roi height"),
            hbin=h.get("hbin"), vbin=h.get("vbin"), readout=h.get("readout rate") or h.get("readoutrate"),
            gain=h.get("gain mode") or h.get("dynamicrangemode"),
            sha256_raw=json.loads(qc.read_text()).get("sha256_raw") if qc.exists() else None,
        ))
    cm = pd.DataFrame(cubes).sort_values(["set", "role", "hour", "treatment", "plate", "row", "laser"],
                                         na_position="last")
    dup = cm.cube_id.duplicated(keep=False)
    if dup.any():
        raise SystemExit(f"duplicate cube ids:\n{cm[dup][['cube_id', 'relpath_hdr']]}")
    cm.to_csv(META / "cube_manifest.csv", index=False)

    # ---- ROI spectra
    rois = []
    for rel in inv[(inv.ext == "csv") & inv.category.isin(["set_A", "set_B", "pilot"])].relpath:
        info = parse_roi(Path(rel).stem, rel)
        if info is None:
            unparsed.append(f"roi\t{rel}")
            continue
        n_rows = sum(1 for line in open(SRC / rel, errors="replace") if line.strip())
        rois.append(dict(relpath=rel, location=location_kind(rel), **info,
                         n_rows=n_rows, sha256=hashes.get(rel)))
    rm = pd.DataFrame(rois)
    rm["spectrum_id"] = rm.sha256.str[:16]
    rm.to_csv(META / "roi_manifest.csv", index=False)

    inv.to_csv(META / "file_inventory.csv", index=False)
    (META / "unparsed.txt").write_text("\n".join(unparsed) + ("\n" if unparsed else ""))

    # ---- summary
    print(inv.groupby("category").agg(files=("relpath", "size"), GB=("bytes", lambda b: round(b.sum() / 1e9, 2))))
    print("\ncubes by set/role:\n", cm.groupby(["set", "role"]).size())
    print("\nROI files by set/location:\n", rm.groupby(["set", "location"]).size())
    print("unique spectra by set:\n", rm.groupby("set").spectrum_id.nunique())
    print(f"\nunparsed names: {len(unparsed)}")
    for u in unparsed[:40]:
        print("  ", u)


if __name__ == "__main__":
    main()
