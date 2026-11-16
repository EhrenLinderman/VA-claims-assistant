#!/usr/bin/env python3
"""
VA Claims Assistant - "Draft your statements" helpers.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

  facts  --claims F --intake I --duties D --id C01             fact sheet (JSON) for drafting one claim
  save   --claims F --id C01 --text statement.txt --out <VA-Claim-Output> [--status draft|done]
         writes Claims/<C01-name>/Statement.txt + Statement.docx and sets writeup.status
  letter --claims F --intake I --duties D --id C01 --out <VA-Claim-Output>
         writes Claims/<C01-name>/Doctor-Letter.docx (fact sheet + opinion template the doctor edits and signs)
  needs_letter --claims F                                       claims that still need a doctor's link

Filed documents (statements, letters) carry NO app notices or markers.
"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, re, zipfile
from datetime import date
from xml.sax.saxutils import escape

CERT = ("I certify that the statements in this document are true and correct to the best of my "
        "knowledge and belief.")
PENALTY = ("I understand that the law provides severe penalties, including a fine, imprisonment, or both, "
           "for the willful submission of any statement or evidence of a material fact, knowing it to be "
           "false (18 U.S.C. 1001).")


# ---------- tiny, portable .docx writer ----------
def docx(path, blocks):
    """blocks: list of (style, text) where style in h1, h2, p, b (bold para), line (signature line), small, check,
    pagebreak; or ("table", rows, {"widths": [...], "height": twips})."""
    def run(text, bold=False, size=None, italic=False):
        rpr = ""
        if bold or size or italic:
            rpr = "<w:rPr>" + ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + \
                  (f'<w:sz w:val="{size}"/>' if size else "") + "</w:rPr>"
        parts = text.split("\n")
        out = ""
        for i, t in enumerate(parts):
            if i:
                out += "<w:r><w:br/></w:r>"
            out += f'<w:r>{rpr}<w:t xml:space="preserve">{escape(t)}</w:t></w:r>'
        return out
    def table(rows, widths=None, header=True, height=None):
        """rows: list of lists of str. Bordered grid; the first row is bold if header."""
        n = max(len(r) for r in rows)
        widths = widths or [int(10080 / n)] * n
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        b = '<w:tblBorders>' + "".join(f'<w:{x} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
                                         for x in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders>'
        out = f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/>{b}</w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
        for i, r in enumerate(rows):
            trpr = f'<w:trPr><w:trHeight w:val="{height}"/></w:trPr>' if height and not (header and i == 0) else ""
            out += f"<w:tr>{trpr}"
            for j in range(n):
                t = r[j] if j < len(r) else ""
                out += (f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/></w:tcPr>'
                        f'<w:p>{run(t, header and i == 0, 18)}</w:p></w:tc>')
            out += "</w:tr>"
        return out + "</w:tbl><w:p/>"
    body = ""
    for blk in blocks:
        style, text = blk[0], blk[1]
        if style == "table":  # ("table", rows, {"widths": [...], "height": 400})
            opts = blk[2] if len(blk) > 2 else {}
            body += table(text, opts.get("widths"), opts.get("header", True), opts.get("height"))
            continue
        if style == "check":  # a box to tick, then the text
            body += f"<w:p>{run(chr(9744) + '  ' + text)}</w:p>"
            continue
        if style == "pagebreak":
            body += '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
            continue
        if style == "h1":
            body += f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>{run(text, True, 30)}</w:p>'
        elif style == "h2":
            body += f'<w:p><w:pPr><w:spacing w:before="200" w:after="80"/></w:pPr>{run(text, True, 24)}</w:p>'
        elif style == "b":
            body += f"<w:p>{run(text, True)}</w:p>"
        elif style == "small":
            body += f"<w:p>{run(text, False, 18, True)}</w:p>"
        elif style == "line":
            body += f'<w:p><w:pPr><w:spacing w:before="360"/></w:pPr>{run(text)}</w:p>'
        else:
            body += f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>{run(text)}</w:p>'
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           + body + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" '
           'w:bottom="1080" w:left="1080" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
              '<w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults></w:styles>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", drels)


# ---------- helpers ----------
def load(p):
    return json.load(open(p, encoding="utf-8"))


def find(C, cid):
    for c in C["claims"]:
        if c["id"] == cid:
            return c
    raise SystemExit(f"no claim {cid}")


def short(name):
    s = re.split(r"\s*[(:,]", name)[0].strip()
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:40]


def claim_dir(out, c):
    d = os.path.join(out, "Claims", f'{c["id"]}-{short(c["condition"])}')
    os.makedirs(d, exist_ok=True)
    return d


def duty_labels(ids, D):
    m = {d["id"]: d.get("label", d["id"]) for d in D["duties"]}
    return [m.get(i, i) for i in ids or []]


def fmt_date(s):
    if not s:
        return ""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3])).strftime("%b %-d, %Y")
    m = re.fullmatch(r"(\d{4})-(\d{2})", s)
    if m:
        return date(int(m[1]), int(m[2]), 1).strftime("%b %Y")
    return s


def lower_first(s):
    return s if s[:2].isupper() else s[:1].lower() + s[1:]


def clean_name(name):
    """'Left knee condition, caused by favoring the right knee' -> 'left knee condition'."""
    return lower_first(re.split(r"\s*[(:,]", name)[0].strip())


EARLY_WINDOWS = {"bdd", "pre_discharge", "under_90", "first_year"}


def letter_level(c, I=None):
    """'needed', 'optional' or 'no'. Answer-key lesson (2026-11-08): on a BDD claim, 7 of 8 conditions
    with letter templates were granted without one, because a diagnosis made on active duty, claimed
    within a year of discharge, usually meets the link by itself (38 CFR 3.303(a)). Aggravation
    claims still need a doctor's opinion."""
    el = c.get("elements", {})
    if c.get("vet_status") != "confirmed" or el.get("nexus") == "found":
        return "no"
    I = I or {}
    window = (I.get("filing_window") or {}).get("window", "")
    sep = I.get("separation_date") or "9999"
    in_service_dx = any(e.get("role") in ("diagnosis", "in_service") and (e.get("date") or "9999")[:10] <= sep
                        for e in c.get("evidence", []))
    if c.get("type") != "aggravation" and window in EARLY_WINDOWS and in_service_dx:
        return "optional"
    return "needed"


