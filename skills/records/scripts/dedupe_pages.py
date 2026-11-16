#!/usr/bin/env python3
"""
VA Claims Assistant - find duplicate pages across the records (same page saved in
more than one file). Each page gets a `dup_of` pointer to its canonical copy.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

Exact duplicates: same normalized text. Near duplicates: simhash within
--max-dist bits AND same set of dates (so two different visits with the same
template are NOT merged).

Usage: python3 dedupe_pages.py --pages pages.jsonl --out pages_dedup.jsonl
"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, re
from collections import defaultdict


def prefer(rec):
    # canonical copy preference: split "Part" files over combined files (smaller,
    # easier to cite), then alphabetical, then page number
    f = rec["file"]
    return (0 if "part" in f.lower() else 1, f, rec["page"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-dist", type=int, default=3)
    a = ap.parse_args()
    recs = [json.loads(l) for l in open(a.pages, encoding="utf-8")]
    for i, r in enumerate(recs):
        r["id"] = i
    canon = {}
    # exact
    groups = defaultdict(list)
    for r in recs:
        if r["exact_key"]:
            groups[r["exact_key"]].append(r)
    for g in groups.values():
        g.sort(key=prefer)
        for r in g[1:]:
            canon[r["id"]] = g[0]["id"]
    # near: bucket by 4 x 16-bit bands (pigeonhole for distance <= 3)
    live = [r for r in recs if r["id"] not in canon and int(r["simhash"]) and r["chars"] > 200]
    buckets = defaultdict(list)
    for r in live:
        h = int(r["simhash"])
        for b in range(4):
            buckets[(b, (h >> (16 * b)) & 0xFFFF)].append(r)
    for bl in buckets.values():
        if len(bl) < 2:
            continue
        bl.sort(key=prefer)
        for i, x in enumerate(bl):
            for y in bl[i + 1:]:
                if y["id"] in canon or x["id"] in canon:
                    continue
                if bin(int(x["simhash"]) ^ int(y["simhash"])).count("1") <= a.max_dist and set(x["dates"]) == set(y["dates"]):
                    canon[y["id"]] = x["id"]
    # content-level duplicates: the same page saved in another file with different
    # headers/footers or a different scan (MinHash on 4-word shingles, Jaccard >= 0.8)
    import hashlib as _h
    def shingles(t):
        w = re.sub(r"[^a-z0-9 ]", " ", t.lower()).split()
        return {" ".join(w[i:i + 4]) for i in range(max(0, len(w) - 3))}
    NH = 32
    def mh(sh):
        return [min(int(_h.md5(f"{k}|{x}".encode()).hexdigest()[:12], 16) for x in sh) for k in range(NH)]
    cand = [r for r in recs if r["id"] not in canon and r["chars"] > 400]
    S = {r["id"]: shingles(r["text"]) for r in cand}
    M = {r["id"]: mh(S[r["id"]]) for r in cand if S[r["id"]]}
    bands = defaultdict(list)
    for r in cand:
        if r["id"] in M:
            for b in range(8):
                bands[(b, tuple(M[r["id"]][b * 4:(b + 1) * 4]))].append(r)
    seen = set()
    for bl in bands.values():
        if len(bl) < 2:
            continue
        bl.sort(key=prefer)
        for i, x in enumerate(bl):
            for y in bl[i + 1:]:
                if x["file"] == y["file"] or (x["id"], y["id"]) in seen:
                    continue
                seen.add((x["id"], y["id"]))
                if y["id"] in canon or x["id"] in canon:
                    continue
                A, B = S[x["id"]], S[y["id"]]
                j = len(A & B) / max(1, len(A | B))
                if j >= 0.8:
                    canon[y["id"]] = x["id"]
                    y["dup_reason"] = f"same page in another file (similarity {j:.2f})"
    # resolve chains
    def root(i):
        while i in canon:
            i = canon[i]
        return i
    with open(a.out, "w", encoding="utf-8") as out:
        for r in recs:
            r["dup_of"] = root(r["id"]) if r["id"] in canon else None
            out.write(json.dumps(r) + "\n")
    uniq = sum(1 for r in recs if r["id"] not in canon)
    print(json.dumps({"pages": len(recs), "unique_pages": uniq, "duplicates": len(recs) - uniq}))


if __name__ == "__main__":
    main()
