"""Create Zenodo DRAFT records for the packaged raw cubes and upload the archives. Run by the
data owner, never by an automated agent: it reads a personal token from ZENODO_TOKEN.

Nothing is published. Review each draft in the Zenodo web interface (creators, description),
publish it there, then run with --dois to copy the DOIs into metadata/zenodo_records.csv.

Resumable: draft ids are kept in STAGE/records/drafts[_sandbox].json, so a rerun reuses the
drafts it made and skips archives already in them at full size. Every upload is checked
against the MD5 that Zenodo reports back.

Usage:
  export ZENODO_TOKEN=...            # deposit:write + deposit:actions scopes
  python scripts/zenodo_upload.py [--stage DIR] [--sandbox]          # create drafts, upload
  python scripts/zenodo_upload.py --dois [--stage DIR] [--sandbox]   # after publishing
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, SRC  # noqa: E402


def call(method, url, token, data=None):
    headers = {"Authorization": f"Bearer {token}"}
    body = None
    if data is not None:
        body, headers["Content-Type"] = json.dumps(data).encode(), "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.load(r) if r.headers.get("Content-Type", "").startswith("application/json") else None


class HashingReader:
    """File wrapper that computes the MD5 of what http.client reads from it."""

    def __init__(self, f):
        self.f, self.md5 = f, hashlib.md5()

    def read(self, n=-1):
        b = self.f.read(n)
        self.md5.update(b)
        return b


def upload_file(bucket, path, token):
    size = path.stat().st_size
    with open(path, "rb") as f:
        body = HashingReader(f)
        req = urllib.request.Request(f"{bucket}/{path.name}", data=body, method="PUT",
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": "application/octet-stream",
                                              "Content-Length": str(size)})
        with urllib.request.urlopen(req) as r:
            res = json.load(r)
    if res.get("checksum") != f"md5:{body.md5.hexdigest()}" or int(res.get("size", -1)) != size:
        raise SystemExit(f"{path.name}: Zenodo reports {res.get('checksum')} / {res.get('size')} bytes, "
                         f"sent md5:{body.md5.hexdigest()} / {size} bytes; rerun to replace it")


def upload(api, token, stage, R, drafts_path):
    drafts = json.loads(drafts_path.read_text()) if drafts_path.exists() else {}
    for k, g in R.groupby("record"):
        meta = json.loads((stage / "records" / f"record_{k:02d}.json").read_text())
        d = drafts.get(str(k))
        if d is None:
            dep = call("POST", f"{api}/deposit/depositions", token, data={})
            call("PUT", f"{api}/deposit/depositions/{dep['id']}", token, data={"metadata": meta})
            d = drafts[str(k)] = dict(id=dep["id"], bucket=dep["links"]["bucket"], html=dep["links"]["html"])
            drafts_path.write_text(json.dumps(drafts, indent=1))
        have = {x["filename"]: int(x["filesize"])
                for x in call("GET", f"{api}/deposit/depositions/{d['id']}/files", token) or []}
        for arc in g.archive:
            path = stage / arc
            if have.get(arc) == path.stat().st_size:
                print(f"record {k} (draft {d['id']}): {arc} already uploaded", flush=True)
                continue
            print(f"record {k} (draft {d['id']}): uploading {arc} ({path.stat().st_size / 1e9:.1f} GB)", flush=True)
            upload_file(d["bucket"], path, token)
        print(f"record {k}: draft ready at {d['html']} (not published)")


def fill_dois(api, token, R, drafts_path):
    drafts = json.loads(drafts_path.read_text())
    for k, d in drafts.items():
        dep = call("GET", f"{api}/deposit/depositions/{d['id']}", token)
        if not dep.get("submitted") or not dep.get("doi"):
            print(f"record {k} (draft {d['id']}) is not published yet; DOI left PENDING")
            continue
        R.loc[R.record == int(k), "doi"] = dep["doi"]
        print(f"record {k}: {dep['doi']}")
    R.to_csv(META / "zenodo_records.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, default=SRC.parent / "_PathoFluor_zenodo_staging")
    ap.add_argument("--sandbox", action="store_true", help="use sandbox.zenodo.org for a dry run")
    ap.add_argument("--dois", action="store_true", help="after publishing: write DOIs into zenodo_records.csv")
    a = ap.parse_args()
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        raise SystemExit("set ZENODO_TOKEN (personal access token) in your own shell first")
    api = "https://sandbox.zenodo.org/api" if a.sandbox else "https://zenodo.org/api"
    drafts_path = a.stage / "records" / ("drafts_sandbox.json" if a.sandbox else "drafts.json")
    R = pd.read_csv(META / "zenodo_records.csv")
    if a.dois:
        if a.sandbox:
            raise SystemExit("sandbox DOIs are not real; --dois only runs against zenodo.org")
        fill_dois(api, token, R, drafts_path)
    else:
        upload(api, token, a.stage, R, drafts_path)


if __name__ == "__main__":
    main()
