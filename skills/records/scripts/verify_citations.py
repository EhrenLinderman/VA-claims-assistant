#!/usr/bin/env python3
"""
VA Claims Assistant - check every page cited in claims.json: the page must exist,
must be the kept copy (not a duplicate), and should contain words from the
"shows" summary. Re-points duplicate citations to the kept copy (--fix).
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

Usage: python3 verify_citations.py --pages pages_dedup.jsonl --claims claims.json [--fix]
Exit code 1 if any cited page is missing or no keyword matches.
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import gzip, argparse, json, re, sys

STOP = {"veteran", "exam", "diagnosis", "records", "service", "active", "statement", "clinic", "documented", "condition", "claimant"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True)
    ap.add_argument("--claims", required=True)
    ap.add_argument("--fix", action="store_true")
    a = ap.parse_args()
    pages = [json.loads(l) for l in (gzip.open(a.pages, "rt", encoding="utf-8") if a.pages.endswith(".gz") else open(a.pages, encoding="utf-8"))]
    idx = {(p["file"], p["page"]): p for p in pages}
    byid = {p["id"]: p for p in pages}
    C = json.load(open(a.claims))
    bad = 0
    for c in C["claims"]:
        for e in c["evidence"]:
            p = idx.get((e["file"], e["page"]))
            if not p:
                print(f'MISSING  {c["id"]} {e["file"]} p{e["page"]}'); bad += 1; continue
            if p["dup_of"] is not None:
                k = byid[p["dup_of"]]
                print(f'DUP      {c["id"]} {e["file"]} p{e["page"]} -> kept copy {k["file"]} p{k["page"]}')
                if a.fix:
                    e.setdefault("also_in", []).append({"file": e["file"], "page": e["page"]})
                    e["file"], e["page"] = k["file"], k["page"]
                    p = k
            words = [w for w in re.findall(r"[A-Za-z]{6,}", e["shows"]) if w.lower() not in STOP][:4]
            hits = [w for w in words if w.lower() in p["text"].lower()]
            if words and not hits:
                print(f'NO-MATCH {c["id"]} {e["file"]} p{e["page"]} (check by eye): {e["shows"][:80]}'); bad += 1
    if a.fix:
        json.dump(C, open(a.claims, "w"), indent=1)
    print("OK" if not bad else f"{bad} problem(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
