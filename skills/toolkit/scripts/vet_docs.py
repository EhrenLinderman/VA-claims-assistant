#!/usr/bin/env python3
"""
VA Claims Assistant - the Veteran's toolkit documents:
  exam   --claims F --id C01 --out <VA-Claim-Output>    Claims/<id-name>/Exam-Prep.docx (what VA measures,
                                                         what to tell the examiner, what to bring)
  log    --claims F --id C01 --out <VA-Claim-Output> [--kind auto|headache|flare|sleep|mental|general] [--weeks 8]
                                                         Claims/<id-name>/Symptom-Log.docx (printable, signable)
  buddy  --claims F --id C01 --out <VA-Claim-Output>    Claims/<id-name>/Buddy-Statement-Guide.docx (guide + witness form)
  vso    --claims F --intake I --out <VA-Claim-Output>  VSO-Handoff/ folder + VSO-Handoff.zip (copies; originals untouched)
  family --claims F --id C01                             which exam family the claim falls in
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

Symptom logs and witness forms may be filed with VA, so they carry no app notices or markers.
The Veteran's and witness's names are never stored: forms have blanks to fill in by hand.
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, re, shutil, sys, zipfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "writeups", "scripts"))
from writeups_tools import docx, claim_dir, clean_name, CERT, PENALTY, letter_level  # noqa: E402

GUIDE = os.path.join(HERE, "..", "references", "exam-guide.json")
NOT_ADVICE = ("Not legal or medical advice. Not affiliated with or endorsed by VA. Be honest and specific; "
              "describe your typical and your bad days.")
LOGS = {
    "headache": ("Headache Log", ["Date", "Start time", "How long", "Pain 0-10", "Had to stop and lie down? (Y/N)",
                                  "Medicine taken", "Missed or left work? (Y/N)", "Notes"]),
    "flare": ("Flare-Up Log", ["Date", "Body part", "How long", "Pain 0-10", "What set it off",
                               "What I couldn't do", "Brace / medicine / rest", "Missed or left work? (Y/N)"]),
    "sleep": ("Sleep Log", ["Date", "Hours slept", "Times woke up", "Nightmares? (Y/N)", "Breathing machine used? (Y/N)",
                            "Dozed off in the day? (Y/N)", "Notes"]),
    "mental": ("Symptom Log", ["Date", "Symptoms (nightmares, panic, anger, low mood...)", "How long / how bad 0-10",
                               "What set it off", "Effect on work", "Effect on family / others", "Notes"]),
    "general": ("Symptom Log", ["Date", "Symptoms", "How long", "Severity 0-10", "Medicine / treatment",
                                "What I couldn't do", "Notes"]),
}
FAMILY_LOG = {"joint": "flare", "spine": "flare", "muscle": "flare", "nerve": "flare", "headache": "headache",
              "apnea": "sleep", "mental": "mental", "tbi": "mental"}


def title(c):
    return re.split(r"\s*[(:,]", c["condition"])[0].strip()


def load(p):
    return json.load(open(p, encoding="utf-8"))


def find(C, cid):
    for c in C["claims"]:
        if c["id"] == cid:
            return c
    sys.exit(f"no claim {cid}")


def family(c, G):
    codes = [int(x) for d in (c.get("dc") or []) for x in re.findall(r"\b(\d{4})\b", d)]
    for key, f in G["families"].items():
        if any(lo <= code <= hi for code in codes for lo, hi in f["dc"]):
            return key
    name = c["condition"].lower()
    for key, f in G["families"].items():
        if any(w in name for w in f["words"]):
            return key
    return "general"


def my_facts(c):
    """Short reminders from the Veteran's own saved answers (never invented)."""
    d = c.get("details") or {}
    out = []
    for k, v in (d.get("answers") or {}).items():
        v = "; ".join(v) if isinstance(v, list) else str(v)
        if v and not re.search(r"^(none|no|not sure|skip)", v, re.I):
            out.append(f"{k}: {v}")
    imp = d.get("impact") or {}
    for k in ("work", "relationships", "daily"):
        if imp.get(k):
            out.append(f"Impact on {k if k != 'relationships' else 'family and friends'}: " + "; ".join(imp[k]))
    if imp.get("example"):
        out.append("My example: " + imp["example"])
    return out[:10]


