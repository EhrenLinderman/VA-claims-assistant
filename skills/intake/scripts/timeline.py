#!/usr/bin/env python3
"""
VA Claims Assistant - claim timeline (estimates) as JSON + a self-contained SVG.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0).
Standard library only.

Usage:
  python3 timeline.py --separation 2027-03-01 [--file-by 2026-11-01] [--itf YYYY-MM-DD]
                      [--today YYYY-MM-DD] [--avg-days 68] [--build-days 21] [--svg out.svg]

Sources for the estimates (update AVG_DAYS when VA posts a new number):
  * VA.gov "The VA claim process after you file your claim": average 68.2 days to
    complete disability-related claims (September 2026; page updated 2026-10-05).
  * VA.gov pre-discharge (BDD): file 180-90 days before separation; be available for
    VA exams for 45 days from the date you apply.
  * 38 CFR 3.31: payment starts the first day of the month after the effective date.
  * VA Form 21-8764: payments are made at the beginning of each month for the prior month.
Everything after "file" is an ESTIMATE, labeled as such.
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, json, os, sys
from datetime import date, timedelta
from html import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filing_window import calculate, add_years  # noqa: E402

AVG_DAYS = 69          # VA average days to complete (Oct 2026: 69.2)
AVG_SOURCE = "VA.gov average, Sept 2026 (68.2 days)"
EXAM_WINDOW = 45       # BDD: available for exams 45 days from filing
BUILD_DAYS = 21        # typical time to build the claim with this app (estimate)


def first_of_next_month(d):
    return date(d.year + (d.month // 12), d.month % 12 + 1, 1)


def nice(d):
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def build(separation, today, file_by=None, itf=None, avg_days=AVG_DAYS, build_days=BUILD_DAYS):
    fw = calculate(separation, today, itf)
    target = None
    if file_by:
        target = file_by
    elif fw["window"] == "bdd":
        target = date.fromisoformat(fw["dates"]["bdd_target"])
    else:
        target = today + timedelta(days=build_days)
    target = max(target, today + timedelta(days=7))
    build_end = target

    bars, marks = [], []
    bars.append({"lane": "You", "label": "Build your claim with this app", "start": today, "end": build_end,
                 "who": "you", "note": "Gather records, review claims, write statements (estimate)"})
    if fw["window"] in ("before_bdd", "bdd"):
        bdd_open = separation - timedelta(days=180)
        bdd_close = separation - timedelta(days=90)
        bars.append({"lane": "BDD", "label": "BDD window (fast track)", "start": bdd_open, "end": bdd_close,
                     "who": "window", "note": "File 180 to 90 days before separation"})
        marks.append({"label": "BDD closes", "date": bdd_close, "kind": "deadline"})

    pre_sep = target < separation
    exam_start = target + timedelta(days=7)
    exam_end = target + timedelta(days=EXAM_WINDOW if pre_sep else 60)
    bars.append({"lane": "VA", "label": "VA medical exams (approx.)", "start": exam_start, "end": exam_end,
                 "who": "va", "note": ("Be available for VA exams for 45 days after you file"
                                      if pre_sep else "VA schedules exams; times vary (estimate)")})

    if pre_sep:
        dec_start = separation
        dec_end = separation + timedelta(days=avg_days)
        dec_note = "Decision expected after you separate (estimate)"
    else:
        dec_start = target + timedelta(days=max(30, avg_days // 2))
        dec_end = target + timedelta(days=avg_days + 30)
        dec_note = f"Based on {AVG_SOURCE}; varies by claim (estimate)"
    bars.append({"lane": "VA", "label": "Expected rating decision", "start": dec_start, "end": dec_end,
                 "who": "va", "note": dec_note})

    one_year_nlt = add_years(separation, 1) - timedelta(days=1)
    within_year = target <= one_year_nlt or (fw["intent_to_file"] and fw["intent_to_file"].get("filed_within_first_year_after_separation"))
    effective = separation + timedelta(days=1) if within_year else (itf or target)
    pay_start = first_of_next_month(effective)
    first_payment = max(first_of_next_month(pay_start), first_of_next_month(dec_end))

    marks += [
        {"label": "Today", "date": today, "kind": "now"},
        {"label": "Goal: file claim", "date": target, "kind": "goal"},
        {"label": "Separation", "date": separation, "kind": "key"},
        {"label": "Benefits start (effective date)", "date": effective, "kind": "key"},
        {"label": "First VA payment (approx.)", "date": first_payment, "kind": "pay"},
    ]
    if fw["window"] in ("first_year", "pre_discharge_under_90", "bdd", "before_bdd"):
        marks.append({"label": "Last day to keep start date", "date": one_year_nlt, "kind": "deadline"})

    return {"filing_window": fw, "goal_file_date": target, "effective_date": effective,
            "payment_start": pay_start, "first_payment_est": first_payment,
            "bars": bars, "marks": sorted(marks, key=lambda m: m["date"]), "avg_days": avg_days,
            "avg_source": AVG_SOURCE}


COLORS = {"you": "#2a78d6", "va": "#eb6834", "window": "#1baf7a"}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"


def svg(tl, width=980):
    marks = [m for m in tl["marks"] if m["kind"] != "deadline" or m["label"] == "BDD closes"]
    start = min([b["start"] for b in tl["bars"]] + [m["date"] for m in marks]) - timedelta(days=10)
    end = max([b["end"] for b in tl["bars"]] + [m["date"] for m in marks]) + timedelta(days=20)
    left, right = 230, 30
    span = (end - start).days or 1
    X = lambda d: left + (width - left - right) * (d - start).days / span
    rows = tl["bars"]
    top, row_h = 70, 46
    bars_bottom = top + len(rows) * row_h
    mark_top = bars_bottom + 20
    height = mark_top + len(marks) * 30 + 60
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
         f'font-family="Segoe UI, Helvetica, Arial, sans-serif" role="img" aria-label="VA claim timeline (estimates)">',
         f'<rect width="{width}" height="{height}" fill="#fcfcfb"/>',
         f'<text x="20" y="32" font-size="22" font-weight="700" fill="{INK}">Your VA claim timeline</text>',
         f'<text x="20" y="54" font-size="13" fill="{MUTED}">Dates after you file are estimates. Hover any item for details.</text>']
    # month gridlines
    m = date(start.year, start.month, 1)
    first_tick = True
    while m <= end:
        if m >= start:
            x = X(m)
            o.append(f'<line x1="{x:.1f}" y1="{top-8}" x2="{x:.1f}" y2="{height-50}" stroke="{GRID}" stroke-width="1"/>')
            o.append(f'<text x="{x+3:.1f}" y="{height-34}" font-size="11" fill="{MUTED}">{m.strftime("%b")}</text>')
            if m.month == 1 or first_tick:
                first_tick = False
                o.append(f'<text x="{x+3:.1f}" y="{height-20}" font-size="11" font-weight="700" fill="{MUTED}">{m.year}</text>')
        m = first_of_next_month(m)
    for i, b in enumerate(rows):
        y = top + i * row_h
        x1, x2 = X(b["start"]), max(X(b["end"]), X(b["start"]) + 6)
        c = COLORS[b["who"]]
        tip = escape(f'{b["label"]}: {nice(b["start"])} – {nice(b["end"])}. {b["note"]}')
        o.append(f'<text x="20" y="{y+24}" font-size="14" fill="{INK}">{escape(b["label"])}</text>')
        o.append(f'<g><title>{tip}</title><rect x="{x1:.1f}" y="{y+8}" width="{x2-x1:.1f}" height="22" rx="4" fill="{c}"/>'
                 f'<rect x="{x1-4:.1f}" y="{y}" width="{x2-x1+8:.1f}" height="38" fill="transparent"/></g>')
        lab = f'{nice(b["start"])} – {nice(b["end"])}'
        if x2 + 6 + len(lab) * 6.6 > width - right:
            o.append(f'<text x="{x1-6:.1f}" y="{y+24}" font-size="12" text-anchor="end" fill="{MUTED}">{lab}</text>')
        else:
            o.append(f'<text x="{x2+6:.1f}" y="{y+24}" font-size="12" fill="{MUTED}">{lab}</text>')
    for j, mk in enumerate(marks):
        x = X(mk["date"])
        y = mark_top + j * 30
        o.append(f'<line x1="{x:.1f}" y1="{top-6}" x2="{x:.1f}" y2="{y}" stroke="{INK}" stroke-width="1" stroke-dasharray="3 3" opacity="0.45"/>')
        tip = escape(f'{mk["label"]}: {nice(mk["date"])}')
        o.append(f'<g><title>{tip}</title><path d="M{x:.1f} {y-8} L{x+8:.1f} {y} L{x:.1f} {y+8} L{x-8:.1f} {y} Z" fill="{INK}" stroke="#fcfcfb" stroke-width="2"/>'
                 f'<circle cx="{x:.1f}" cy="{y}" r="14" fill="transparent"/></g>')
        anchor, tx = ("end", x - 14) if x > width * 0.62 else ("start", x + 14)
        o.append(f'<text x="{tx:.1f}" y="{y+5}" font-size="13" text-anchor="{anchor}" fill="{INK}">'
                 f'<tspan font-weight="700">{escape(mk["label"])}</tspan> · {nice(mk["date"])}</text>')
    lx = 20
    for key, lab in (("you", "You"), ("window", "BDD window"), ("va", "VA")):
        if any(b["who"] == key for b in rows):
            o.append(f'<rect x="{lx}" y="{height-14}" width="14" height="10" rx="2" fill="{COLORS[key]}"/>'
                     f'<text x="{lx+20}" y="{height-5}" font-size="12" fill="{INK}">{lab}</text>')
            lx += 110
    o.append(f'<text x="{width-20}" y="{height-5}" font-size="10" text-anchor="end" fill="{MUTED}">VA Claims Assistant · free · created by EhrenAL</text>')
    o.append('</svg>')
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--separation", required=True)
    ap.add_argument("--file-by")
    ap.add_argument("--itf")
    ap.add_argument("--today")
    ap.add_argument("--avg-days", type=int, default=AVG_DAYS)
    ap.add_argument("--build-days", type=int, default=BUILD_DAYS)
    ap.add_argument("--svg")
    a = ap.parse_args()
    d = lambda s: date.fromisoformat(s) if s else None
    tl = build(d(a.separation), d(a.today) or date.today(), d(a.file_by), d(a.itf), a.avg_days, a.build_days)
    if a.svg:
        with open(a.svg, "w", encoding="utf-8") as f:
            f.write(svg(tl))
    print(json.dumps(tl, indent=2, default=str))


if __name__ == "__main__":
    main()
