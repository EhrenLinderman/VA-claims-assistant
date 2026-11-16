#!/usr/bin/env python3
"""
VA Claims Assistant - check eCFR for newer 38 CFR Part 3/4 text and, if found,
download and convert it. Falls back to the copy bundled with the app.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0).
Standard library only.

Usage:
  python3 cfr_update.py --bundled <plugin>/skills/cfr/references/cfr --local <vet>/VA-Claim-Output/VA-Rules
Prints JSON: {"status": "up_to_date" | "updated" | "offline", "use_dir": ..., "as_of": ...}
"""

_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, sys, tempfile, urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfr_convert import convert  # noqa: E402

API = "https://www.ecfr.gov/api/versioner/v1"
PARTS = ("3", "4")


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "VA-Claims-Assistant/0.3 (free Veteran tool)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def read_meta(d):
    try:
        with open(os.path.join(d, "meta.json")) as f:
            return json.load(f)
    except Exception:
        return None


def latest_amendment(part, fetch):
    data = json.loads(fetch(f"{API}/versions/title-38.json?part={part}"))
    dates = [v.get("amendment_date") or v.get("date") for v in data.get("content_versions", [])]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def run(bundled, local, fetch=http_get):
    current_dir, current = bundled, read_meta(bundled)
    lm = read_meta(local)
    if lm and current and lm["as_of"] > current["as_of"]:
        current_dir, current = local, lm
    as_of = current["as_of"] if current else "0000-00-00"
    try:
        titles = json.loads(fetch(f"{API}/titles.json"))["titles"]
        t38 = next(t for t in titles if int(t["number"]) == 38)
        up_to = t38["up_to_date_as_of"]
        newest = max(filter(None, (latest_amendment(p, fetch) for p in PARTS)), default=None)
    except Exception as e:  # no internet, blocked, API change
        return {"status": "offline", "use_dir": current_dir, "as_of": as_of, "detail": str(e)[:200]}

    if newest is None or newest <= as_of:
        return {"status": "up_to_date", "use_dir": current_dir, "as_of": as_of,
                "checked": date.today().isoformat(), "latest_change": newest}
    try:
        tmp = tempfile.mkdtemp()
        paths = []
        for p in PARTS:
            xml = fetch(f"{API}/full/{up_to}/title-38.xml?part={p}")
            fp = os.path.join(tmp, f"part{p}.xml")
            with open(fp, "wb") as f:
                f.write(xml)
            paths.append(fp)
        meta = convert(paths, local, up_to)
        return {"status": "updated", "use_dir": local, "as_of": up_to,
                "previous_as_of": as_of, "latest_change": newest, "sections": meta["sections"]}
    except Exception as e:
        return {"status": "offline", "use_dir": current_dir, "as_of": as_of,
                "detail": "download failed: " + str(e)[:200]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundled", required=True)
    ap.add_argument("--local", required=True)
    a = ap.parse_args()
    print(json.dumps(run(a.bundled, a.local), indent=2))