def needs_letter(c, I=None):
    return letter_level(c, I) == "needed"


def facts(c, I, D):
    d, s = c.get("details") or {}, c.get("story") or {}
    ev = [{"date": e.get("date", ""), "role": e.get("role"), "shows": e.get("shows"),
           "page": f'{e["file"]} p.{e["page"]}', "vet_explanation": e.get("vet_explanation")}
          for e in c.get("evidence", [])]
    return {
        "id": c["id"], "condition": c["condition"], "type": c.get("type"), "secondary_to": c.get("secondary_to"),
        "dc": c.get("dc"), "separate_parts": c.get("separate_parts", []),
        "service": {k: I.get(k) for k in ("branch", "service_start", "separation_date", "status")},
        "duties": duty_labels(d.get("duties"), D), "injury": d.get("injury"),
        "answers": d.get("answers", {}), "impact": d.get("impact", {}),
        "story_events": [{"date": fmt_date(e.get("date")), "where": e.get("where"), "what": e.get("what"),
                          "source": e.get("source")} for e in s.get("events", [])],
        "waits": s.get("waits", []), "caused_by": s.get("caused_by", []), "led_to": s.get("led_to", []),
        "outcome": s.get("outcome", []), "vet_words": s.get("vet_words", ""),
        "secondary_alt": c.get("secondary_alt", []), "evidence": ev,
        "stressors": [{k: e.get(k) for k in ("type", "what", "where", "when", "unit", "hurt")}
                      for e in (c.get("stressors") or {}).get("events", [])],
        "behavior_changes": (c.get("stressors") or {}).get("behavior_changes", []),
        "contrary_explained": [e for e in ev if e["role"] == "contrary"],
        "needs_doctor_letter": needs_letter(c, I),
        "doctor_letter_level": letter_level(c, I),
        "rules": ["First person, plain words, past events in date order, then how it is now.",
                  "Use ONLY facts in this sheet. No diagnoses the records don't have. No rating requests.",
                  "Typical days AND bad days. Work, family, daily life. One real example if given.",
                  "Explain contrary records using the Veteran's own explanation.",
                  "No app notices or markers in filed documents.",
                  "Mental health claims: describe each stressor event briefly (what, where, about when, unit), "
                  "without graphic detail, then the changes after."],
    }


