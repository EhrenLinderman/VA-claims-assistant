#!/usr/bin/env python3
"""
VA Claims Assistant - VA Form 21-526EZ copy-and-paste guide, section by section.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

  build --out <VA-Claim-Output> [--answers a.json]
        writes Claims/526EZ-Copy-Paste-Guide.docx and .md (item numbers from the Dec 2024 form)

Fills in what the app knows (claim list, service dates, separation date, exposures, filing
window). Private details (SSN, date of birth, address, phone, bank) are NEVER stored or
filled in: the guide says "Type this yourself".

answers JSON (from the button screen in the file skill; all optional):
 {"retiring": "retiring|separating|ides", "separation_place": "Fort Example, TX",
  "deployments": [{"where": "Iraq", "from": "2007", "to": "2008"}], "filed_before": false,
  "component": "Active", "combat_zone": true, "pow": false, "other_names": false,
  "homeless": false, "vso": false}
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "writeups", "scripts"))
from writeups_tools import docx  # noqa: E402

YOURSELF = "Type this yourself (the app never stores it)."
DISCLAIMER = ("Not legal advice. Not affiliated with or endorsed by VA. AI can make mistakes: check everything "
              "against your records before filing.")
GULF = {"southwest_asia", "iraq", "afghanistan", "kuwait", "gulf"}


def mdy(iso):
    try:
        d = date.fromisoformat(iso)
        return d.strftime("%m-%d-%Y")
    except (TypeError, ValueError):
        return iso or ""


def early_service(C, I):
    """In-service evidence dated before the entry date (for example, service academy cadet time)."""
    start = (I.get("service_start") or "")[:7]
    early = sorted(e["date"] for c in C["claims"] if c.get("vet_status") == "confirmed"
                   for e in c.get("evidence", []) if e.get("role") == "in_service" and e.get("date")
                   and e["date"][:7] < start)
    if not start or not early:
        return []
    return [("20D. Additional periods of service",
             f"Add your earlier service (records show in-service care from {early[0][:7]}, before {start})",
             "Service academy cadet time counts as active duty for VA. List the academy entry and graduation "
             "dates here so in-service injuries from that time are counted.")]


def build(out, A):
    C = json.load(open(os.path.join(out, "Claims", "claims.json"), encoding="utf-8"))
    I = json.load(open(os.path.join(out, "intake.json"), encoding="utf-8"))
    fw = I.get("filing_window") or {}
    bdd = fw.get("window") == "bdd"
    sep = I.get("separation_date")
    deps = A.get("deployments") or []
    gulf = any(x in GULF for x in I.get("exposure_locations") or [])
    S = []  # (section title, [(item, value, note)])

    def sec(title, items):
        S.append((title, items))

    sec("Start: claim type", [
        ("1. Type of claim", "BDD Program Claim" if bdd else "Standard Claim Process",
         "BDD: you are 180 to 90 days from separation. Online, choose the pre-discharge (BDD) option."
         if bdd else "Fully Developed Claim (FDC) is optional: only if you send all your evidence now.")])
    sec("Section I: Your identification", [
        ("2. Name", YOURSELF, ""), ("3. SSN", YOURSELF, ""),
        ("4. Ever filed a claim with VA?", "Yes" if A.get("filed_before") else "No", ""),
        ("5. VA file number", YOURSELF if A.get("filed_before") else "Leave blank (first claim)", ""),
        ("6. Date of birth", YOURSELF, ""), ("7. DoD ID number", YOURSELF, ""),
        ("8. BDD: separation date", mdy(sep) if bdd and sep else "Only for BDD claims", ""),
        ("9-11. Phone, mailing address, email", YOURSELF,
         "Use an address that will still reach you after you separate. Overseas: APO/FPO is fine."),
        ("12. VA employee?", "No (check only if you work for VA)", "")])
    sec("Section II: Change of address", [("13A-13C", "Skip unless your address will change soon", "")])
    sec("Section III: Homeless information", [
        ("14A / 14C", "No" if A.get("homeless") is False else "Answer for yourself",
         "If you are homeless or at risk, say Yes: VA can speed up your claim.")])
    tox = [("15A. Claiming conditions related to toxic exposures?",
            "No", "None of your claims is filed as a toxic-exposure claim. If you add one (for example "
            "chronic rhinitis under the PACT Act), answer Yes and fill 15B-15E.")]
    if gulf:
        when = "; ".join(f'{d.get("where", "")} {d.get("from", "")}-{d.get("to", "")}'.strip() for d in deps) or "see your orders"
        tox.append(("15B. Gulf War hazard locations (only if 15A is Yes)", "Yes. " + when,
                    "The form wants month and year (MM-YYYY); take them from your orders or DD 214 worksheet."))
    others = I.get("other_service_locations") or []
    if others:
        tox.append(("15C/15E. Other places served (only if 15A is Yes)", "; ".join(others), ""))
    sec("Section IV: Exposure information", tox)
    claims = [(r["disability"], r.get("cause", ""), r.get("explain", ""), r.get("date", "")) for r in C.get("ez_list", [])]
    sec("Section V: Claim information", [
        ("16. Current disabilities", f"{len(claims)} conditions, one per line, in the table below",
         "Lines 1-15 on the form; put more on the Section XIII addendum page. Online, add them one at a time."),
        ("17. VA or military treatment after discharge",
         "BDD: list your current military clinic; VA gets your service treatment records." if bdd else
         "List each VA medical center or military clinic, by condition.",
         "If treatment began in 2005 or later, dates are not needed (17B).")])
    comp = A.get("component", "Active")
    combat = A.get("combat_zone")
    sec("Section VI: Service information", [
        ("18A. Served under another name?", "Yes" if A.get("other_names") else "No", ""),
        ("19A / 19B. Branch / component", f'{I.get("branch", "")} / {comp}', ""),
        ("20A. Most recent active service", f'Entry: {I.get("service_start", "")} (add the day) · Exit: {mdy(sep)}', ""),
        ("20B. Place of last or anticipated separation", A.get("separation_place") or "Your installation", ""),
        ("20C. Combat zone since 8-7-2000?",
         ("Yes. " + "; ".join(f'{d.get("from")}-{d.get("to")}' for d in deps)) if combat else "Answer for yourself",
         "Use the dates from your orders (month/day/year)."),
        *early_service(C, I),
        ("21A. Reserves or National Guard?", "No" if comp == "Active" else "Yes", ""),
        ("22A. Activated on federal orders (Reserve/Guard)?", "No" if comp == "Active" else "Answer for yourself", ""),
        ("23A. Prisoner of war?", "No" if A.get("pow") is False else "Answer for yourself", "")])
    r = A.get("retiring")
    pay = [("24A. Receiving military retired pay now?", "No" if r in ("retiring", "ides") else "No", "")]
    if r in ("retiring", "ides"):
        pay += [("24B. Will receive retired pay in the future?", "Yes", ""),
                ("24C. Branch", I.get("branch", ""), ""),
                ("24D. Monthly amount", "Your estimate, if known (or leave blank)", ""),
                ("25. Retired status", "Retired" if r == "retiring" else "Ask your PEBLO: TDRL or PDRL", ""),
                ("26. 'Do NOT pay me VA compensation'", "Leave UNCHECKED",
                 "General information, not financial advice: with 20+ years and a combined VA rating of 50% or "
                 "more, Concurrent Retirement and Disability Pay (CRDP) usually pays both in full. Below 50%, "
                 "VA pay replaces part of the retired pay, and the VA part is tax-free. Confirm with DFAS or a VSO.")]
    else:
        pay.append(("24B. Will receive retired pay in the future?", "No" if r == "separating" else "Answer for yourself", ""))
    pay.append(("27A. Separation pay, severance pay, or lump sum?", "Answer for yourself",
                "If yes, VA may hold back some compensation until it is recouped."))
    sec("Section VII: Service pay", pay)
    sec("Section VIII: Direct deposit", [("29-32. Bank details", YOURSELF, "Never give bank details to anyone helping you, except on VA.gov or the signed form.")])
    sec("Section IX: Certification and signature", [("33A / 33B", "Sign and date (online: check the certification box)", "")])
    if A.get("vso"):
        sec("Section XII: Power of attorney", [("37A / 37B", "Your VSO signs here, if they file for you", "")])
    return S, claims, fw


def as_md(S, claims, fw):
    L = ["# VA Form 21-526EZ: Copy-and-Paste Guide", "",
         "Item numbers follow the paper form (December 2024 version). Online at VA.gov the questions "
         "come in a different order, but the answers are the same.", ""]
    kd = fw.get("key_deadline") or {}
    if kd.get("date"):
        L += [f"**{kd.get('label')}: {kd['date']}.**", ""]
    for title, items in S:
        L += [f"## {title}", ""]
        for item, val, note in items:
            L.append(f"- **{item}:** {val}" + (f"  \n  _{note}_" if note else ""))
        if title.startswith("Section V:"):
            L += ["", "| # | Current disability | If due to exposure/event/injury | How it relates to service | Began or worsened |",
                  "|---|---|---|---|---|"]
            L += [f"| {i} | {a} | {b} | {c} | {d} |" for i, (a, b, c, d) in enumerate(claims, 1)]
        L.append("")
    L += ["> **THIS TOOL IS FREE.** It is unlawful for anyone to charge a fee for preparing an initial VA claim. "
          "Report it: VSAFE.gov or 1-833-38V-SAFE (1-833-388-7233).", ">", "> " + DISCLAIMER, ""]
    return "\n".join(L)


def as_docx(path, S, claims, fw):
    b = [("h1", "VA Form 21-526EZ: Copy-and-Paste Guide"),
         ("small", "Item numbers follow the paper form (December 2024 version). Online at VA.gov the questions "
                   "come in a different order, but the answers are the same.")]
    kd = fw.get("key_deadline") or {}
    if kd.get("date"):
        b.append(("b", f"{kd.get('label')}: {kd['date']}"))
    for title, items in S:
        b.append(("h2", title))
        for item, val, note in items:
            b.append(("b", item))
            b.append(("p", val))
            if note:
                b.append(("small", note))
        if title.startswith("Section V:"):
            for i, (a, c1, c2, d) in enumerate(claims, 1):
                b.append(("b", f"Line {i}: {a}"))
                if c1:
                    b.append(("p", "If due to exposure, event, or injury: " + c1))
                if c2:
                    b.append(("p", "How it relates to service: " + c2))
                if d:
                    b.append(("p", "Began or worsened: " + d))
    b.append(("small", "This guide is free. " + DISCLAIMER))
    docx(path, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--answers")
    a = ap.parse_args()
    A = json.load(open(a.answers, encoding="utf-8")) if a.answers else {}
    S, claims, fw = build(a.out, A)
    base = os.path.join(a.out, "Claims", "526EZ-Copy-Paste-Guide")
    open(base + ".md", "w", encoding="utf-8").write(as_md(S, claims, fw))
    as_docx(base + ".docx", S, claims, fw)
    print(json.dumps({"ok": True, "files": [base + ".docx", base + ".md"], "claims": len(claims)}))


if __name__ == "__main__":
    main()
