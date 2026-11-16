#!/usr/bin/env python3
"""
VA Claims Assistant - Claim Summary: the front pages of each claim packet, in titled
sections a rater can scan:
  Statement for Submission / Summary of Medical History with Extracts /
  CFR Aligned Rating Language (with residuals) / Nexus - Service Connection Rationale /
  Functional Impact Statement / Substantial Record (index of the attached records)
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only
(build_packet.py renders it with reportlab).

  verify --claims F --id C01 --summary s.json --pages page-text.jsonl.gz
         check every quote word-for-word against the record page it cites
  save   --claims F --id C01 --summary s.json --pages page-text.jsonl.gz
         verify, then store on the claim (refuses if any quote fails)
  show   --claims F --id C01        print the saved summary as plain text

Summary JSON (Claude drafts it from the claim's facts only):
{
 "claim_type": "Direct" | "Secondary to <condition>" | ...,
 "onset": "plain words",
 "history": [{"period": "Early service injury (2002-2004)",
              "items": [{"file": "...pdf", "page": 25, "label": "Operative note",
                         "quote": "exact words ... more exact words"}]}],
 "rating":   [{"dc": "5257 - Instability", "points": ["what the records/Veteran show"]}],
 "residuals": ["surgical scars ...", "brace use ..."],
 "nexus": {"theory": "Direct service connection", "cfr": "38 CFR 3.303",
           "points": ["In service: ...", "Current diagnosis: ...", "Link: ..."],
           "refs": [{"file": "...", "page": 21}]},
 "impact": ["Work: ...", "Family: ...", "Daily life: ..."],
 "strongest": {"file": "...pdf", "page": 1, "why": "..."}
}
Quotes: short (<= 40 words), exact words from the page; "..." may join two exact pieces.
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, gzip, json, re, sys

MAX_QUOTES = 6
MAX_QUOTE_WORDS = 40


def norm(s):
    s = (s or "").lower().replace("ﬁ", "fi").replace("ﬂ", "fl")
    s = re.sub(r"[‘’“”]", "'", s)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def load_pages(path, wanted):
    f = gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")
    out = {}
    for line in f:
        r = json.loads(line)
        k = (r["file"], int(r["page"]))
        if k in wanted:
            out[k] = norm(r.get("text", ""))
    return out


def quote_ok(quote, page_text):
    """Every piece between ellipses (3+ words) must appear word-for-word on the page."""
    pieces = [norm(p) for p in re.split(r"…|\.\.\.", quote or "")]
    pieces = [p for p in pieces if p]
    if not pieces or any(len(p.split()) < 3 for p in pieces):
        return False, "each quoted piece needs at least 3 words"
    for p in pieces:
        if p not in page_text:
            return False, f'not on the page: "{p[:60]}"'
    return True, ""


def all_refs(S):
    refs = []
    for g in S.get("history", []):
        for it in g.get("items", []):
            refs.append(it)
    refs += S.get("nexus", {}).get("refs", [])
    if S.get("strongest"):
        refs.append(S["strongest"])
    return refs


def verify(S, c, pages_path):
    problems = []
    ev = {(e["file"], int(e["page"])) for e in c.get("evidence", []) if e.get("role") != "contrary"}
    refs = all_refs(S)
    for r in refs:
        if (r["file"], int(r["page"])) not in ev:
            problems.append(f'{r["file"]} p.{r["page"]} is not one of this claim\'s packet pages')
    quotes = [it for g in S.get("history", []) for it in g.get("items", []) if it.get("quote")]
    if len(quotes) > MAX_QUOTES:
        problems.append(f"{len(quotes)} quotes; keep it to {MAX_QUOTES} or fewer")
    text = load_pages(pages_path, {(q["file"], int(q["page"])) for q in quotes})
    for q in quotes:
        if len(q["quote"].split()) > MAX_QUOTE_WORDS:
            problems.append(f'quote on {q["file"]} p.{q["page"]} is over {MAX_QUOTE_WORDS} words')
        ok, why = quote_ok(q["quote"], text.get((q["file"], int(q["page"])), ""))
        if not ok:
            problems.append(f'{q["file"]} p.{q["page"]}: {why}')
    for k in ("rating", "nexus", "impact"):
        if not S.get(k):
            problems.append(f"missing section: {k}")
    return problems


def statement_text(out_dir, c):
    """The saved statement, without the certification lines (they stay on the signed copy)."""
    import os
    folder = (c.get("writeup") or {}).get("folder")
    if not folder:
        return ""
    p = os.path.join(out_dir, folder, "Statement.txt")
    if not os.path.exists(p):
        return ""
    t = open(p, encoding="utf-8").read()
    return t.split("I certify that")[0].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["verify", "save", "show"])
    for x in ("--claims", "--id", "--summary", "--pages"):
        ap.add_argument(x)
    a = ap.parse_args()
    C = json.load(open(a.claims, encoding="utf-8"))
    c = next((x for x in C["claims"] if x["id"] == a.id), None)
    if not c:
        sys.exit(f"no claim {a.id}")
    if a.cmd == "show":
        S = c.get("summary")
        print(json.dumps(S, indent=1) if S else "No summary saved yet.")
        return
    S = json.load(open(a.summary, encoding="utf-8"))
    problems = verify(S, c, a.pages)
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=1))
        sys.exit(1)
    if a.cmd == "save":
        from datetime import date
        S["saved"] = date.today().isoformat()
        c["summary"] = S
        json.dump(C, open(a.claims, "w", encoding="utf-8"), indent=1)
    print(json.dumps({"ok": True, "quotes": sum(1 for g in S["history"] for i in g["items"] if i.get("quote"))}))


if __name__ == "__main__":
    main()
