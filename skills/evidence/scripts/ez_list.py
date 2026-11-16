#!/usr/bin/env python3
"""
VA Claims Assistant - VA Form 21-526EZ claim list worksheet (Section V, item 16, and the
Section XIII addendum). Short entries that fit the form's boxes and match the statements.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

  draft --claims F --duties D                 first draft (JSON) from claims.json; Claude edits it
  save  --claims F --list l.json --out <VA-Claim-Output>
        check box lengths and dates, store on claims.json, write Claims/526EZ-Claim-List.docx

Columns (as on the form): CURRENT DISABILITY(IES) / IF DUE TO EXPOSURE, EVENT, OR INJURY,
PLEASE SPECIFY / EXPLAIN HOW THE DISABILITY(IES) RELATES TO THE IN-SERVICE
EVENT/EXPOSURE/INJURY / APPROXIMATE DATE DISABILITY(IES) BEGAN OR WORSENED.
The paper boxes are small; text that runs past them gets cut off. Limits below keep each
entry readable on paper; the online form accepts the same entries.
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "writeups", "scripts"))
from writeups_tools import docx, clean_name  # noqa: E402

LIMITS = {"disability": 45, "cause": 30, "explain": 60}
DATE_RX = re.compile(r"^(0[1-9]|1[0-2])/(19|20)\d\d$|^(19|20)\d\d$")
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()


def mmyyyy(d):
    m = re.match(r"(\d{4})(?:-(\d{1,2}))?", d or "")
    if not m:
        return ""
    return f"{int(m.group(2)):02d}/{m.group(1)}" if m.group(2) else m.group(1)


def draft(C, D):
    names = {c["id"]: clean_name(c["condition"]) for c in C["claims"]}
    labels = {x["id"]: x.get("short") or x.get("label", x["id"]) for x in D.get("duties", [])}
    rows = []
    for c in C["claims"]:
        if c.get("vet_status") != "confirmed":
            continue
        name = clean_name(c["condition"])
        sec = c.get("secondary_to")
        if sec:
            name = re.split(r",\s*caused by", name, flags=re.I)[0] + ", secondary to " + names.get(sec, sec).lower()
        ev = (c.get("story") or {}).get("events", [])
        start = next((e.get("date") for e in ev if e.get("kind") == "start" and e.get("date")), "")
        duties = [labels.get(x, x) for x in (c.get("details") or {}).get("duties", [])][:2]
        rows.append({"id": c["id"], "disability": name.upper(),
                     "cause": "" if sec else ", ".join(duties).lower(),
                     "explain": "", "date": mmyyyy(start)})
    return rows


def check(rows):
    problems = []
    for r in rows:
        for k, n in LIMITS.items():
            if len(r.get(k) or "") > n:
                problems.append(f'{r["id"]} {k}: {len(r[k])} characters; keep to {n}')
        if not r.get("disability"):
            problems.append(f'{r["id"]}: disability is empty')
        if r.get("date") and not DATE_RX.match(r["date"]):
            problems.append(f'{r["id"]} date "{r["date"]}": use MM/YYYY (or YYYY if the month is unknown)')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["draft", "save"])
    for x in ("--claims", "--duties", "--list", "--out"):
        ap.add_argument(x)
    a = ap.parse_args()
    C = json.load(open(a.claims, encoding="utf-8"))
    if a.cmd == "draft":
        D = json.load(open(a.duties, encoding="utf-8")) if a.duties else {}
        print(json.dumps(draft(C, D), indent=1))
        return
    rows = json.load(open(a.list, encoding="utf-8"))
    p = check(rows)
    if p:
        print(json.dumps({"ok": False, "problems": p}, indent=1))
        sys.exit(1)
    C["ez_list"] = rows
    json.dump(C, open(a.claims, "w", encoding="utf-8"), indent=1)
    b = [("h1", "VA Form 21-526EZ: Claim List Worksheet"),
         ("small", "Copy each line into Section V, item 16 (lines 1-15). Use the Section XIII addendum "
                   "page for more than 15. Online, enter the same words. Keep the dates the same as "
                   "in your statements.")]
    for i, r in enumerate(rows, 1):
        b.append(("b", f"{i}. {r['disability']}"))
        if r.get("cause"):
            b.append(("p", "If due to exposure, event, or injury: " + r["cause"]))
        if r.get("explain"):
            b.append(("p", "How it relates to service: " + r["explain"]))
        if r.get("date"):
            b.append(("p", "Approximate date began or worsened: " + r["date"]))
    d = os.path.join(a.out, "Claims")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "526EZ-Claim-List.docx")
    docx(path, b)
    print(json.dumps({"ok": True, "lines": len(rows), "file": path}))


if __name__ == "__main__":
    main()
