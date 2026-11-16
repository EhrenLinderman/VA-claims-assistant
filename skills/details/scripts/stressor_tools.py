#!/usr/bin/env python3
"""
VA Claims Assistant - mental health stressor details and a VA Form 21-0781 worksheet.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

VA Form 21-0781 (revision March 2024) replaced the old 21-0781a. If the Veteran files the
526EZ ONLINE, the online claim asks these same questions and a separate 21-0781 is not
needed; the worksheet then serves as answers ready to copy in. A PDF 21-0781 is needed with
a PDF 526EZ, or when VA asks for one.

  options                                         the button choices (event types, changes, sources)
  save      --claims F --id C10 --data s.json     check and store the stressor details on the claim
  worksheet --claims F --id C10 --out <VA-Claim-Output>
            writes Claims/<id-name>/Form-21-0781-Worksheet.docx (answers laid out by form section)

Stressor JSON:
{"events": [{"type": "combat", "what": "IED strike on our convoy", "where": "near <town>, Iraq",
             "when": "2007-09" or "about Sep 2007", "unit": "<company, battalion>",
             "hurt": "two soldiers wounded"  (optional), "pages": [{"file": "...", "page": 3}]}],
 "behavior_changes": ["Depression, panic attacks, or anxiety", ...], "changes_detail": "...",
 "official_report": "yes" | "no" | "n/a", "sources": ["Fellow service members", ...],
 "treatment": "counseling since early 2025 at ...", "vet_ok_to_share": true}
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "writeups", "scripts"))
from writeups_tools import docx, claim_dir  # noqa: E402

EVENT_TYPES = {
    "combat": "Combat",
    "personal": "Personal traumatic event (not MST), such as assault, robbery, or domestic abuse",
    "mst": "Military sexual trauma (MST)",
    "other": "Other, such as an accident, disaster, or witnessing a death or injury",
}
BEHAVIOR_CHANGES = [
    "More or fewer visits to a doctor, counselor, or clinic",
    "Asked for a different job or duty assignment",
    "More or less leave used",
    "Changes in performance or evaluations",
    "Depression, panic attacks, or anxiety",
    "Started or changed medication",
    "More alcohol or drug use",
    "Disciplinary or legal trouble",
    "Changes in eating habits or weight",
    "Pregnancy or STI tests",
    "Money or social changes",
    "A relationship changed or ended",
]
SOURCES = [
    "Rape crisis center or domestic abuse center",
    "Chaplain or clergy",
    "Counseling facility or health clinic",
    "Fellow service members",
    "Family members or roommates",
    "Personal diaries or journals",
    "Faculty member",
    "Civilian police reports",
]


def check(S):
    problems = []
    ev = S.get("events") or []
    if not ev:
        problems.append("no events; at least one event is needed (or skip the worksheet)")
    for i, e in enumerate(ev, 1):
        if e.get("type") not in EVENT_TYPES:
            problems.append(f"event {i}: type must be one of {list(EVENT_TYPES)}")
        for k in ("what", "where", "when"):
            if not (e.get(k) or "").strip():
                problems.append(f"event {i}: '{k}' is empty (use 'not sure' if the Veteran doesn't know)")
        if len((e.get("what") or "").split()) > 60:
            problems.append(f"event {i}: keep 'what' brief (60 words or fewer); the form asks for a brief description")
    for x in S.get("behavior_changes", []):
        if x not in BEHAVIOR_CHANGES:
            problems.append(f"unknown behavior change: {x}")
    return problems


def worksheet(out, c, S):
    d = claim_dir(out, c)
    b = [("h1", "VA Form 21-0781 Worksheet"),
         ("small", "Your answers, laid out in the order of VA Form 21-0781 (Statement in Support of Claimed "
                   "Mental Health Disorder(s) Due to an In-Service Traumatic Event(s)). If you file your claim "
                   "online, the online claim asks these same questions: copy your answers in. If you file on "
                   "paper, copy them onto the current PDF form from VA.gov."),
         ("h2", "Section I: Your identification"),
         ("p", "Fill in on the form: name, SSN or VA file number, date of birth, phone, email."),
         ("h2", "Section II: Traumatic event(s)")]
    types = sorted({EVENT_TYPES[e["type"]] for e in S["events"]})
    b.append(("b", "Check these event type box(es): " + "; ".join(types)))
    for i, e in enumerate(S["events"], 1):
        b.append(("b", f"Event {i}"))
        b.append(("p", "Brief description: " + e["what"].strip()))
        b.append(("p", "Location: " + e["where"].strip()))
        b.append(("p", "Date(s): " + e["when"].strip()))
        if e.get("unit"):
            b.append(("p", "Unit at the time: " + e["unit"].strip()))
        if e.get("hurt"):
            b.append(("p", "Others hurt or killed: " + e["hurt"].strip()))
    b.append(("small", "Tip: a month and year (within about 60 days) and your unit help VA find "
                       "unit records. For combat events, your own statement can be enough when it fits "
                       "the places and conditions of your service."))
    b.append(("h2", "Section III: Behavior changes after the event(s)"))
    if S.get("behavior_changes"):
        for x in S["behavior_changes"]:
            b.append(("p", "[X] " + x))
    else:
        b.append(("p", "None checked."))
    if S.get("changes_detail"):
        b.append(("p", "More details: " + S["changes_detail"]))
    b.append(("h2", "Section IV: Reports and other evidence"))
    rep = {"yes": "Yes", "no": "No", "n/a": "Not applicable"}.get(S.get("official_report", ""), "")
    if rep:
        b.append(("p", "Was an official report filed? " + rep))
    if S.get("sources"):
        b.append(("p", "Possible sources of evidence: " + "; ".join(S["sources"])))
    if S.get("treatment"):
        b.append(("p", "Treatment: " + S["treatment"]))
    b.append(("h2", "Remaining sections"))
    b.append(("p", "Remarks (optional), the VHA notification choice, and your signature and date go on the "
                   "form itself. If a representative (VSO or attorney) files for you, they sign the POA section."))
    path = os.path.join(d, "Form-21-0781-Worksheet.docx")
    docx(path, b)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["options", "save", "worksheet"])
    for x in ("--claims", "--id", "--data", "--out"):
        ap.add_argument(x)
    a = ap.parse_args()
    if a.cmd == "options":
        print(json.dumps({"event_types": EVENT_TYPES, "behavior_changes": BEHAVIOR_CHANGES, "sources": SOURCES}, indent=1))
        return
    C = json.load(open(a.claims, encoding="utf-8"))
    c = next((x for x in C["claims"] if x["id"] == a.id), None)
    if not c:
        sys.exit(f"no claim {a.id}")
    if a.cmd == "save":
        S = json.load(open(a.data, encoding="utf-8"))
        p = check(S)
        if p:
            print(json.dumps({"ok": False, "problems": p}, indent=1))
            sys.exit(1)
        S["saved"] = date.today().isoformat()
        c["stressors"] = S
        json.dump(C, open(a.claims, "w", encoding="utf-8"), indent=1)
        print(json.dumps({"ok": True, "events": len(S["events"])}))
    else:
        S = c.get("stressors")
        if not S:
            sys.exit("no stressor details saved for this claim")
        print(worksheet(a.out, c, S))


if __name__ == "__main__":
    main()
