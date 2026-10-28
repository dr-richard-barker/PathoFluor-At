"""Create Zenodo DRAFT records for the packaged raw cubes and upload the archives. Run by the
data owner, never by an automated agent: it reads a personal token from ZENODO_TOKEN.

Nothing is published. Review each draft in the Zenodo web interface, request the quota
increase there if a record needs it, publish, then copy the DOIs into
metadata/zenodo_records.csv.

Usage:
  export ZENODO_TOKEN=...            # deposit:write + deposit:actions scopes
  python scripts/zenodo_upload.py [--stage DIR] [--sandbox]
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pathofluor.config import META, SRC  # noqa: E402


def call(method, url, token, data=None, raw=None):
    headers = {"Authorization": f"Bearer {token}"}
    body = None
    if data is not None:
        body, headers["Content-Type"] = json.dumps(data).encode(), "application/json"
    if raw is not None:
        body, headers["Content-Type"] = raw, "application/octet-stream"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.load(r) if r.headers.get("Content-Type", "").startswith("application/json") else None


def upload_file(bucket, path, token):
    size = path.stat().st_size
    with open(path, "rb") as f:
        req = urllib.request.Request(f"{bucket}/{path.name}", data=f, method="PUT",
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": "application/octet-stream",
                                              "Content-Length": str(size)})
        with urllib.request.urlopen(req) as r:
            return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, default=SRC.parent / "_PathoFluor_zenodo_staging")
    ap.add_argument("--sandbox", action="store_true", help="use sandbox.zenodo.org for a dry run")
    a = ap.parse_args()
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        raise SystemExit("set ZENODO_TOKEN (personal access token) in your own shell first")
    api = "https://sandbox.zenodo.org/api" if a.sandbox else "https://zenodo.org/api"
    R = pd.read_csv(META / "zenodo_records.csv")
    for k, g in R.groupby("record"):
        meta = json.loads((a.stage / "records" / f"record_{k:02d}.json").read_text())
        dep = call("POST", f"{api}/deposit/depositions", token, data={})
        call("PUT", f"{api}/deposit/depositions/{dep['id']}", token, data={"metadata": meta})
        for arc in g.archive:
            print(f"record {k} (draft {dep['id']}): uploading {arc}", flush=True)
            upload_file(dep["links"]["bucket"], a.stage / arc, token)
        print(f"record {k}: draft ready at {dep['links']['html']} (not published)")


if __name__ == "__main__":
    main()
