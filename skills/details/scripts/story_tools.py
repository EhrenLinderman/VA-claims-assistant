#!/usr/bin/env python3
"""
VA Claims Assistant - "Your condition's story": how a condition started, what made it
worse (new injuries, more wear, waits for care, moves, surgeries that found more
damage), and how it is today. Records give a DRAFT; the Veteran confirms and adds.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

  draft --claims F --id C01 --pages page-text.jsonl.gz --terms condition-terms.json
        candidate dated events from the records (Claude reviews; nothing is final)
  save  --claims F --id C01 --story story.json     store the story on the claim (adds waits)
  show  --claims F --id C01                        plain-language timeline + waits
"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, gzip, json, re
from datetime import date, datetime

KINDS = {  # kind: (plain label, record pattern)
    "start":     ("It started", r"date of injury|\bdoi\b|injured (his|her|my|the)?|twist(ed|ing)[- ]type|sustained a"),
    "test":      ("Tested / diagnosed", r"\bmri\b[^.]{0,80}(impression|findings|tear|demonstrat)|impression:|x-?ray|radiograph"),
    "move":      ("Moved (PCS) or deployed during care", r"newly (pcs|assigned)|\bpcs\b|permanent change of station|previous (assignment|duty station)|last duty station"),
    "care_wait": ("Asked for care / waited", r"referral for|surgical consult|consult order|wait(ing)?[ -]list|no (surgeon|provider) (available)?|unable to schedule|deferred to network"),
    "treatment": ("Treatment (PT, brace, profile, shots)", r"physical therapy (service )?evaluation|knee brace|double upright|profile|injection"),
    "surgery":   ("Surgery", r"operative report|ambulatory surgery report|date of operation|procedure performed|operation performed"),
    "finding":   ("Found more damage", r"intraoperative findings|diminutive|deficien(t|cy)|chondromalacia|grade (iii|3|iv|4)"),
    "now":       ("How it is today", r"$^"),
    "worse":     ("Got worse / re-injured", r"re-?tear|re-?injur|worsen|gave way again|again had giving way|knee lock(ed)?"),
}
ENC_DATE = [  # encounter-date patterns, best first
    r"(?:date of operation|procedure date|service date/time|date of service)\s*:?\s*([0-9A-Za-z/ ,-]{6,20})",
    r"\bDate:\s*(\d{1,2} \w{3} \d{4})",
    r"approved date/time:\s*(\d{1,2} \w{3} \d{4})",
]
FMTS = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%B %d %Y", "%b %d %Y", "%B %d, %Y"]
PLACE = re.compile(r"(Fort [A-Z][a-z]+(?: [A-Z][a-z]+)?|Ft\.? [A-Z][a-z]+|Joint Base [A-Z][a-z]+(?: [A-Z][a-z]+)?|JB [A-Z][a-z]+ [A-Z][a-z]+|"
                   r"[A-Z][a-z]+ Proving ?.?Ground|Walter Reed|BAMC|Brooke Army|Camp [A-Z][a-z]+|"
                   r"Maryland|Texas|Virginia|Georgia|North Carolina|Kentucky|Washington|Colorado|Hawaii|Alaska|Korea|Germany)")


def pdate(s):
    s = re.sub(r"\s+", " ", s.strip().rstrip(".,"))
    for f in FMTS:
        for cand in (s, s[:10], s[:11]):
            try:
                return datetime.strptime(cand.strip(), f).date()
            except ValueError:
                pass
    return None


def enc_date(text, dates):
    for rx in ENC_DATE:
        m = re.search(rx, text, re.I)
        if m:
            d = pdate(m.group(1))
            if d:
                return d
    # fallback: earliest plausible date that isn't a birth or print date
    bad = set(re.findall(r"(?:DOB|birth|Created|Print Date/Time)\s*:?\s*([0-9A-Za-z/ ,-]{6,12})", text, re.I))
    ds = [pdate(x) for x in dates if x not in bad]
    ds = [d for d in ds if d and 1995 <= d.year <= date.today().year]
    return min(ds) if ds else None


def as_date(x):
    """'2020', '2020-04' or '2020-04-16' -> a date (missing parts = middle of the period).
    Anything else (ranges like '2008-2010', words) -> None."""
    m = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", (x or "").strip())
    if not m:
        return None
    y, mo, dd = int(m.group(1)), m.group(2), m.group(3)
    if mo is None:
        return date(y, 7, 1)
    return date(y, int(mo), min(int(dd), 28) if dd else 15)


def months(a, b):
    da, db = as_date(a), as_date(b)
    if not da or not db:
        return None
    return round(((db - da).days) / 30.44, 1)


def open_pages(p):
    f = gzip.open(p, "rt", encoding="utf-8") if p.endswith(".gz") else open(p, encoding="utf-8")
    for line in f:
        yield json.loads(line)


def get_claim(C, cid):
    for c in C["claims"]:
        if c["id"] == cid:
            return c
    raise SystemExit(f"no claim {cid}")


def waits(events):
    """For each surgery: months since the injury that led to it (the latest start/worse
    event before it) and since that injury's first test or care request."""
    ev = sorted((e for e in events if e.get("date")), key=lambda e: e["date"])
    out = []
    for i, s in enumerate(ev):
        if s["kind"] != "surgery":
            continue
        inj = [e for e in ev[:i] if (e["kind"] == "start" or (e["kind"] == "worse" and e.get("injury")))
               and e["date"] < s["date"]]
        if not inj:
            continue
        j = inj[-1]
        if not s.get("staged") and any(e["kind"] == "surgery" and j["date"] < e["date"] < s["date"] for e in ev[:i]):
            continue  # a surgery in between: a new, undated re-injury probably started this episode
        m = months(j["date"], s["date"])
        if m is not None and m >= 1:
            out.append({"what": f'From the {j["date"][:7]} injury to surgery on {s["date"]}', "months": m})
        asks = [e for e in ev[:i] if e["kind"] in ("test", "care_wait") and j["date"] <= e["date"] < s["date"]]
        ma = months(asks[0]["date"], s["date"]) if asks else None
        if ma is not None and m is not None and ma >= 1 and abs(ma - m) >= 1:
            out.append({"what": f'From first being seen ({asks[0]["date"]}) to surgery on {s["date"]}',
                        "months": months(asks[0]["date"], s["date"])})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["draft", "save", "show"])
    for x in ("--claims", "--id", "--pages", "--terms", "--story"):
        ap.add_argument(x)
    a = ap.parse_args()
    C = json.load(open(a.claims))
    c = get_claim(C, a.id)

    if a.cmd == "draft":
        T = json.load(open(a.terms))["conditions"]
        terms = [t.lower() for k in c.get("lead_keys", []) for t in T.get(k, {}).get("terms", [])]
        cterm = re.compile("|".join(re.escape(t) for t in terms)) if terms else None
        ev_pages = {(e["file"], e["page"]) for e in c.get("evidence", [])}
        found, injury_dates = {}, []
        for r in open_pages(a.pages):
            if r.get("dup_of") is not None:
                continue
            low = r["text"].lower()
            n = len(cterm.findall(low)) if cterm else 0
            if (r["file"], r["page"]) not in ev_pages and n < 2:
                continue
            d = enc_date(r["text"], r.get("dates", []))
            for m in re.finditer(r"(?:date of injury|injury)\s*(?:in|:)?\s*((?:early |late )?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*,?\s*(?:/\s*\w+\s*)?\d{0,4})", low):
                injury_dates.append({"says": m.group(1).strip(), "file": r["file"], "page": r["page"]})
            places = sorted(set(PLACE.findall(r["text"])))[:4]
            for kind, (label, rx) in KINDS.items():
                m = re.search(rx, low)
                if not m:
                    continue
                key = (kind, d.isoformat()[:7] if d else "undated")
                snip = re.sub(r"\s+", " ", r["text"][max(0, m.start() - 120):m.end() + 200])
                item = found.setdefault(key, {"kind": kind, "label": label, "date": d.isoformat() if d else None,
                                              "places": set(), "pages": [], "snippet": snip})
                item["places"].update(places)
                if len(item["pages"]) < 4:
                    item["pages"].append({"file": r["file"], "page": r["page"]})
        out = sorted(found.values(), key=lambda e: (e["date"] or "9999", list(KINDS).index(e["kind"])))
        for e in out:
            e["places"] = sorted(e["places"])
        seen, idates = set(), []
        for x in injury_dates:
            if x["says"] not in seen:
                seen.add(x["says"]); idates.append(x)
        print(json.dumps({"claim": c["condition"], "candidates": out, "injury_dates_reported": idates,
                          "note": "Draft only. Read the pages, keep what is real, merge repeats, and confirm with the Veteran."}, indent=1))

    elif a.cmd == "save":
        S = json.load(open(a.story))
        S["events"] = sorted(S.get("events", []), key=lambda e: e.get("date") or "9999")
        S["waits"] = waits(S["events"])
        S["saved"] = date.today().isoformat()
        c["story"] = S
        json.dump(C, open(a.claims, "w"), indent=1)
        print("saved")

    elif a.cmd == "show":
        S = c.get("story")
        if not S:
            print("No story saved yet."); return
        print(c["condition"])
        for e in S["events"]:
            lab = KINDS.get(e["kind"], (e["kind"],))[0]
            src = {"record": "records", "vet": "your words", "both": "records + your words"}.get(e.get("source"), "")
            print(f'- {e.get("date") or "date unknown"} · {lab}: {e.get("what", "")}'
                  + (f' ({e["where"]})' if e.get("where") else "") + (f" [{src}]" if src else ""))
        for w in S.get("waits", []):
            print(f'  ⏱ {w["what"]}: about {w["months"]:g} months')
        for l in S.get("led_to", []):
            print(f'  ➜ Led to: {l["condition"]} ({l.get("how", "")})')
        if S.get("outcome"):
            print("  Today: " + "; ".join(S["outcome"]))


if __name__ == "__main__":
    main()
