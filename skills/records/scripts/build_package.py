#!/usr/bin/env python3
"""
VA Claims Assistant - turn the reviewed claim list (claims.json) plus the page
index into the Veteran's working files:
  Evidence/evidence-index.csv   every page: kept or duplicate, date, type, conditions, earmarks
  Possible-Claims.md            plain-language list of possible claims for the Veteran to review
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

Usage:
  python3 build_package.py --pages pages_dedup.jsonl --leads leads.json --claims claims.json --out <VA-Claim-Output>
"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import gzip, argparse, csv, json, os, re
from collections import defaultdict

STRENGTH = {"strong": "🟢 Strong", "moderate": "🟡 Moderate", "needs_more": "🟠 Needs more evidence"}
ELEM = {"found": "✅ Found", "partial": "🟡 Partial", "missing": "❌ Missing"}
TYPE = {"direct": "Direct (happened in service)", "secondary": "Secondary (caused by another service-connected condition)",
        "presumptive": "Presumptive (automatic link by law)", "aggravation": "Aggravation (made worse by service)"}
ROLE = {"diagnosis": "Current diagnosis", "in_service": "In-service event", "nexus": "Link to service",
        "severity": "How bad it is", "lay": "Your own statement", "contrary": "⚠ Works against the claim"}
DATE_RX = re.compile(r"\b(19|20)\d{2}\b")


def short(f):
    return os.path.splitext(f)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True)
    ap.add_argument("--leads", required=True)
    ap.add_argument("--claims", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pages = [json.loads(l) for l in (gzip.open(a.pages, "rt", encoding="utf-8") if a.pages.endswith(".gz") else open(a.pages, encoding="utf-8"))]
    byid = {p["id"]: p for p in pages}
    leads = json.load(open(a.leads))
    C = json.load(open(a.claims))
    os.makedirs(os.path.join(a.out, "Evidence"), exist_ok=True)

    tags = defaultdict(set)
    for k, v in leads.items():
        for pid in v["all_page_ids"]:
            tags[pid].add(v["label"])
    earmark = defaultdict(list)
    support = defaultdict(set)
    key = {(p["file"], p["page"]): p["id"] for p in pages}
    for c in C["claims"]:
        for e in c["evidence"]:
            pid = key.get((e["file"], e["page"]))
            if pid is not None:
                earmark[pid].append(f'{c["id"]}:{e["role"]}')
        for lk in c.get("lead_keys", []):
            for pid in leads.get(lk, {}).get("all_page_ids", []):
                support[c["id"]].add(pid)

    with open(os.path.join(a.out, "Evidence", "evidence-index.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "page", "status", "duplicate_of", "dates_on_page", "possible_conditions", "earmarked_for_claims"])
        for p in pages:
            d = byid[p["dup_of"]] if p["dup_of"] is not None else None
            w.writerow([p["file"], p["page"], "duplicate" if d else "kept",
                        f'{d["file"]} p{d["page"]}' if d else "",
                        "; ".join(p["dates"][:6]), "; ".join(sorted(tags.get(p["id"], []))),
                        "; ".join(earmark.get(p["id"], []))])

    n_pages = len(pages)
    n_kept = sum(1 for p in pages if p["dup_of"] is None)
    L = []
    L += ["# Your Possible VA Claims", "",
          "> **⚠ THIS TOOL IS FREE.** No one should charge you to use it. Report fees: VSAFE.gov or 1-833-38V-SAFE (1-833-388-7233).",
          "> Not legal advice. Not affiliated with or endorsed by VA. AI can make mistakes: check everything against your records before filing.",
          "", f"*Made by VA Claims Assistant on {C['generated']}. This is a working list for you to review. It is **not** a VA decision and not something to file as-is.*", "",
          "## What the app read", "",
          f"- **{n_pages:,} pages** in {len({p['file'] for p in pages})} files from your records folder.",
          f"- **{n_pages - n_kept:,} pages were copies** of pages in other files. Each page is counted once, and each condition appears as **one** claim, no matter how many records mention it.",
          f"- **{n_kept:,} unique pages** were checked for conditions.", ""]
    if C.get("service_facts"):
        L += ["## Service facts the app found", ""]
        for s in C["service_facts"]:
            L.append(f"- {s['fact']} *(" + "; ".join(f"{short(f)} p.{p}" for f, p in s["cite"]) + ")*")
        L.append("")
    L += ["## Possible claims", "",
          "| # | Condition | Type | Strength | Key pages |", "|---|---|---|---|---|"]
    for c in C["claims"]:
        L.append(f'| {c["id"]} | {c["condition"]} | {TYPE.get(c["type"], c["type"])}'
                 f'{" → " + c["secondary_to"] if c.get("secondary_to") else ""} | {STRENGTH.get(c["strength"], c["strength"])} | {len(c["evidence"])} |')
    L.append("")
    for c in C["claims"]:
        L += [f'### {c["id"]}. {c["condition"]}', "",
              f'**Type:** {TYPE.get(c["type"], c["type"])}{" (to " + c["secondary_to"] + ")" if c.get("secondary_to") else ""}  ',
              f'**VA rating code(s):** {", ".join(c["dc"])}  ',
              f'**Strength:** {STRENGTH.get(c["strength"], c["strength"])}', "",
              "| The 3 things VA needs | Status |", "|---|---|",
              f'| 1. A current diagnosis | {ELEM.get(c["elements"]["diagnosis"], c["elements"]["diagnosis"])} |',
              f'| 2. Something that happened in service | {ELEM.get(c["elements"]["in_service"], c["elements"]["in_service"])} |',
              f'| 3. A link between them | {ELEM.get(c["elements"]["nexus"], c["elements"]["nexus"])} |', ""]
        if c.get("separate_parts"):
            L += ["**Parts VA may rate separately** (one claim, more than one rating when the symptoms are different, per 38 CFR 4.14):", ""]
            for sp in c["separate_parts"]:
                L.append(f'- **{sp["part"]}** (DC {sp["dc"]}): {sp["note"]}')
            L.append("")
        L += ["**Key evidence (earmarked for your claim packet):**", "", "| Role | Record | Page | Date | What it shows |", "|---|---|---|---|---|"]
        for e in c["evidence"]:
            also = f' (also in {short(e["also_in"][0]["file"])} p.{e["also_in"][0]["page"]})' if e.get("also_in") else ""
            L.append(f'| {ROLE.get(e["role"], e["role"])} | {short(e["file"])} | {e["page"]}{also} | {e.get("date", "")} | {e["shows"]} |')
        L.append("")
        more = len(support.get(c["id"], set()) - {key.get((e["file"], e["page"])) for e in c["evidence"]})
        if more:
            L += [f"*{more} other pages also mention this condition. They're listed in the evidence index and will be checked when the evidence packet is built.*", ""]
        if c.get("flags"):
            L += ["**Notes:**", ""] + [f"- {x}" for x in c["flags"]] + [""]
        if c.get("questions_for_vet"):
            L += ["**Questions for you:**", ""] + [f"- {x}" for x in c["questions_for_vet"]] + [""]
    if C.get("possible_additional"):
        L += ["## Worth checking with a doctor", ""]
        for x in C["possible_additional"]:
            L.append(f'- **{x["condition"]}:** {x["reason"]} *(' + "; ".join(f"{short(f)} p.{p}" for f, p in x["cite"]) + ")*")
        L.append("")
    if C.get("not_recommended"):
        L += ["## Found in your records, but not recommended right now", ""]
        for x in C["not_recommended"]:
            L.append(f'- **{x["condition"]}:** {x["reason"]} *(' + "; ".join(f"{short(f)} p.{p}" for f, p in x["cite"]) + ")*")
        L.append("")
    if C.get("record_flags"):
        L += ["## Things to check in your records", ""] + [f"- {x}" for x in C["record_flags"]] + [""]
    L += ["---", "Created by EhrenAL · Free for non-commercial use (CC BY-NC-SA 4.0)"]
    with open(os.path.join(a.out, "Possible-Claims.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(json.dumps({"claims": len(C["claims"]), "pages": n_pages, "kept": n_kept}))


if __name__ == "__main__":
    main()
