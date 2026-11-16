#!/usr/bin/env python3
"""
VA Claims Assistant - read a VA decision letter (rating decision) and compare it with the claims.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Uses pdftotext or pypdf.

  parse   --letter <decision.pdf|.txt>                     decisions as JSON (granted %, denied, combined, dates)
  compare --claims F --decision d.json [--out <VA-Claim-Output>]
          match each decision to a claim, flag 0% ratings, denials, claims not decided, and
          removed claims VA granted anyway; store on claims.json and write My-Decision-Review.md

Review deadline = one day before the 1-year anniversary of the letter date (conservative,
same rule as filing-rules.md). Nothing here gives a legal opinion; Claude explains, the
Veteran decides, a VSO can help.
"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, re, shutil, subprocess, sys
from datetime import date, datetime, timedelta

MONTH_DATE = r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}"
SYN = {  # word -> concept, to match VA wording to claim names
    "lumbar": "back", "lumbosacral": "back", "thoracolumbar": "back", "back": "back", "spine": "spine",
    "cervical": "neck", "neck": "neck", "knee": "knee", "meniscal": "knee", "meniscus": "knee",
    "hamstring": "hamstring", "hip": "hip", "ankle": "ankle", "shoulder": "shoulder", "arm": "arm",
    "radiculopathy": "nerve", "radicular": "nerve", "nerve": "nerve", "scar": "scar", "scars": "scar",
    "tinnitus": "tinnitus", "gerd": "gerd", "gastroesophageal": "gerd", "reflux": "gerd",
    "migraine": "headache", "migraines": "headache", "headache": "headache", "headaches": "headache",
    "apnea": "apnea", "sleep": "sleep", "ptsd": "ptsd", "post": "ptsd", "traumatic": "trauma", "tbi": "tbi",
    "brain": "tbi", "anxiety": "anxiety", "hypertension": "hypertension", "eye": "eye", "femur": "femur",
    "dysplasia": "femur", "rhinitis": "rhinitis", "insomnia": "sleep", "ankles": "ankle", "hips": "hip",
    "shoulders": "shoulder", "knees": "knee",
}


def read_text(path):
    if path.lower().endswith(".txt"):
        return open(path, encoding="utf-8", errors="ignore").read()
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True).stdout
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)


def strip_running_heads(text):
    """Drop page headers and footers (short lines that repeat on many pages, page counters)."""
    lines = [l.strip() for l in text.splitlines()]
    count = {}
    for l in lines:
        if l:
            count[l] = count.get(l, 0) + 1
    keep = [l for l in lines if not (l and ((count[l] >= 3 and len(l) < 60 and not re.search(r"[a-z]", l))
                                          or re.fullmatch(r"(?:Page )?\d+ of \d+|ICN: .*Page \d+", l)))]
    return "\n".join(keep)


def parse(text):
    flat = " ".join(strip_running_heads(text).split())
    m = re.search(MONTH_DATE, flat)
    letter_date = datetime.strptime(m.group(0), "%B %d, %Y").date() if m else None
    # the numbered DECISION list of the Rating Decision is single-column and complete
    sec = flat
    a = re.search(r"\bDECISION\s+(?:1\. )?Service connection", flat)
    if a:
        b = flat.find(" EVIDENCE ", a.end())
        sec = flat[a.start():b if b > 0 else len(flat)]
    items = []
    seen = set()
    for x in re.finditer(r"Service connection for ((?:(?!Service connection for).)+?) is (granted with an evaluation of ([0-9AOoIlSB]{1,3}) percent"
                         r"(?: effective (" + MONTH_DATE + r"))?|denied|continued[^.]*)\s*\.", sec):
        name = re.sub(r"\s+", " ", x.group(1)).strip()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        if x.group(3) is not None:
            raw = x.group(3)
            pct = int(raw.translate(str.maketrans("AOoIlSB", "4001158")))  # scanned letters: 'AO' = 40
            item = {"condition": name, "result": "granted", "percent": pct, "effective": x.group(4)}
            if not raw.isdigit():
                item["ocr_fix"] = f"read '{raw}' as {pct}; check the letter"
            items.append(item)
        elif x.group(2).startswith("denied"):
            items.append({"condition": name, "result": "denied"})
    comb = re.search(r"combined (?:rating )?evaluation is (\d{1,3}) ?%", flat, re.I) or \
        re.search(r"combined evaluation (?:for compensation )?(?:is )?(\d{1,3}) percent", flat, re.I)
    pt = bool(re.search(r"permanent and total", flat, re.I))
    out = {"letter_date": letter_date.isoformat() if letter_date else None, "combined": int(comb.group(1)) if comb else None,
           "permanent_total": pt, "dea": bool(re.search(r"Dependents' Educational Assistance", flat)),
           "dependents_note": bool(re.search(r"21-686c", flat)), "decisions": items}
    if letter_date:
        try:
            anniv = letter_date.replace(year=letter_date.year + 1)
        except ValueError:
            anniv = letter_date + timedelta(days=365)
        out["review_deadline_nlt"] = (anniv - timedelta(days=1)).isoformat()
    return out


def concepts(s):
    words = re.findall(r"[a-z]+", (s or "").lower())
    return {SYN[w] for w in words if w in SYN}


def sides(s):
    s = (s or "").lower()
    found = set(re.findall(r"\b(left|right)\b", s))
    if re.search(r"\b(both|bilateral|b/l)\b", s):
        found |= {"left", "right"}
    return found


def match(item, claims, text=None):
    """Best claim for a decision item: shared body concept, and sides that agree. VA's own name is
    tried first, then the '(claimed as ...)' words."""
    text = text if text is not None else item["condition"]
    own = re.split(r"\(claimed as", text, flags=re.I)[0]
    best = _match(own, claims)
    if not best and own != text:
        best = _match(text, claims)
    return best


def _match(text, claims):
    ic, isd = concepts(text), sides(text)
    best, score = None, 0
    for c in claims:
        cc = concepts(c["condition"] + " " + " ".join(c.get("dc") or []))
        common = ic & cc
        if not common:
            continue
        csd = sides(c["condition"])
        if isd and csd and not (isd & csd):
            continue
        sc = len(common) + (1 if isd and isd & csd else 0)
        if sc > score:
            best, score = c, sc
    return best


def compare(C, D):
    rows, flags = [], []
    decided = set()
    for it in D["decisions"]:
        main, _, extra = it["condition"].partition(" to include ")
        c = match(it, C["claims"], main)
        also = match(it, C["claims"], extra) if extra else None
        row = dict(it, claim_id=c["id"] if c else None, claim_status=c.get("vet_status") if c else None)
        if not c and also:
            c, also = also, None
            row.update(claim_id=c["id"], claim_status=c.get("vet_status"))
        if also and (not c or also["id"] != c["id"]):
            row["also_covers"] = also["id"]
            decided.add(also["id"])
        rows.append(row)
        if c:
            decided.add(c["id"])
        if it["result"] == "granted" and c and c.get("vet_status") == "removed":
            flags.append({"kind": "removed_but_granted", "claim": c["id"], "condition": it["condition"],
                          "msg": f"VA granted {it['percent']}% for a claim that was removed in the app. Lesson: keep conditions that have their own diagnosis or exam."})
        if it["result"] == "granted" and it["percent"] == 0 and not any(
                x.get("percent") and match(x, C["claims"], x["condition"].partition(" to include ")[0]) is c
                for x in D["decisions"]):
            flags.append({"kind": "zero_percent", "claim": row["claim_id"], "condition": it["condition"],
                          "msg": "Rated 0%. Compare the Veteran's own facts with the next level's criteria in the letter; a Supplemental Claim needs new evidence."})
        if it["result"] == "denied":
            ok = c and c.get("vet_status") == "removed" or any(
                x for x in C.get("not_recommended", []) if concepts(x["condition"]) & concepts(it["condition"]))
            flags.append({"kind": "denied", "claim": row["claim_id"], "condition": it["condition"],
                          "msg": "Denied. " + ("The app had not recommended this claim." if ok else "Read the reason; new evidence (often a diagnosis or a doctor's opinion) goes with a Supplemental Claim.")})
    for c in C["claims"]:
        if c.get("vet_status") == "confirmed" and c["id"] not in decided:
            flags.append({"kind": "not_decided", "claim": c["id"], "condition": c["condition"],
                          "msg": "Not in this decision. Check whether it was on the claim form; if not, it can be filed now."})
    return rows, flags


def md(D, rows, flags):
    L = ["# My Decision Review", ""]
    if D.get("combined") is not None:
        L.append(f"**Combined rating: {D['combined']}%**" + (" (permanent and total)" if D.get("permanent_total") else ""))
    if D.get("review_deadline_nlt"):
        if D["review_deadline_nlt"] < date.today().isoformat():
            L.append(f"\n**The 1-year review window ended {D['review_deadline_nlt']}.** A Supplemental Claim (VA Form 20-0995) "
                     "with new evidence still works, and so does a claim for an increase (21-526EZ). Benefits for those "
                     "start from the new filing date.")
        else:
            L.append(f"\n**To ask for a review and keep your effective date, file no later than {D['review_deadline_nlt']}.**")
    L += ["", "| VA decision | Rating | My claim |", "|---|---|---|"]
    for r in rows:
        res = f"{r['percent']}%" if r["result"] == "granted" else "Denied"
        L.append(f"| {r['condition']} | {res} | {r['claim_id'] or '-'} |")
    L += ["", "## Things to look at", ""]
    L += [f"- [ ] {f['claim'] or '-'}: {f['condition']}. {f['msg']}" for f in flags] or ["- Nothing."]
    L += ["", "## Other benefits to check", "",
          "- [ ] Rated 30% or more: add your spouse and children (VA Form 21-686c). Within 1 year of the letter, VA can pay back to the effective date.",
          "- [ ] Permanent and total: education benefits for dependents (DEA, Chapter 35)." if D.get("permanent_total") else "",
          "- [ ] Retiring with 20+ years and rated 50% or more: Concurrent Retirement and Disability Pay (CRDP). Confirm with DFAS.",
          "- [ ] VA life insurance (VALife) for service-connected Veterans.",
          "- [ ] Your state's Veteran benefits (property tax, license plates, tuition).", "",
          "> **THIS TOOL IS FREE. NO ONE SHOULD CHARGE YOU TO USE IT.** Report anyone who charges for an initial "
          "claim: VSAFE.gov or 1-833-38V-SAFE (1-833-388-7233).", ">", "> Not legal advice. Not affiliated with or endorsed by VA. AI can make mistakes: check everything against your records before filing. Explanations here are general; a VSO can advise you for free.", ""]
    return "\n".join(x for x in L if x is not None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["parse", "compare"])
    for x in ("--letter", "--claims", "--decision", "--out"):
        ap.add_argument(x)
    a = ap.parse_args()
    if a.cmd == "parse":
        print(json.dumps(parse(read_text(a.letter)), indent=1))
        return
    C = json.load(open(a.claims, encoding="utf-8"))
    D = json.load(open(a.decision, encoding="utf-8"))
    rows, flags = compare(C, D)
    C["decision"] = {"letter_date": D.get("letter_date"), "combined": D.get("combined"),
                     "permanent_total": D.get("permanent_total"), "review_deadline_nlt": D.get("review_deadline_nlt"),
                     "items": rows, "flags": flags, "saved": date.today().isoformat()}
    json.dump(C, open(a.claims, "w", encoding="utf-8"), indent=1)
    if a.out:
        open(os.path.join(a.out, "My-Decision-Review.md"), "w", encoding="utf-8").write(md(D, rows, flags))
    print(json.dumps({"items": rows, "flags": flags}, indent=1))


if __name__ == "__main__":
    main()
