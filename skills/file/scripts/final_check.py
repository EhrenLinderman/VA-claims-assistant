#!/usr/bin/env python3
"""
VA Claims Assistant - final check before filing. Read-only except for the checklist page.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

  check --out <VA-Claim-Output> --dc <diagnostic-codes.md> [--md]
        every claim: statement, packet, summary quotes, rating codes, letters, worksheets;
        consistency of start dates across the 526EZ list, statement and Claim Summary;
        packets older than their statements; deadline. --md also writes My-Filing-Checklist.md

Problem levels: "fix" (must fix before filing), "todo" (Veteran action, can follow the claim),
"check" (look at it; may be fine).
"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, re, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "evidence", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "writeups", "scripts"))
MENTAL = re.compile(r"ptsd|depress|anxiety|mental|adjustment|bipolar|schizo", re.I)


def load_dcs(path):
    out = set()
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\|\s*(\d{4})\s*\|", line)
        if m:
            out.add(m.group(1))
    return out


def years(text):
    return set(re.findall(r"\b(?:19|20)\d\d\b", text or ""))


def check(out, dc_path):
    C = json.load(open(os.path.join(out, "Claims", "claims.json"), encoding="utf-8"))
    I = {}
    ip = os.path.join(out, "intake.json")
    if os.path.exists(ip):
        I = json.load(open(ip, encoding="utf-8"))
    dcs = load_dcs(dc_path)
    pages = os.path.join(out, "Evidence", "page-text.jsonl.gz")
    ez = {r["id"]: r for r in C.get("ez_list", [])}
    rows, problems = [], []

    def p(level, cid, msg):
        problems.append({"level": level, "id": cid, "msg": msg})

    for c in C["claims"]:
        if c.get("vet_status") != "confirmed":
            continue
        cid = c["id"]
        folder = os.path.join(out, (c.get("writeup") or {}).get("folder") or "-")
        st, sd = os.path.join(folder, "Statement.txt"), os.path.join(folder, "Statement.docx")
        pk = os.path.join(out, (c.get("packet") or {}).get("file") or "-")
        row = {"id": cid, "name": re.split(r"\s*[(:,]", c["condition"])[0].strip(),
               "statement": os.path.exists(st) and os.path.exists(sd),
               "packet": os.path.exists(pk), "summary": bool(c.get("summary")),
               "packet_mb": round(os.path.getsize(pk) / 1e6, 1) if os.path.exists(pk) else None,
               "doctor_letter": bool((c.get("writeup") or {}).get("doctor_letter"))
               or os.path.exists(os.path.join(folder, "Doctor-Letter.docx")),
               "form_0781": os.path.exists(os.path.join(folder, "Form-21-0781-Worksheet.docx"))}
        rows.append(row)
        if not row["statement"]:
            p("fix", cid, "No saved statement. Finish it in 'Draft your statements' or file without one.")
        if not row["packet"]:
            p("fix", cid, "No evidence packet. Build it in 'Build your claim packet'.")
        elif row["statement"] and os.path.getmtime(st) > os.path.getmtime(pk) + 1:
            p("fix", cid, "The statement changed after the packet was built. Rebuild this packet.")
        if c.get("summary") and os.path.exists(pages):
            from claim_summary import verify
            for x in verify(c["summary"], c, pages):
                p("fix", cid, "Claim Summary: " + x)
        for d in c.get("dc") or []:
            for code in re.findall(r"\b\d{4}\b", d):
                if code not in dcs:
                    p("fix", cid, f"Rating code {code} is not in the rating schedule.")
        if row["doctor_letter"]:
            from writeups_tools import letter_level
            if letter_level(c, I) == "needed":
                p("todo", cid, "Doctor's letter: take the template to a doctor; upload the signed letter when you have it (it can follow the claim).")
            else:
                p("todo", cid, "Doctor's letter is optional: diagnosed on active duty, so VA usually grants it without one. Keep the template in case of a denial.")
        if MENTAL.search(c["condition"]) and not row["form_0781"]:
            p("check", cid, "Mental health claim: answer the event questions in the online claim, or make the 21-0781 worksheet.")
        # start dates must agree across the 526EZ list, the statement and the Claim Summary
        e = ez.get(cid)
        if not e:
            p("fix", cid, "Missing from the 526EZ claim list.")
        elif e.get("date"):
            y = e["date"][-4:]
            stxt = open(st, encoding="utf-8").read() if os.path.exists(st) else ""
            onset = (c.get("summary") or {}).get("onset", "")
            if stxt and y not in years(stxt) and y not in years(onset):
                p("check", cid, f"526EZ start date {e['date']} isn't mentioned in the statement or the summary's onset.")
            oy = sorted(years(onset))
            if oy and y not in oy and int(y) < int(oy[0]):
                p("check", cid, f"526EZ start year {y} is earlier than the summary's onset ({oy[0]}).")
        for ev in c.get("evidence", []):
            if ev.get("role") == "contrary" and not ev.get("vet_explanation"):
                p("check", cid, f"A record that disagrees ({ev['file']} p.{ev['page']}) has no explanation yet.")
    if not C.get("ez_list"):
        p("fix", "-", "No 526EZ claim list. Make it at the end of 'Build your claim packet'.")
    kd = (I.get("filing_window") or {}).get("key_deadline") or {}
    days_left = None
    if kd.get("date"):
        days_left = (date.fromisoformat(kd["date"]) - date.today()).days
    window = (I.get("filing_window") or {}).get("window")
    return {"rows": rows, "problems": problems, "deadline": kd.get("label"), "deadline_date": kd.get("date"),
            "days_left": days_left, "window": window,
            "counts": {k: sum(1 for x in problems if x["level"] == k) for k in ("fix", "todo", "check")}}


NOTICE = ("> **THIS TOOL IS FREE. NO ONE SHOULD CHARGE YOU TO USE IT.** It is unlawful for anyone to charge "
          "a fee for preparing an initial VA claim. Report it: VSAFE.gov or 1-833-38V-SAFE (1-833-388-7233).\n>\n> Not legal advice. Not affiliated with or endorsed by VA. AI can make mistakes: check everything against your records before filing.")


def md(R):
    L = ["# My Filing Checklist", ""]
    if R["deadline_date"]:
        L += [f"**{R['deadline']}: {R['deadline_date']} ({R['days_left']} days left).** "
              "VA counts the day it receives your claim. Filing online gives you proof right away.", ""]
    L += ["## Your claims", "", "| Claim | Statement | Packet (MB) | Doctor's letter | 21-0781 worksheet |",
          "|---|---|---|---|---|"]
    for r in R["rows"]:
        L.append(f"| {r['name']} | {'Yes' if r['statement'] else 'MISSING'} | "
                 f"{r['packet_mb'] if r['packet'] else 'MISSING'} | {'Take to a doctor' if r['doctor_letter'] else '-'} | "
                 f"{'Yes' if r['form_0781'] else '-'} |")
    for lvl, title in (("fix", "Fix before filing"), ("check", "Take a look"), ("todo", "Can follow the claim")):
        items = [x for x in R["problems"] if x["level"] == lvl]
        L += ["", f"## {title} ({len(items)})", ""]
        L += [f"- [ ] {x['id']}: {x['msg']}" for x in items] or ["- Nothing here."]
    L += ["", "## What to file", "",
          "- [ ] VA Form 21-526EZ (online at VA.gov is best). Use `Claims/526EZ-Claim-List.docx` for the claim list.",
          "- [ ] For each claim: upload `Evidence-Packet.pdf`, and the statement (paste `Statement.txt` into the online "
          "Lay/Witness Statement, VA Form 21-10210, or upload the signed `Statement.docx` as a PDF).",
          "- [ ] BDD claims: the Separation Health Assessment Part A (Self-Assessment). Filing online, VA gets your "
          "service treatment records; on paper, include a copy.",
          "- [ ] Be available for VA exams for 45 days after you file (BDD).",
          "- [ ] Signed doctor's letters when you have them (you have up to a year after VA receives your claim to add evidence).",
          "", NOTICE, ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--dc", required=True)
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()
    R = check(a.out, a.dc)
    if a.md:
        path = os.path.join(a.out, "My-Filing-Checklist.md")
        open(path, "w", encoding="utf-8").write(md(R))
        R["checklist"] = path
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    main()
