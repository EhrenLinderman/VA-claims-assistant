#!/usr/bin/env python3
"""
VA Claims Assistant - the Veteran's status bar.
Reads progress.json + Claims/claims.json and shows where the Veteran is:
major steps ticked off, then each claim with its own stages
(Found -> Confirmed -> Described -> Evidence -> Written).
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

  python3 status.py bar   --out <VA-Claim-Output>     one line for the top of a screen
  python3 status.py board --out <VA-Claim-Output>     full board (Markdown) for the chat
  python3 status.py html  --out <VA-Claim-Output>     writes My-Progress.html in that folder
  python3 status.py json  --out <VA-Claim-Output>     the computed status (for other tools)

PORT-TO-APP: keep this feature in any future version (web, desktop or mobile app).
`json` is the platform-neutral contract: an app can draw its own progress bar or
sidebar from it, and `html` already works in any browser. See porting-notes.md.
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, html, json, os, re
from datetime import date

MAJOR = [  # key in progress.json -> plain name shown to the Veteran
    ("start", "Set up your folder"),
    ("intake", "About your service & key dates"),
    ("cfr", "Get the latest VA rules"),
    ("records", "Read your records"),
    ("claims_work", "Work each claim"),       # computed from the per-claim stages
    ("evidence", "Build your claim packet"),
    ("file", "Final check & file with VA"),
]
STAGES = [("found", "Found"), ("confirmed", "Confirmed"), ("described", "Described"),
          ("evidence", "Evidence"), ("written", "Written")]
STAGE_WEIGHT = {"found": 1, "confirmed": 1, "described": 3, "evidence": 2, "written": 3}
NEEDS = {"diagnosis": "a current diagnosis", "in_service": "proof from service", "nexus": "a doctor's link"}
ICON = {"done": "✅", "in_progress": "▶", "partial": "◐", "not_started": "○", "skipped": "⏭", "removed": "➖"}


def short(name, n=34):
    s = re.split(r"\s*[(:,]", name)[0].strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def claim_status(c):
    st = {"found": "done"}
    vs = c.get("vet_status", "pending")
    st["confirmed"] = {"confirmed": "done", "removed": "removed"}.get(vs, "in_progress")
    d, s = c.get("details") or {}, c.get("story")
    parts = [bool(d.get("answers") or d.get("duties")), bool(s), bool(isinstance(d.get("impact"), dict))]
    st["described"] = "skipped" if d.get("skipped") else ("done" if all(parts) else "partial" if any(parts) else "not_started")
    el = c.get("elements", {})
    have = [k for k in NEEDS if el.get(k) == "found"]
    if (c.get("evidence_check") or {}).get("status") == "done" or (len(have) == 3 and c.get("evidence")):
        st["evidence"] = "done"
    else:
        st["evidence"] = "partial" if have else "not_started"
    w = (c.get("writeup") or {}).get("status")
    st["written"] = {"done": "done", "draft": "partial"}.get(w, "not_started")
    missing = [NEEDS[k] for k in NEEDS if el.get(k) != "found"]
    return st, f"{len(have)}/3", missing


def compute(out):
    P = json.load(open(os.path.join(out, "progress.json")))
    cf = os.path.join(out, "Claims", "claims.json")
    C = json.load(open(cf))["claims"] if os.path.exists(cf) else []
    steps = P.get("steps", {})
    rows, n_conf, units, done_units = [], 0, 0, 0.0
    for c in C:
        st, ev, missing = claim_status(c)
        rows.append({"id": c["id"], "name": short(c["condition"]), "full": c["condition"],
                     "strength": c.get("strength", ""), "stages": st, "evidence_count": ev, "needs": missing,
                     "removed": st["confirmed"] == "removed", "current": P.get("current_claim") == c["id"]})
        if st["confirmed"] == "removed":
            continue
        n_conf += 1
        for k, _ in STAGES:  # describing and writing are most of the Veteran's work
            wt = STAGE_WEIGHT[k]
            units += wt
            done_units += wt * {"done": 1, "skipped": 1, "partial": .5, "in_progress": .25}.get(st[k], 0)
    claim_frac = (done_units / units) if units else 0
    if claim_frac >= 1:
        cw = "done"
    elif steps.get("claims") in ("in_progress", "done") or claim_frac > 0:
        cw = "in_progress"
    else:
        cw = "not_started"
    major = []
    for k, label in MAJOR:
        s = cw if k == "claims_work" else steps.get(k, "not_started")
        major.append({"key": k, "label": label, "status": s})
    # weights: setup steps 30%, claims 55%, packet 10%, filing 5%
    w = {"start": 3, "intake": 7, "cfr": 3, "records": 17, "evidence": 10, "file": 5}
    pct = sum(v for k, v in w.items() if steps.get(k) == "done") + 55 * claim_frac
    pct += sum(v * .5 for k, v in w.items() if steps.get(k) == "in_progress")
    cur = next((m for m in major if m["status"] == "in_progress"), next((m for m in major if m["status"] == "not_started"), None))
    return {"pct": round(min(pct, 100)), "major": major, "claims": rows, "n_confirmed": n_conf,
            "n_described": sum(1 for r in rows if not r["removed"] and r["stages"]["described"] in ("done", "skipped")),
            "current": cur, "current_claim": next((r for r in rows if r["current"]), None),
            "updated": P.get("updated", "")}


def meter(pct, n=10):
    k = round(pct / 100 * n)
    return "▓" * k + "░" * (n - k)


def bar(S):
    i = next((n for n, m in enumerate(S["major"], 1) if m is S["current"]), len(S["major"]))
    line = f'**Your progress** {meter(S["pct"])} {S["pct"]}% · Step {i} of {len(S["major"])}: {S["current"]["label"] if S["current"] else "All done"}'
    if S["current"] and S["current"]["key"] == "claims_work":
        line += f' · {S["n_described"]} of {S["n_confirmed"]} claims described'
        if S["current_claim"]:
            line += f' · Now: {S["current_claim"]["name"]}'
    return line


def board(S):
    out = [bar(S), ""]
    for n, m in enumerate(S["major"], 1):
        out.append(f'{ICON[m["status"]]} {n}. {m["label"]}' + ("  ← you are here" if m is S["current"] else ""))
        if m["key"] == "claims_work" and S["claims"]:
            out.append("")
            out.append("| | Claim | " + " | ".join(l for _, l in STAGES) + " |")
            out.append("|---|---|" + "---|" * len(STAGES))
            for r in S["claims"]:
                if r["removed"]:
                    out.append(f'| ➖ | ~~{r["name"]}~~ | left out | | | | |')
                    continue
                cells = []
                for k, _ in STAGES:
                    s = r["stages"][k]
                    cells.append(r["evidence_count"] if k == "evidence" and s == "partial" else ICON[s])
                out.append(f'| {"▶" if r["current"] else ""} | {r["name"]} | ' + " | ".join(cells) + " |")
            out.append("")
    out.append("✅ done · ▶ working on it · ◐ partly done · ○ not yet · Evidence ✅ = all 3 things VA needs (a current diagnosis, proof from service, a doctor's link) are backed by pages in your records; otherwise it shows how many are.")
    return "\n".join(out)


CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#1d2330;--muted:#5d6676;--line:#e3e6ec;--blue:#2a78d6;--green:#1baf7a;--amber:#d98a00;--track:#e6ebf2}
@media (prefers-color-scheme:dark){:root{--bg:#12151b;--card:#1b2029;--ink:#e8ebf0;--muted:#9aa3b2;--line:#2c333f;--blue:#5a9be6;--green:#2fc48d;--amber:#f0a92a;--track:#2a313c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:880px;margin:0 auto;padding:24px 16px 48px}h1{font-size:1.5rem;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:16px}
.meter{height:12px;background:var(--track);border-radius:99px;overflow:hidden;margin:10px 0 4px}.meter i{display:block;height:100%;background:var(--blue);border-radius:99px}
.big{font-size:1.1rem;font-weight:600}ol.steps{list-style:none;margin:0;padding:0}
ol.steps li{display:flex;gap:12px;align-items:center;padding:10px 0;border-top:1px solid var(--line)}ol.steps li:first-child{border-top:0}
.dot{flex:0 0 28px;height:28px;border-radius:50%;display:grid;place-items:center;font-size:.85rem;font-weight:700;border:2px solid var(--line);color:var(--muted)}
.done .dot{background:var(--green);border-color:var(--green);color:#fff}.in_progress .dot{border-color:var(--blue);color:var(--blue)}
.here{margin-left:auto;font-size:.8rem;color:var(--blue);font-weight:600;white-space:nowrap}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}.sh{display:none}
@media (max-width:560px){table{table-layout:fixed}th:not(:first-child){width:46px}td.name{overflow-wrap:anywhere}.card{padding:14px 10px}thead th{letter-spacing:0;font-size:.72rem;text-transform:none}table th,table td{padding:7px 2px}.lg{display:none}.sh{display:inline}.s{min-width:18px;padding:1px 3px;font-size:.72rem}td.name{font-size:.88rem}}th,td{padding:8px 6px;text-align:center;border-top:1px solid var(--line);font-size:.92rem}
th{font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);border-top:0}td.name{text-align:left;font-weight:500}
tr.cur td{background:color-mix(in srgb,var(--blue) 9%,transparent)}tr.removed td{color:var(--muted);text-decoration:line-through}
.s{display:inline-block;min-width:28px;padding:2px 6px;border-radius:99px;font-size:.8rem;font-weight:600}
.s.done{background:var(--green);color:#fff}.s.partial,.s.in_progress{background:color-mix(in srgb,var(--amber) 22%,transparent);color:var(--amber)}
.s.not_started{color:var(--muted)}.s.skipped{color:var(--muted)}.needs{display:block;font-size:.75rem;color:var(--muted);font-weight:400}
.legend,.foot{color:var(--muted);font-size:.85rem}.foot{margin-top:24px}
"""