def write_statement(out, c, text, I):
    d = claim_dir(out, c)
    txt = text.strip() + "\n\n" + CERT + "\n" + PENALTY + "\n"
    open(os.path.join(d, "Statement.txt"), "w", encoding="utf-8").write(txt)
    cond = re.split(r"\s*[(:,]", c["condition"])[0].strip()
    blocks = [("h1", "Statement in Support of Claim"),
              ("p", "Veteran: ______________________________    VA file number or SSN (last 4): __________"),
              ("p", "Claimed condition: " + cond),
              ("h2", "My statement")]
    for para in [p.strip() for p in text.strip().split("\n\n") if p.strip()]:
        blocks.append(("p", para))
    blocks += [("h2", "Certification"), ("p", CERT), ("small", PENALTY),
               ("line", "Signature: ______________________________________    Date: ________________")]
    docx(os.path.join(d, "Statement.docx"), blocks)
    return d


C_ALL = []


def write_letter(out, c, I, D):
    F = facts(c, I, D)
    d = claim_dir(out, c)
    cond = clean_name(c["condition"])
    prim = ""
    ids, names = [], []
    for x in F["caused_by"]:
        if x.get("claim_id"):
            ids.append(x["claim_id"])
        else:
            names.append(x["condition"])
    for alt in F.get("secondary_alt") or []:
        ids += re.findall(r"C\d{2}", str(alt.get("to", "")))
    seen = set()
    for cid in ids:
        if cid in seen:
            continue
        seen.add(cid)
        for o in C_ALL:
            if o["id"] == cid and o.get("vet_status") == "confirmed":
                names.append(clean_name(o["condition"]))
    if not names and c.get("secondary_to"):
        names = [str(c["secondary_to"])]
    if names:
        prim = " and ".join(lower_first(n) for n in names)
    blocks = [("h1", "Medical Opinion"),
              ("small", "Template prepared from the Veteran's records for the doctor to review, edit and sign. "
                        "The opinion, wording and reasons must be the doctor's own."),
              ("p", "Physician name, specialty and license: ____________________________________________"),
              ("p", "Veteran: ______________________________    Date of birth: ______________"),
              ("p", f"Condition: {cond}"),
              ("h2", "Records I reviewed"),
              ("p", "[ ] Service treatment records   [ ] VA records   [ ] Private records   [ ] VA exam reports   "
                    "[ ] The Veteran's statement   [ ] Examined the Veteran on: ____________"),
              ("h2", "Relevant history from the records")]
    for e in F["story_events"]:
        blocks.append(("p", f'• {e["date"] or "Date unknown"}: {e["what"]}' + (f' ({e["where"]})' if e["where"] else "")))
    if F["duties"]:
        blocks.append(("p", "Military duties the Veteran reports: " + "; ".join(F["duties"]) + "."))
    blocks.append(("p", "Key record pages: " + "; ".join(
        f'{e["page"]} ({e["date"]})' for e in F["evidence"] if e["role"] != "contrary")[:1500]))
    blocks.append(("h2", "Opinion (check one in each section that applies)"))
    if c.get("type") == "aggravation":
        blocks += [("p", f"It is [ ] at least as likely as not (50% or greater probability)  [ ] less likely than not "
                         f"that the Veteran's {cond} was permanently worsened beyond its natural progress by military service, "
                         "including the duties listed above (38 CFR 3.306).")]
    else:
        blocks += [("p", f"Direct: It is [ ] at least as likely as not (50% or greater probability)  [ ] less likely than not "
                         f"that the Veteran's {cond} began in, or was caused by, military service, including the duties "
                         "and events listed above.")]
    if prim:
        blocks += [("p", f"Secondary - caused: It is [ ] at least as likely as not  [ ] less likely than not that the "
                         f"Veteran's {cond} was caused by the Veteran's {prim}."),
                   ("p", f"Secondary - worsened: It is [ ] at least as likely as not  [ ] less likely than not that the "
                         f"Veteran's {cond} was worsened beyond its natural progress by the Veteran's {prim} (38 CFR 3.310(b)). "
                         "If yes, the baseline level before the worsening was: ____________________")]
    blocks += [("h2", "Reasons for my opinion"),
               ("p", "Please explain the medical reasoning, citing the records and any medical literature you rely on:"),
               ("p", "_" * 90 + "\n" + "_" * 90 + "\n" + "_" * 90),
               ("line", "Physician signature: ______________________________    Date: ______________\n"
                        "Phone: ______________    Address: ____________________________________________")]
    docx(os.path.join(d, "Doctor-Letter.docx"), blocks)
    return d


