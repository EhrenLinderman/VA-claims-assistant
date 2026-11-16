#!/usr/bin/env python3
"""
VA Claims Assistant - filing-window and Intent to File calculator.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0).

Pure standard-library Python 3 so it runs anywhere. Prints JSON.

Rules (sources: VA.gov pre-discharge, effective-date, and intent-to-file pages;
38 CFR 3.155 and 3.400(b)(2)):
  * BDD: file 180 to 90 days before separation; must be available for VA exams
    within 45 days of filing.
  * Fewer than 90 days before separation: may still file a pre-discharge claim
    (standard process); VA may not process it until after discharge.
  * Claim received within 1 year after separation: effective date can be as early
    as the day after separation.
  * After that: effective date is generally the date VA receives the claim (or
    the date of the Intent to File, if a complete claim follows within 1 year).
  * Intent to File: complete claim must be filed within 1 year of the ITF.

Deadlines are CONSERVATIVE: "file no later than" = one day before the 1-year
anniversary, and a "target" date 30 days earlier is suggested as a safety buffer.

Usage:
  python3 filing_window.py --separation 2026-12-31 [--itf 2026-05-01] [--today 2026-10-05]
"""

_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse
import json
from datetime import date, timedelta

BUFFER_DAYS = 30


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29 -> Feb 28
        return d.replace(year=d.year + years, day=28)


def fmt(d):
    return d.isoformat() if d else None


def nice(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}" if d else None


def calculate(separation: date, today: date, itf: date | None = None) -> dict:
    out = {"today": fmt(today), "separation_date": fmt(separation)}
    days_to_sep = (separation - today).days
    one_year_mark = add_years(separation, 1)          # anniversary
    one_year_nlt = one_year_mark - timedelta(days=1)  # conservative last day

    dates = {}
    actions = []

    if days_to_sep > 180:
        window = "before_bdd"
        bdd_open = separation - timedelta(days=180)
        bdd_close = separation - timedelta(days=90)
        dates["bdd_opens"] = fmt(bdd_open)
        dates["bdd_closes_nlt"] = fmt(bdd_close)
        summary = (f"You are more than 180 days from separation. The fast-track BDD "
                   f"window opens {nice(bdd_open)} and closes {nice(bdd_close)}.")
        actions += ["gather_records", "plan_bdd"]
    elif days_to_sep >= 90:
        window = "bdd"
        bdd_close = separation - timedelta(days=90)
        dates["bdd_closes_nlt"] = fmt(bdd_close)
        dates["bdd_target"] = fmt(max(today, bdd_close - timedelta(days=min(BUFFER_DAYS, (bdd_close - today).days))))
        summary = (f"You are in the BDD window (180 to 90 days before separation). "
                   f"File by {nice(bdd_close)} to use BDD. You must be available for "
                   f"VA exams within 45 days after you file.")
        actions += ["file_bdd", "confirm_exam_availability"]
    elif days_to_sep > 0:
        window = "pre_discharge_under_90"
        dates["bdd_closed_on"] = fmt(separation - timedelta(days=90))
        summary = ("You have fewer than 90 days until separation. BDD is closed, but you "
                   "can still file a pre-discharge claim. VA may not process it until "
                   "after you separate.")
        actions += ["file_pre_discharge_or_itf"]
    elif today <= one_year_nlt:
        window = "first_year"
        summary = (f"You are in your first year after separation. File by "
                   f"{nice(one_year_nlt)} so your benefits can start the day after "
                   f"you separated.")
        actions += ["file_itf_now", "file_before_one_year"]
    else:
        window = "after_first_year"
        summary = ("It has been more than a year since separation. There is no deadline "
                   "to file, but benefits generally start from the date VA receives your "
                   "claim or Intent to File, so filing an Intent to File now protects that date.")
        actions += ["file_itf_now"]

    if window in ("before_bdd", "bdd", "pre_discharge_under_90", "first_year"):
        dates["one_year_after_separation_nlt"] = fmt(one_year_nlt)
        dates["one_year_target"] = fmt(one_year_nlt - timedelta(days=BUFFER_DAYS))

    itf_info = None
    if itf:
        itf_nlt = add_years(itf, 1) - timedelta(days=1)
        expired = today > itf_nlt
        filed_in_first_year = (itf > separation) and (itf <= one_year_nlt) if separation else False
        itf_info = {
            "itf_date": fmt(itf),
            "complete_claim_nlt": fmt(itf_nlt),
            "complete_claim_target": fmt(itf_nlt - timedelta(days=BUFFER_DAYS)),
            "days_left": (itf_nlt - today).days,
            "expired": expired,
            "filed_within_first_year_after_separation": filed_in_first_year,
        }
        if expired:
            actions = [a for a in actions if a != "file_itf_now"] + ["file_new_itf_now"]
        else:
            actions = [a for a in actions if a != "file_itf_now"] + ["file_claim_before_itf_deadline"]
    elif window in ("first_year", "after_first_year", "pre_discharge_under_90"):
        if "file_itf_now" not in actions:
            actions.append("consider_itf")

    # The single most important date to show the Veteran.
    candidates = []
    if itf_info and not itf_info["expired"]:
        candidates.append(("Intent to File deadline", date.fromisoformat(itf_info["complete_claim_nlt"])))
    if "bdd_closes_nlt" in dates and window == "bdd":
        candidates.append(("BDD window closes", date.fromisoformat(dates["bdd_closes_nlt"])))
    itf_protects_first_year = bool(itf_info and not itf_info["expired"]
                                   and itf_info["filed_within_first_year_after_separation"])
    if window in ("first_year", "pre_discharge_under_90", "before_bdd", "bdd") and not itf_protects_first_year:
        candidates.append(("One year after separation", one_year_nlt))
    if itf_protects_first_year:
        out["note"] = ("Your Intent to File was filed within a year of separation. If you file "
                       "your complete claim by the Intent to File deadline, benefits can still "
                       "start the day after you separated.")
    key = min(candidates, key=lambda c: c[1]) if candidates else None

    out.update({
        "days_until_separation": days_to_sep,
        "window": window,
        "summary": summary,
        "dates": dates,
        "intent_to_file": itf_info,
        "key_deadline": {"label": key[0], "date": fmt(key[1]), "days_left": (key[1] - today).days} if key else None,
        "actions": actions,
        "buffer_days": BUFFER_DAYS,
    })
    if "note" in out:
        out["summary"] = "You are in your first year after separation. " + out.pop("note")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--separation", required=True, help="Separation date YYYY-MM-DD (past or expected)")
    p.add_argument("--itf", help="Intent to File date YYYY-MM-DD, if already filed")
    p.add_argument("--today", help="Override today's date (testing) YYYY-MM-DD")
    a = p.parse_args()
    today = date.fromisoformat(a.today) if a.today else date.today()
    res = calculate(date.fromisoformat(a.separation), today,
                    date.fromisoformat(a.itf) if a.itf else None)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
