"""Package the raw cubes for Zenodo as lossless tar.zst archives, verify them, and plan records.

Zenodo limits (help.zenodo.org, checked 2026-10-28): 50 GB and 100 files per record by default,
with a one-time increase to 200 GB available on request. Archives are grouped by set x hour x
treatment and packed into records of at most RECORD_LIMIT bytes.

Steps (each resumable; finished archives are skipped):
  pack     tar each group's .raw + .hdr (original relative paths) | zstd -> STAGE/<archive>.tar.zst
  verify   stream-decompress every archive and check each member's SHA-256 against
           metadata/cube_manifest.csv (raw) or the file inventory (headers)
  plan     write metadata/zenodo_records.csv and STAGE/records/<record>.json (Zenodo metadata)

Usage: python scripts/10_package_zenodo.py pack|verify|plan [--level 10] [--stage DIR]
The staging directory defaults to a folder next to (not inside) the source folder.
Uploading is a separate, user-run step: scripts/zenodo_upload.py (needs ZENODO_TOKEN).
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, SRC  # noqa: E402

RECORD_LIMIT = 45e9   # stay under the 50 GB default with margin
DEFAULT_STAGE = SRC.parent / "_PathoFluor_zenodo_staging"


def groups(cm):
    cm = cm[cm["set"].isin(["A", "B"])].copy()
    cm["group"] = cm.apply(lambda r: f"{r['set']}_H{int(r.hour):02d}_{r.treatment}" if r.role == "sample"
                           else f"{r['set']}_{'bacteria' if r.role == 'bacteria_scan' else 'reference'}", axis=1)
    return cm


def pack(cm, stage, level):
    stage.mkdir(parents=True, exist_ok=True)
    for g, d in cm.groupby("group"):
        out = stage / f"PathoFluor-At_{g}.tar.zst"
        if out.exists() and (stage / f"{out.name}.done").exists():
            continue
        members = sorted(set(d.relpath_raw) | set(d.relpath_hdr))
        listfile = stage / f"{g}.members.txt"
        listfile.write_text("\n".join(members) + "\n")
        print(f"packing {g}: {len(members)} files, {d.raw_bytes.sum() / 1e9:.1f} GB raw", flush=True)
        tar = subprocess.Popen(["tar", "-C", str(SRC), "-cf", "-", "-T", str(listfile)], stdout=subprocess.PIPE)
        with open(out, "wb") as f:
            z = subprocess.run(["zstd", f"-{level}", "-T0", "--long=27", "-q", "-c"], stdin=tar.stdout, stdout=f)
        tar.wait()
        if tar.returncode or z.returncode:
            out.unlink(missing_ok=True)
            raise SystemExit(f"packing {g} failed (tar {tar.returncode}, zstd {z.returncode})")
        (stage / f"{out.name}.done").write_text("")


def verify(cm, stage):
    inv = pd.read_csv(META / "file_inventory.csv").set_index("relpath").sha256
    want = {**cm.set_index("relpath_raw").sha256_raw.to_dict(), **{p: inv.get(p) for p in cm.relpath_hdr}}
    rows = []
    for arc in sorted(stage.glob("PathoFluor-At_*.tar.zst")):
        ok_flag = stage / f"{arc.name}.verified"
        h = hashlib.sha256()
        with open(arc, "rb") as f:
            for chunk in iter(lambda: f.read(16 << 20), b""):
                h.update(chunk)
        arc_sha = h.hexdigest()
        if not ok_flag.exists():
            z = subprocess.Popen(["zstd", "-d", "--long=27", "-q", "-c", str(arc)], stdout=subprocess.PIPE)
            bad = []
            with tarfile.open(fileobj=z.stdout, mode="r|") as t:
                for m in t:
                    if not m.isfile():
                        continue
                    mh = hashlib.sha256()
                    fo = t.extractfile(m)
                    for chunk in iter(lambda: fo.read(16 << 20), b""):
                        mh.update(chunk)
                    if want.get(m.name) is None or want[m.name] != mh.hexdigest():
                        bad.append(m.name)
            z.wait()
            if bad or z.returncode:
                raise SystemExit(f"{arc.name}: {len(bad)} members failed SHA-256 check: {bad[:5]}")
            ok_flag.write_text(arc_sha)
        rows.append(dict(archive=arc.name, bytes=arc.stat().st_size, sha256=arc_sha))
        print(f"verified {arc.name}", flush=True)
    pd.DataFrame(rows).to_csv(stage / "archives.csv", index=False)


def plan(cm, stage):
    a = pd.read_csv(stage / "archives.csv").sort_values("archive")
    rec, size, out = 1, 0, []
    for r in a.itertuples():
        if size + r.bytes > RECORD_LIMIT or sum(1 for x in out if x["record"] == rec) >= 95:
            rec, size = rec + 1, 0
        size += r.bytes
        out.append(dict(record=rec, archive=r.archive, bytes=r.bytes, sha256=r.sha256, doi="PENDING"))
    R = pd.DataFrame(out)
    R.to_csv(META / "zenodo_records.csv", index=False)
    (stage / "records").mkdir(exist_ok=True)
    n = R.record.max()
    for k, g in R.groupby("record"):
        meta = {
            "title": f"PathoFluor-At raw fluorescence hyperspectral cubes, part {k} of {n}",
            "upload_type": "dataset",
            "description": ("<p>Raw ENVI cubes (BIL, uint16) from the 2016 UW-Madison fluorescence hyperspectral "
                            "imaging of Arabidopsis seedlings treated with mock, flg22 or Pseudomonas syringae. "
                            f"Part {k} of {n}; archives: " + ", ".join(g.archive) + ". Each archive is a tar "
                            "stream compressed with zstd (--long=27); members keep the original drive paths. "
                            "SHA-256 of every member is in metadata/cube_manifest.csv and of every archive in "
                            "metadata/zenodo_records.csv of the code repository.</p>"),
            "creators": [{"name": "Barker, Richard J.", "orcid": "0000-0001-5681-9857"}],
            "license": "cc-by-4.0", "access_right": "open",
            "keywords": ["Arabidopsis thaliana", "hyperspectral imaging", "chlorophyll fluorescence", "flg22",
                         "Pseudomonas syringae"],
            "related_identifiers": [{"identifier": "https://github.com/dr-richard-barker/PathoFluor-At",
                                     "relation": "isSupplementTo"}],
        }
        (stage / "records" / f"record_{k:02d}.json").write_text(json.dumps(meta, indent=1))
    print(R.groupby("record").agg(archives=("archive", "size"), GB=("bytes", lambda b: round(b.sum() / 1e9, 1))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["pack", "verify", "plan"])
    ap.add_argument("--level", type=int, default=10)
    ap.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    a = ap.parse_args()
    cm = groups(pd.read_csv(META / "cube_manifest.csv"))
    if cm.sha256_raw.isna().any():
        raise SystemExit("cube_manifest.csv lacks raw SHA-256 values: run 02 then 00 first")
    {"pack": lambda: pack(cm, a.stage, a.level), "verify": lambda: verify(cm, a.stage),
     "plan": lambda: plan(cm, a.stage)}[a.step]()


if __name__ == "__main__":
    main()
