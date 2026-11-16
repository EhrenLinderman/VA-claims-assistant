#!/usr/bin/env python3
"""
VA Claims Assistant - screen unique record pages for possible conditions and rank
the pages most useful as evidence. Output is a LEAD LIST for Claude/the Veteran to
review; it is not a diagnosis.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

Usage:
  python3 condition_scan.py --pages pages_dedup.jsonl --terms condition-terms.json --out leads.json
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import gzip, argparse, json, re
from collections import defaultdict
from datetime import datetime

DOC_TYPES = [
    ("separation_exam", r"separation health assessment|dd form 2807|dd form 2808|report of medical examination|report of medical history|sha part"),
    ("operative_report", r"operative report|procedure note|op note|arthroscop|postoperative diagnosis|pre-?operative diagnosis"),
    ("imaging", r"\bmri\b|x-?ray|radiograph|impression:|findings:|\bct\b scan|ultrasound"),
    ("profile_duty_limit", r"da form 3349|physical profile|profile:|duty limitation|e-?profile"),
    ("line_of_duty", r"line of duty|da form 2173|lod "),
    ("audiogram", r"dd form 2215|dd form 2216|audiogram|hearing conservation|reference audiogram"),
    ("mental_health", r"behavioral health|psycholog|psychiatr|pcl-5|phq-9|gad-7"),
    ("problem_list", r"problem list|active problems|clinical service:.*confirmation"),
    ("clinic_note", r"subjective|chief complaint|history of present illness|assessment|plan:"),
]
DIAG_CTX = re.compile(r"assessment|diagnos|impression|problem|icd|code:|a/p|\bdx\b", re.I)
DATE_FMTS = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"]


def parse_date(s):
    for f in DATE_FMTS:
        try:
            return datetime.strptime(s.strip(), f).date()
        except ValueError:
            pass
    return None


def page_date(rec):
    ds = [d for d in (parse_date(x) for x in rec["dates"]) if d and 1990 <= d.year <= 2030]
    return min(ds).isoformat() if ds else None  # earliest date on page (approx.)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True)
    ap.add_argument("--terms", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    T = json.load(open(a.terms))
    conds, negs = T["conditions"], T["negations"]
    rx = {k: re.compile("|".join(re.escape(t.lower()) for t in v["terms"])) for k, v in conds.items()}
    leads = {k: {"label": v["label"], "system": v["system"], "dc_hint": v["dc_hint"], "pages": []} for k, v in conds.items()}
    for line in (gzip.open(a.pages, "rt", encoding="utf-8") if a.pages.endswith(".gz") else open(a.pages, encoding="utf-8")):
        r = json.loads(line)
        if r.get("dup_of") is not None:
            continue
        low = r["text"].lower()
        dtype = [n for n, p in DOC_TYPES if re.search(p, low)]
        for k, pat in rx.items():
            pos_hits, neg_hits, diag_hits, snippets = 0, 0, 0, []
            for ln in low.splitlines():
                for m in pat.finditer(ln):
                    pre = ln[max(0, m.start() - 30):m.start()]
                    if any(n in pre for n in negs):
                        neg_hits += 1
                        continue
                    pos_hits += 1
                    if DIAG_CTX.search(ln):
                        diag_hits += 1
                    if len(snippets) < 3:
                        snippets.append(re.sub(r"\s+", " ", ln.strip())[:180])
            if pos_hits:
                score = pos_hits + 4 * diag_hits + 6 * bool(set(dtype) & {"separation_exam", "operative_report", "imaging", "profile_duty_limit", "line_of_duty"})
                leads[k]["pages"].append({"id": r["id"], "file": r["file"], "page": r["page"], "date": page_date(r),
                                          "doc_types": dtype, "hits": pos_hits, "diag_hits": diag_hits,
                                          "negated": neg_hits, "score": score, "snippets": snippets})
    out = {}
    for k, v in leads.items():
        ps = v["pages"]
        if not ps:
            continue
        dated = sorted(p["date"] for p in ps if p["date"])
        out[k] = {**{x: v[x] for x in ("label", "system", "dc_hint")},
                  "page_count": len(ps), "diag_page_count": sum(1 for p in ps if p["diag_hits"]),
                  "first_date": dated[0] if dated else None, "last_date": dated[-1] if dated else None,
                  "top_pages": sorted(ps, key=lambda p: -p["score"])[:15], "all_page_ids": [p["id"] for p in ps]}
    json.dump(out, open(a.out, "w"), indent=1)
    for k, v in sorted(out.items(), key=lambda kv: -kv[1]["diag_page_count"]):
        print(f'{v["diag_page_count"]:4} diag / {v["page_count"]:4} pages  {v["first_date"]} → {v["last_date"]}  {v["label"]}')


if __name__ == "__main__":
    main()