def html_page(S):
    e = html.escape
    lab = {"done": "✓", "in_progress": "…", "partial": "½", "not_started": "–", "skipped": "skip", "removed": "–"}
    steps = "".join(
        f'<li class="{m["status"]}"><span class="dot">{"✓" if m["status"] == "done" else n}</span>'
        f'<span>{e(m["label"])}</span>{"<span class=here>You are here</span>" if m is S["current"] else ""}</li>'
        for n, m in enumerate(S["major"], 1))
    rows = []
    for r in S["claims"]:
        if r["removed"]:
            rows.append(f'<tr class="removed"><td class="name">{e(r["name"])}</td><td colspan="{len(STAGES)}">left out</td></tr>')
            continue
        cells = []
        for k, _ in STAGES:
            s = r["stages"][k]
            t = r["evidence_count"] if (k == "evidence" and s == "partial") else lab[s]
            cells.append(f'<td><span class="s {s}">{e(t)}</span></td>')
        need = f'<span class="needs">Still needs: {e(", ".join(r["needs"]))}</span>' if r["needs"] else ""
        rows.append(f'<tr class="{"cur" if r["current"] else ""}"><td class="name" title="{e(r["full"])}">{e(r["name"])}{need}</td>{"".join(cells)}</tr>')
    SH = {"found": "Found", "confirmed": "OK", "described": "Desc.", "evidence": "Evid.", "written": "Write"}
    head = "".join(f'<th><span class="lg">{e(l)}</span><span class="sh">{e(SH[k])}</span></th>' for k, l in STAGES)
    claim_line = f'{S["n_described"]} of {S["n_confirmed"]} claims described'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>My VA Claim Progress</title><style>{CSS}</style></head><body><main>
