"""Look up candidate references on Crossref and print the best match for each query.

Used to build manuscript/references.bib: an entry goes in only if a Crossref record
confirms it (ABAI L002). No e-mail address is sent in request headers.
Usage: python scripts/crossref_lookup.py "query one" "query two" ...
"""
import json
import sys
import time
import urllib.parse
import urllib.request

UA = "PathoFluor-At/0.1 (https://github.com/dr-richard-barker/PathoFluor-At)"


def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError("rate limited")


def show(item):
    au = ", ".join(f"{a.get('family', '')} {a.get('given', '')[:1]}" for a in item.get("author", [])[:4])
    yr = (item.get("issued", {}).get("date-parts") or [[None]])[0][0]
    return (f"{au} ({yr}). {item.get('title', [''])[0]}. {item.get('container-title', [''])[0]} "
            f"{item.get('volume', '')}:{item.get('page', item.get('article-number', ''))}. doi:{item.get('DOI')}")


for q in sys.argv[1:]:
    if q.startswith("10."):
        print("DOI", q, "->", show(get("https://api.crossref.org/works/" + urllib.parse.quote(q))["message"]))
    else:
        res = get("https://api.crossref.org/works?rows=2&query.bibliographic=" + urllib.parse.quote(q))
        for it in res["message"]["items"]:
            print("Q", q[:50], "->", show(it))
    time.sleep(1)
