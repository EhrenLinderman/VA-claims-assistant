#!/usr/bin/env python3
"""
VA Claims Assistant - helpers for the "Review possible claims" step.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only
(page-image rendering needs poppler's pdftoppm).

Subcommands (all read/write VA-Claim-Output/Claims/claims.json):
  summary   --claims F                         one-line-per-claim list (JSON) for the quick check screen
  set       --claims F --id C13 --status confirmed|removed|pending [--reason TEXT]
  explain   --claims F --id C13 --file X --page N --why mistake|misunderstood|correct [--note TEXT]
  search    --pages page-text.jsonl.gz --terms "tinnitus|ringing" [--positive]   find the Veteran's own reports
  addev     --claims F --id C13 --file X --page N --role lay --shows TEXT [--date D]
  add       --claims F --condition TEXT [--note TEXT]   a condition the Veteran says was missed
  render    --records DIR --file X --page N --out P.png   page image, to read checkboxes by eye
"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, gzip, json, os, re, subprocess, sys
from datetime import date

ONE_LINE = {  # plain-language "why" built from the evidence roles
    "in_service": "in-service record", "diagnosis": "current diagnosis", "nexus": "doctor's link to service",
}


def load(p):
    return json.load(open(p, encoding="utf-8"))


def save(p, d):
    d["updated"] = date.today().isoformat()
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1)


def find(C, cid):
    for c in C["claims"]:
        if c["id"] == cid:
            return c
    sys.exit(f"no claim {cid}")


def open_pages(p):
    op = gzip.open if p.endswith(".gz") else open
    with op(p, "rt", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    for a in ("--claims", "--id", "--status", "--reason", "--file", "--why", "--note", "--pages", "--terms",
              "--role", "--shows", "--date", "--condition", "--records", "--out"):
        ap.add_argument(a)
    ap.add_argument("--page", type=int)
    ap.add_argument("--positive", action="store_true")
    a = ap.parse_args()

    if a.cmd == "summary":
        C = load(a.claims)
        out = []
        for c in C["claims"]:
            roles = {e["role"] for e in c["evidence"]}
            have = [ONE_LINE[r] for r in ("in_service", "diagnosis", "nexus") if r in roles]
            contrary = [{"file": e["file"], "page": e["page"], "shows": e["shows"], "explained": e.get("vet_explanation")}
                        for e in c["evidence"] if e["role"] == "contrary"]
            out.append({"id": c["id"], "condition": c["condition"], "type": c["type"], "strength": c["strength"],
                        "why": ", ".join(have) or "needs more evidence", "status": c.get("vet_status", "pending"),
                        "contrary": contrary})
        print(json.dumps({"claims": out, "not_recommended": [x["condition"] for x in C.get("not_recommended", [])],
                          "possible_additional": [x["condition"] for x in C.get("possible_additional", [])]}, indent=1))

    elif a.cmd == "guard":
        # Before removing or merging a claim: does it stand on its own? (answer-key lesson: a merged
        # shoulder claim with its own diagnosis and VA exam was later granted 20% + 20% by VA)
        C = load(a.claims); c = find(C, a.id)
        own = [e for e in c.get("evidence", []) if e.get("role") in ("diagnosis", "severity")]
        exam = [e for e in own if re.search(r"DBQ|VA .{0,20}exam|Separation Health|SHA", e.get("shows") or "", re.I)]
        sides = sorted(set(re.findall(r"\b(left|right|both|bilateral)\b", (c["condition"] + " " +
                       " ".join(e.get("shows") or "" for e in own)).lower())))
        level = "stop" if exam else ("warn" if own else "ok")
        msg = {"stop": "VA diagnosed or examined this on its own. Merging or removing it can drop a rating VA would give.",
               "warn": "Your records show a diagnosis for this on its own. Keep it unless it truly is the same condition.",
               "ok": "No separate diagnosis or exam found. Merging is low risk."}[level]
        print(json.dumps({"id": a.id, "level": level, "message": msg, "sides": sides,
                          "own_pages": [{"file": e["file"], "page": e["page"], "shows": e.get("shows")} for e in own]}, indent=1))

    elif a.cmd == "set":
        C = load(a.claims); c = find(C, a.id)
        c["vet_status"] = a.status
        if a.reason:
            c["vet_reason"] = a.reason
        save(a.claims, C); print(f"{a.id} -> {a.status}")

    elif a.cmd == "explain":
        C = load(a.claims); c = find(C, a.id)
        for e in c["evidence"]:
            if e["file"] == a.file and e["page"] == a.page:
                e["vet_explanation"] = {"why": a.why, "note": a.note or "", "date": date.today().isoformat()}
                if a.why in ("mistake", "misunderstood"):
                    c.setdefault("statement_points", []).append(
                        f'Explain the record on {os.path.splitext(a.file)[0]} p.{a.page}: '
                        + ("it is a mistake" if a.why == "mistake" else "I didn't understand the question at the time")
                        + (f" ({a.note})" if a.note else "") + ".")
                save(a.claims, C); print("saved"); return
        sys.exit("that page is not cited on this claim")

    elif a.cmd == "search":
        rx = re.compile(a.terms, re.I)
        neg = re.compile(r"(denie[sd]|no\b|not\b|negative|without)\W{0,3}(\w+\W+){0,3}$", re.I)
        hits = []
        for p in open_pages(a.pages):
            if p.get("dup_of") is not None:
                continue
            t = re.sub(r"\s+", " ", p["text"])
            for m in rx.finditer(t):
                pre = t[max(0, m.start() - 40):m.start()]
                is_neg = bool(neg.search(pre))
                if a.positive and is_neg:
                    continue
                hits.append({"file": p["file"], "page": p["page"], "negated_nearby": is_neg,
                             "context": t[max(0, m.start() - 160):m.end() + 200]})
                break
        print(json.dumps(hits[:60], indent=1))
        print(f"# {len(hits)} page(s). Checkbox answers can't be read from text: render the page and look.", file=sys.stderr)

    elif a.cmd == "addev":
        C = load(a.claims); c = find(C, a.id)
        c["evidence"].append({"file": a.file, "page": a.page, "role": a.role or "lay", "date": a.date or "",
                              "shows": a.shows, "added_in_review": True})
        save(a.claims, C); print("added")

    elif a.cmd == "add":
        C = load(a.claims)
        n = 1 + max(int(c["id"][1:]) for c in C["claims"])
        C["claims"].append({"id": f"C{n:02d}", "condition": a.condition, "type": "to_be_determined", "system": "",
                            "dc": [], "strength": "needs_more", "lead_keys": [], "elements":
                            {"diagnosis": "missing", "in_service": "missing", "nexus": "missing"},
                            "evidence": [], "questions_for_vet": [], "flags": ["Added by the Veteran in review. Search records next."],
                            "vet_status": "confirmed", "vet_note": a.note or ""})
        save(a.claims, C); print(f"C{n:02d} added")

    elif a.cmd == "render":
        pdf = os.path.join(a.records, a.file)
        base = os.path.splitext(a.out)[0]
        subprocess.run(["pdftoppm", "-f", str(a.page), "-l", str(a.page), "-r", "110", "-png", "-singlefile", pdf, base], check=True)
        print(base + ".png")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