<h1>My VA Claim Progress</h1><p class="sub">Updated {e(S["updated"] or date.today().isoformat())} · This page stays in your own folder.</p>
<section class="card"><div class="big">{S["pct"]}% done</div><div class="meter" role="progressbar" aria-valuenow="{S["pct"]}" aria-valuemin="0" aria-valuemax="100"><i style="width:{S["pct"]}%"></i></div>
<div class="legend">{e(claim_line)}</div></section>
<section class="card"><ol class="steps">{steps}</ol></section>
<section class="card"><div class="big" style="margin-bottom:8px">Your claims</div><div class="scroll"><table>
<thead><tr><th style="text-align:left">Claim</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p class="legend">✓ done · ½ partly done · – not yet · Evidence ✓ means all 3 things VA needs (a current diagnosis, proof from service, a doctor's link) are backed by pages in your records; otherwise it shows how many are.</p></section>
<p class="foot">VA Claims Assistant is FREE. No one may charge you to prepare an initial VA claim. Report it: VSAFE.gov or 1-833-38V-SAFE. · Created by EhrenAL Not legal advice. Not affiliated with or endorsed by VA. AI can make mistakes: check everything against your records before filing.</p>
</main></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bar", "board", "html", "json"])
    ap.add_argument("--out", required=True, help="the VA-Claim-Output folder")
    a = ap.parse_args()
    S = compute(a.out)
    if a.cmd == "bar":
        print(bar(S))
    elif a.cmd == "board":
        print(board(S))
    elif a.cmd == "html":
        p = os.path.join(a.out, "My-Progress.html")
        open(p, "w", encoding="utf-8").write(html_page(S))
        print(p)
    else:
        print(json.dumps(S, indent=1, default=str))


if __name__ == "__main__":
    main()