def exam(out, c, G):
    fk = family(c, G)
    f, a = G["families"][fk], G["all"]
    name = title(c)
    b = [("h1", f"Exam Prep: {name}"),
         ("small", "For you to read before your VA exam (C&P exam). You don't file this sheet. " + NOT_ADVICE),
         ("h2", "What the examiner will check"), ("p", f["measured"]),
         ("h2", "Tell the examiner")]
    b += [("check", t) for t in f["tell"]]
    if f.get("extra"):
        b += [("p", t) for t in f["extra"]]
    facts = my_facts(c)
    if facts:
        b.append(("h2", "What you told the app (your own words, to remember)"))
        b += [("p", "• " + t) for t in facts]
    st = c.get("story") or {}
    ev = [e for e in st.get("events", []) if e.get("date")][:8]
    if ev:
        b.append(("h2", "Key dates (from your records and your answers)"))
        b += [("p", f"• {e['date']}: {e.get('what', '')}") for e in ev]
    flags = (c.get("details") or {}).get("notes")
    if flags and re.search(r"exam", flags, re.I):
        b += [("h2", "From your last VA exam"),
              ("p", "Your answers differed from a past VA exam on this condition. Describe your symptoms "
                    "clearly so this exam records them accurately.")]
    b += [("h2", "Before the exam")] + [("check", t) for t in a["before"]]
    b += [("h2", "Bring")] + [("check", t) for t in a["bring"]]
    b += [("h2", "During the exam")] + [("p", "• " + t) for t in a["during"]]
    b += [("h2", "After the exam")] + [("p", "• " + t) for t in a["after"]]
    b += [("h2", "My notes after the exam"), ("table", [[""]] * 6, {"header": False, "height": 500})]
    path = os.path.join(claim_dir(out, c), "Exam-Prep.docx")
    docx(path, b)
    return path


def log(out, c, G, kind="auto", weeks=8):
    if kind == "auto":
        kind = FAMILY_LOG.get(family(c, G), "general")
    log_title, cols = LOGS[kind]
    name = title(c)
    b = [("h1", f"{log_title}: {name}"),
         ("p", "Name: ______________________________    Start date: ______________"),
         ("small", "Fill in one line each time it happens (or each day). Write what really happened, in your own "
                   "words. A log kept over weeks shows how often and how badly symptoms affect you.")]
    n = len(cols)
    first = 1800 if n > 6 else 1600
    rest = int((10080 - first) / (n - 1))
    rows = [cols] + [[""] * n for _ in range(weeks * 7 if kind in ("sleep",) else weeks * 4)]
    b.append(("table", rows, {"widths": [first] + [rest] * (n - 1), "height": 420}))
    b += [("p", CERT), ("p", PENALTY), ("line", "Signature: ______________________________    Date: ______________")]
    path = os.path.join(claim_dir(out, c), "Symptom-Log.docx")
    docx(path, b)
    return path, kind


def buddy(out, c, G):
    name = title(c)
    st = c.get("story") or {}
    service_ev = [e for e in st.get("events", []) if e.get("kind") in ("start", "worse") and e.get("date")][:4]
    b = [("h1", f"Buddy Statement Guide: {name}"),
         ("small", "Part 1 is for you. Part 2 is the form your witness fills in and signs. " + NOT_ADVICE),
         ("h2", "Part 1: Who to ask and how it works"),
         ("p", "A buddy statement (lay statement) is a witness's own description of what they saw. It can help "
               "show that something happened in service, or how a condition affects you now."),
         ("b", "Good witnesses"),
         ("p", "• Someone who served with you and saw the injury or event, or saw you struggle with it afterward."),
         ("p", "• Someone who sees you now: a spouse, family member, roommate, coworker or supervisor."),
         ("b", "What they need to know"),
         ("p", "• They write only what they saw or know themselves, in their own words. Don't write it for them."),
         ("p", "• Dates and places help, even if approximate ('spring 2007, Fort Benning')."),
         ("p", "• They file it on VA Form 21-10210 (Lay/Witness Statement), online at VA.gov or on the PDF. "
               "Or they fill in Part 2 below, sign it, and give it to you to upload with your claim."),
         ("p", "• They should include a phone number or email so VA can reach them if needed.")]
    if service_ev:
        b.append(("b", "Events a fellow service member might have seen (from your records and answers)"))
        b += [("p", f"• {e['date']}: {e.get('what', '')}" + (f" ({e['where']})" if e.get("where") else ""))
              for e in service_ev]
    b += [("pagebreak", ""),
          ("h1", "Statement in Support of Claim (Witness)"),
          ("p", "Veteran's name: ______________________________    Veteran's VA file number or SSN (last 4): ________"),
          ("p", f"Condition this statement is about: {name}"),
          ("h2", "About me (the witness)"),
          ("p", "My name: ______________________________    Phone or email: ______________________________"),
          ("p", "How I know the Veteran, and for how long: ______________________________________________"),
          ("p", "If we served together: unit, place and dates: _________________________________________"),
          ("h2", "What I saw myself"),
          ("small", "Describe what happened, when and where, and what you saw the Veteran do or go through. "
                    "Write only what you saw or know yourself."),
          ("table", [[""]] * 10, {"header": False, "height": 480}),
          ("h2", "Changes I have seen since then"),
          ("small", "For example: things the Veteran can no longer do, how often symptoms happen, effects on work, "
                    "family, sleep or daily life. Give examples."),
          ("table", [[""]] * 8, {"header": False, "height": 480}),
          ("p", CERT), ("p", PENALTY),
          ("line", "Witness signature: ______________________________    Date: ______________")]
    path = os.path.join(claim_dir(out, c), "Buddy-Statement-Guide.docx")
    docx(path, b)
    return path


