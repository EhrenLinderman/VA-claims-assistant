#!/usr/bin/env python3
"""
VA Claims Assistant - check a claim packet made somewhere else (by hand, another app, or
another AI) against the Veteran's own records, before it goes to VA.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Needs pypdf for PDFs.

  check --packet <file.pdf|.txt|.docx> --pages <page-text.jsonl.gz> --dc <diagnostic-codes.md> [--pages-only N]

Checks:
  quotes    every quoted passage ("..." or curly quotes, 4+ words) is searched in the record
            text. found = word-for-word on one page; close = most of it; not found = nowhere.
  codes     every "DC ####" is looked up in the rating schedule; flags codes that don't
            exist and names that don't match the code (e.g. a sleep claim under 9440,
            which is chronic adjustment disorder).
  dates     "Onset" years that come AFTER surgery/injury years in the same document.
  wording   lines raters discount: boilerplate ("no intercurrent injury") and medical
            opinions written in the Veteran's own statement.
Output is JSON. Nothing is changed. The packet text is read only; it is not saved.
"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, gzip, json, re, sys, zipfile


def norm(s):
    s = (s or "").lower().replace("ﬁ", "fi").replace("ﬂ", "fl")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def read_packet(path, max_pages=None):
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader
        r = PdfReader(path)
        pages = r.pages[:max_pages] if max_pages else r.pages
        return "\n".join((p.extract_text() or "") for p in pages)
    if path.lower().endswith(".docx"):
        x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "ignore")
        x = re.sub(r"</w:p>", "\n", x)
        return re.sub(r"<[^>]+>", "", x)
    return open(path, encoding="utf-8", errors="ignore").read()


def load_corpus(path):
    f = gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")
    out = []
    for line in f:
        r = json.loads(line)
        if r.get("dup_of") is None:
            out.append((r["file"], r["page"], norm(r.get("text", ""))))
    return out


def check_quotes(text, corpus):
    raw = re.findall(r"[“\"]([^”\"]{20,500})[”\"]", text)
    seen, res = set(), []
    for q in raw:
        key = norm(q)[:80]
        if key in seen:
            continue
        seen.add(key)
        pieces = [norm(p) for p in re.split(r"…|\.\.\.", q)]
        pieces = [p for p in pieces if len(p.split()) >= 4]
        if not pieces:
            continue
        best, where, exact = 0.0, None, False
        for fl, pg, c in corpus:
            if all(p in c for p in pieces):
                best, where, exact = 1.0, (fl, pg), True
                break
            grams = [g for p in pieces for g in (" ".join(p.split()[i:i + 4]) for i in range(max(1, len(p.split()) - 3)))]
            hit = sum(g in c for g in grams) / len(grams)
            if hit > best:
                best, where = hit, (fl, pg)
        status = "found" if exact else ("close" if best >= 0.6 else "not found")
        res.append({"quote": re.sub(r"\s+", " ", q)[:160], "status": status, "match": round(best, 2),
                    "page": {"file": where[0], "page": where[1]} if where and best >= 0.3 else None})
    return res


def load_dcs(path):
    dcs = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\|\s*(\d{4})\s*\|\s*([^|]+)\|", line)
        if m:
            dcs[m.group(1)] = m.group(2).strip()
    return dcs


STOP = {"of", "the", "and", "or", "a", "an", "other", "than", "with", "to", "in", "nos", "chronic", "dc",
        "disorder", "disorders", "disease", "condition", "conditions", "syndrome", "impairment", "residuals"}


ALIASES = {  # common names people use for a code (word starts)
    "5257": ["instab", "sublux"], "5258": ["menisc", "cartil"], "5259": ["menisc", "cartil"],
    "5260": ["flexion", "motion"], "5261": ["extension", "motion"], "5237": ["strain", "lumbo"],
    "5242": ["degener", "arthrit", "spine"], "5243": ["disc", "interverteb"], "5271": ["motion", "ankle"],
    "5201": ["motion", "arm", "shoulder"], "5252": ["flexion", "thigh", "hip"], "5003": ["arthrit", "degener"],
    "9411": ["ptsd", "post", "stress"], "8045": ["tbi", "brain"], "8100": ["migrain", "headache"],
    "6847": ["apnea", "sleep"], "6260": ["tinnit", "ring"], "7206": ["gerd", "reflux", "esoph"],
    "5313": ["hamstr", "muscle"], "6522": ["rhinit", "allerg"], "5015": ["benign", "tumor", "dysplas", "neoplas"],
}


def check_codes(text, dcs):
    out, seen = [], set()
    for m in re.finditer(r"\bDC[ \t]*(\d{4})(?:[ \t]*/[ \t]*(\d{4}))?[ \t]*(?:[(–—:-][ \t]*)?([A-Za-z][^\n)•]{3,70})?", text):
        for code in [m.group(1), m.group(2)]:
            if not code or code in seen:
                continue
            seen.add(code)
            given = (m.group(3) or "").strip()
            if code not in dcs:
                out.append({"dc": code, "given_name": given, "problem": "not a diagnostic code in the rating schedule"})
                continue
            official = dcs[code]
            gw = {w for w in norm(given).split() if w not in STOP and len(w) > 2}
            ow = {w for w in norm(official).split() if w not in STOP and len(w) > 2}
            alias = any(w.startswith(x) for w in gw for x in ALIASES.get(code, []))
            if given and gw and not alias and not (gw & ow) and not any(g[:5] == o[:5] for g in gw for o in ow):
                out.append({"dc": code, "given_name": given, "official_name": official,
                            "problem": "the name given doesn't match this code"})
    return out


def check_dates(text):
    onset = [int(y) for y in re.findall(r"Onset[^\n]{0,40}?\b((?:19|20)\d\d)\b", text, re.I)]
    events = [int(y) for y in re.findall(r"(?:surgery|surgical|operative|operation|injur\w*|repair)[^\n]{0,60}?\b((?:19|20)\d\d)\b", text, re.I)]
    out = []
    if onset and events and min(onset) > min(events):
        out.append({"problem": f"Check: onset year {min(onset)} comes after a surgery or injury year ({min(events)}) mentioned in the same document"})
    return out


WORDING = [  # (pattern, label, why)
    (r"no intercurrent (injury|trauma|non-service cause)", "No intercurrent injury", "Boilerplate: says no other cause exists, but cites nothing. Raters discount this; keep only if a record says it."),
    (r"at least as likely as not", "At least as likely as not", "Medical-opinion wording. In the Veteran's own statement it carries little weight; it belongs in a doctor's signed letter."),
    (r"\bmalpractice\b|\bnegligen", "Malpractice / negligence", "Blame wording. Describe what happened and how long it took instead."),
]


def check_wording(text):
    out = []
    for rx, label, why in WORDING:
        n = len(re.findall(rx, text, re.I))
        if n:
            out.append({"found": label, "count": n, "why": why})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("--packet", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--dc", required=True)
    ap.add_argument("--pages-only", type=int)
    a = ap.parse_args()
    text = read_packet(a.packet, a.pages_only)
    q = check_quotes(text, load_corpus(a.pages))
    res = {"packet": a.packet.split("/")[-1],
           "quotes": {"total": len(q), "found": sum(x["status"] == "found" for x in q),
                      "close": sum(x["status"] == "close" for x in q),
                      "not_found": sum(x["status"] == "not found" for x in q), "items": q},
           "codes": check_codes(text, load_dcs(a.dc)), "dates": check_dates(text), "wording": check_wording(text)}
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