MIN_WORDS, GOAL_WORDS = 250, 500
DEPTH_CHECKS = [  # (key, pattern that shows it is covered, button question if missing)
    ("start", r"\b(19|20)\d\d\b|in service|deploy|training|while (i was )?(stationed|serving)",
     "When and how did this start in service? (a date, place, or duty)"),
    ("today", r"\btoday\b|\bnow\b|these days|every (day|night|week)|most (days|nights)",
     "What is it like on a typical day now?"),
    ("bad_days", r"flare|bad day|worse (days|nights)|some days|episodes?",
     "What happens on a bad day or during a flare-up, and how often?"),
    ("treatment", r"\b(medication|medicine|pills?|cpap|brace|surgery|therapy|counsel|injection|treat|prescri)",
     "What treatment or devices do you use for it (medicine, CPAP, brace, therapy)?"),
    ("work", r"\b(work|job|duty|duties|profile|mission|unit)\b",
     "How does it affect your work or duty?"),
    ("family", r"\b(family|kids|children|wife|husband|spouse|partner|son|daughter|friends|home)\b",
     "How does it affect your family, kids, or time with friends?"),
]


def depth(c, text):
    """Is the statement deep enough? Returns word count, gaps, and follow-up questions."""
    body = text.split("I certify that")[0]
    words = len(body.split())
    low = body.lower()
    gaps = [(k, q) for k, rx, q in DEPTH_CHECKS if not re.search(rx, low)]
    imp = (c.get("details") or {}).get("impact") or {}
    if not imp.get("example"):
        gaps.append(("example", "Can you give one real example of a time this got in the way?"))
    thin = words < MIN_WORDS
    questions = [q for _, q in gaps][:3] if (thin or len(gaps) >= 3) else []
    return {"id": c["id"], "words": words, "min": MIN_WORDS, "goal": GOAL_WORDS,
            "ok": not thin and len(gaps) < 3, "gaps": [k for k, _ in gaps], "ask": questions}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["facts", "save", "letter", "needs_letter", "depth"])
    for x in ("--claims", "--intake", "--duties", "--id", "--text", "--out", "--status"):
        ap.add_argument(x)
    a = ap.parse_args()
    C = load(a.claims)
    if a.cmd == "needs_letter":
        I = load(a.intake) if a.intake else {}
        print(json.dumps([{"id": c["id"], "condition": c["condition"], "level": letter_level(c, I)}
                          for c in C["claims"] if letter_level(c, I) != "no"], indent=1))
        return
    if a.cmd == "depth":
        rows = []
        for c in C["claims"]:
            if c.get("vet_status") != "confirmed" or (a.id and c["id"] != a.id):
                continue
            if a.text:
                t = open(a.text, encoding="utf-8").read()
            else:
                f = os.path.join(a.out or "", (c.get("writeup") or {}).get("folder", "-"), "Statement.txt")
                if not os.path.exists(f):
                    continue
                t = open(f, encoding="utf-8").read()
            rows.append(depth(c, t))
        print(json.dumps(rows, indent=1))
        return
    c = find(C, a.id)
    C_ALL[:] = C["claims"]
    I = load(a.intake) if a.intake else {}
    D = load(a.duties) if a.duties else {"duties": []}
    if a.cmd == "facts":
        print(json.dumps(facts(c, I, D), indent=1))
    elif a.cmd == "save":
        d = write_statement(a.out, c, open(a.text, encoding="utf-8").read(), I)
        c["writeup"] = {**(c.get("writeup") or {}),  # keep doctor_letter and anything else already saved
                        "status": a.status or "draft", "folder": os.path.relpath(d, a.out), "saved": date.today().isoformat()}
        json.dump(C, open(a.claims, "w"), indent=1)
        print(d)
    elif a.cmd == "letter":
        d = write_letter(a.out, c, I, D)
        c.setdefault("writeup", {})["doctor_letter"] = os.path.join(os.path.relpath(d, a.out), "Doctor-Letter.docx")
        json.dump(C, open(a.claims, "w"), indent=1)
        print(d)


if __name__ == "__main__":
    main()
