#!/usr/bin/env python3
"""
VA Claims Assistant - helpers for the "Describe each condition" step.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

  plan    --claims F --questions Q --duties D [--intake I]   per confirmed claim: question family + likely duties
  duties  --pages page-text.jsonl.gz --duties D               record pages that mention each service duty
  save    --claims F --id C01 --answers answers.json          store the Veteran's answers on the claim
  setduties --intake I --ids airborne,rucking [--note TEXT]    store the Veteran's service duties in intake.json
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, gzip, json, re, sys
from datetime import date

AREA_WORDS = {"knee": r"knee", "ankle": r"ankle", "hip": r"hip", "back": r"back|lumb|thoracolumbar",
              "neck": r"neck|cervical", "shoulder": r"shoulder", "hamstring": r"hamstring|thigh",
              "foot": r"foot|feet|plantar", "hand": r"hand|wrist|finger", "mental": r"ptsd|depress|anxiety|mental",
              "head": r"tbi|brain|head|migraine", "ear": r"tinnitus|hearing|\bears?\b", "sleep": r"sleep",
              "breathing": r"asthma|breath|lung", "sinus": r"sinus|rhinitis", "skin": r"scar|skin"}


def areas_for(text):
    t = text.lower()
    return [a for a, rx in AREA_WORDS.items() if re.search(rx, t)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    for a in ("--claims", "--questions", "--duties", "--intake", "--pages", "--id", "--answers", "--ids", "--note"):
        ap.add_argument(a)
    a = ap.parse_args()

    if a.cmd == "plan":
        C = json.load(open(a.claims)); Q = json.load(open(a.questions)); D = json.load(open(a.duties))
        vet_duties = set()
        if a.intake:
            vet_duties = set(json.load(open(a.intake)).get("service_duties", {}).get("ids", []))
        out = []
        for c in C["claims"]:
            if c.get("vet_status", "confirmed") != "confirmed":
                continue
            fams = []
            for dc in c.get("dc", []):
                for code in re.findall(r"\d{4}", dc):
                    f = Q["dc_to_family"].get(code)
                    if f and f not in fams:
                        fams.append(f)
            ar = areas_for(c["condition"] + " " + c.get("system", ""))
            if c.get("system", "").lower().startswith("skin"):
                ar = ["skin"]  # scars come from the injuries/surgeries already claimed
            likely = [d["id"] for d in D["duties"] if set(d["areas"]) & set(ar)]
            out.append({"id": c["id"], "condition": c["condition"], "families": fams, "areas": ar,
                        "duties_offer": likely, "duties_precheck": [x for x in likely if x in vet_duties],
                        "questions_for_vet": c.get("questions_for_vet", []), "done": bool(c.get("details"))})
        print(json.dumps(out, indent=1))

    elif a.cmd == "duties":
        D = json.load(open(a.duties))
        rx = {d["id"]: re.compile(d["terms"], re.I) for d in D["duties"]}
        hits = {k: [] for k in rx}
        op = gzip.open if a.pages.endswith(".gz") else open
        with op(a.pages, "rt", encoding="utf-8") as f:
            for line in f:
                p = json.loads(line)
                if p.get("dup_of") is not None:
                    continue
                t = re.sub(r"\s+", " ", p["text"])
                for k, r in rx.items():
                    m = None
                    for mm in r.finditer(t):
                        sent = t[max(0, t.rfind(".", 0, mm.start())):t.find(".", mm.end()) if t.find(".", mm.end()) > 0 else len(t)]
                        if "?" not in sent and not re.search(r"\b(no|denies|denied|not)\b", t[max(0, mm.start() - 30):mm.start()], re.I):
                            m = mm; break
                    if m and len(hits[k]) < 8:
                        hits[k].append({"file": p["file"], "page": p["page"], "context": t[max(0, m.start() - 120):m.end() + 160]})
        print(json.dumps({k: v for k, v in hits.items() if v}, indent=1))

    elif a.cmd == "save":
        C = json.load(open(a.claims)); ans = json.load(open(a.answers))
        for c in C["claims"]:
            if c["id"] == a.id:
                ans["saved"] = date.today().isoformat()
                c["details"] = ans
                json.dump(C, open(a.claims, "w"), indent=1); print("saved"); return
        sys.exit("no such claim")

    elif a.cmd == "setduties":
        I = json.load(open(a.intake))
        I["service_duties"] = {"ids": [x for x in (a.ids or "").split(",") if x], "note": a.note or "", "saved": date.today().isoformat()}
        json.dump(I, open(a.intake, "w"), indent=2); print("saved")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