def vso(out, C, I):
    dest = os.path.join(out, "VSO-Handoff")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    copied = []

    def cp(src, rel):
        if os.path.exists(src):
            p = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            shutil.copy2(src, p)
            copied.append(rel)
    for f in ("526EZ-Copy-Paste-Guide.docx", "526EZ-Claim-List.docx"):
        cp(os.path.join(out, "Claims", f), f)
    cp(os.path.join(out, "My-Filing-Checklist.md"), "Filing-Checklist.md")
    cp(os.path.join(out, "My-Decision-Review.md"), "Decision-Review.md")
    rows = [["#", "Condition", "Rating code(s)", "Theory", "Statement", "Packet pages", "Doctor's letter", "Other"]]
    todo = []
    for c in C["claims"]:
        if c.get("vet_status") != "confirmed":
            continue
        folder = (c.get("writeup") or {}).get("folder")
        src = os.path.join(out, folder) if folder else None
        sub = f'{c["id"]}-{re.sub(r"[^A-Za-z0-9]+", "-", clean_name(c["condition"])).strip("-")[:40]}'
        others = []
        if src:
            for f in ("Statement.docx", "Evidence-Packet.pdf", "Doctor-Letter.docx", "Form-21-0781-Worksheet.docx",
                      "Exam-Prep.docx", "Buddy-Statement-Guide.docx", "Symptom-Log.docx"):
                cp(os.path.join(src, f), os.path.join(sub, f))
            others = [f.split(".")[0].replace("-", " ") for f in ("Form-21-0781-Worksheet.docx", "Buddy-Statement-Guide.docx",
                                                                  "Symptom-Log.docx") if os.path.exists(os.path.join(src, f))]
        lvl = letter_level(c, I)
        letter = {"needed": "Needed (template)", "optional": "Optional", "no": "-"}[lvl]
        if lvl == "needed":
            todo.append(f'{c["id"]}: signed doctor\'s letter still needed.')
        theory = (c.get("summary") or {}).get("claim_type") or c.get("type") or ""
        rows.append([c["id"], title(c), "; ".join(c.get("dc") or []), theory,
                     "Done" if (c.get("writeup") or {}).get("status") == "done" else "Not yet",
                     str((c.get("packet") or {}).get("pages") or "-"), letter, ", ".join(others) or "-"])
    fw = I.get("filing_window") or {}
    kd = fw.get("key_deadline") or {}
    b = [("h1", "Claim Hand-Off for My Representative"),
         ("p", "Veteran's name: ______________________________    VA file number or SSN (last 4): ________"),
         ("p", f'Prepared: {date.today().isoformat()}. This folder contains medical information. Please keep it private.'),
         ("h2", "Service"),
         ("p", f'Branch: {I.get("branch", "")}    Service start: {I.get("service_start", "")}    '
               f'Separation: {I.get("separation_date", "")}    Status: {I.get("status", "")}'),
         ("p", "Filing window: " + (fw.get("summary") or "-")),
         ("p", f'Key deadline: {kd.get("label", "-")} {kd.get("date", "")}'),
         ("h2", "Claims"),
         ("table", rows, {"widths": [480, 1700, 1600, 1600, 1000, 800, 1100, 1800]}),
         ("h2", "What's in this folder"),
         ("p", "• 526EZ copy-and-paste guide and claim list (every condition, cause, explanation and start date)."),
         ("p", "• One folder per claim: the Veteran's signed-ready statement, the evidence packet (claim summary "
               "with record quotes checked against the records, an index, and only the relevant record pages), "
               "and any doctor's letter template, 21-0781 worksheet, exam prep sheet, buddy statement guide or symptom log."),
         ("p", "• The filing checklist, and the decision review if a decision has been received."),
         ("h2", "Open items")]
    b += [("p", "• " + t) for t in todo] or [("p", "None noted.")]
    b += [("h2", "Questions for my representative"), ("table", [[""]] * 5, {"header": False, "height": 480})]
    docx(os.path.join(dest, "00-Cover-Memo.docx"), b)
    copied.insert(0, "00-Cover-Memo.docx")
    zpath = os.path.join(out, "VSO-Handoff.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in copied:
            z.write(os.path.join(dest, rel), os.path.join("VSO-Handoff", rel))
    return dest, zpath, copied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["exam", "log", "buddy", "vso", "family"])
    for x in ("--claims", "--id", "--out", "--intake", "--kind"):
        ap.add_argument(x)
    ap.add_argument("--weeks", type=int, default=8)
    a = ap.parse_args()
    C, G = load(a.claims), load(GUIDE)
    if a.cmd == "vso":
        I = load(a.intake) if a.intake else {}
        d, z, files = vso(a.out, C, I)
        print(json.dumps({"folder": d, "zip": z, "files": len(files)}, indent=1))
        return
    c = find(C, a.id)
    if a.cmd == "family":
        print(family(c, G))
    elif a.cmd == "exam":
        print(exam(a.out, c, G))
    elif a.cmd == "log":
        p, k = log(a.out, c, G, a.kind or "auto", a.weeks)
        print(json.dumps({"file": p, "kind": k}))
    elif a.cmd == "buddy":
        print(buddy(a.out, c, G))


if __name__ == "__main__":
    main()
