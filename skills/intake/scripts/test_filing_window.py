"""Run: python3 test_filing_window.py  (no dependencies)."""

_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

from datetime import date
from filing_window import calculate, add_years

T = date(2026, 10, 5)
fails = 0

def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name)
    fails += 0 if cond else 1

r = calculate(date(2027, 6, 1), T);              check("200+ days out -> before_bdd", r["window"] == "before_bdd")
check("bdd opens 180 days before", r["dates"]["bdd_opens"] == "2026-12-03")
r = calculate(T.replace(day=5) .__class__(2027, 2, 2), T); check("120 days -> bdd", r["window"] == "bdd")
check("bdd closes 90 days before", r["dates"]["bdd_closes_nlt"] == "2026-11-04")
r = calculate(date(2027, 1, 3), T);              check("exactly 90 days -> bdd", r["window"] == "bdd")
r = calculate(date(2027, 1, 2), T);              check("89 days -> pre_discharge_under_90", r["window"] == "pre_discharge_under_90")
r = calculate(date(2027, 4, 3), T);              check("exactly 180 days -> bdd", r["window"] == "bdd")
r = calculate(date(2027, 4, 4), T);              check("181 days -> before_bdd", r["window"] == "before_bdd")
r = calculate(date(2026, 3, 1), T);              check("separated 7 months ago -> first_year", r["window"] == "first_year")
check("one-year NLT is day before anniversary", r["dates"]["one_year_after_separation_nlt"] == "2027-02-28")
check("key deadline is one-year mark", r["key_deadline"]["label"] == "One year after separation")
r = calculate(date(2026, 10, 6), T);             check("separation tomorrow -> under 90", r["window"] == "pre_discharge_under_90")
r = calculate(T, T);                             check("separating today -> first_year", r["window"] == "first_year")
r = calculate(date(2025, 10, 6), T);             check("last day of first year", r["window"] == "first_year")
r = calculate(date(2025, 10, 5), T);             check("anniversary -> after_first_year", r["window"] == "after_first_year")
r = calculate(date(2020, 1, 1), T, itf=date(2026, 1, 15))
check("ITF deadline", r["intent_to_file"]["complete_claim_nlt"] == "2027-01-14")
check("ITF active", r["intent_to_file"]["expired"] is False)
check("key deadline = ITF", r["key_deadline"]["label"] == "Intent to File deadline")
r = calculate(date(2020, 1, 1), T, itf=date(2025, 1, 15)); check("ITF expired", r["intent_to_file"]["expired"] and "file_new_itf_now" in r["actions"])
r = calculate(date(2026, 3, 1), T, itf=date(2026, 4, 1))
check("ITF in first year flagged", r["intent_to_file"]["filed_within_first_year_after_separation"])
check("ITF in first year -> key deadline is ITF (later)", r["key_deadline"]["label"] == "Intent to File deadline" and r["key_deadline"]["date"] == "2027-03-31")
check("leap day handled", add_years(date(2028, 2, 29), 1) == date(2029, 2, 28))

r = calculate(date(2027, 1, 1), date(2026, 10, 9))
check("under 90 has key deadline = one year after separation", r["key_deadline"] and r["key_deadline"]["date"] == "2027-12-31")
check("under 90 shows when BDD closed", r["dates"]["bdd_closed_on"] == "2026-10-03")
r = calculate(date(2027, 2, 2), T)
check("bdd window key deadline is BDD close (earlier)", r["key_deadline"]["label"] == "BDD window closes")
r = calculate(date(2027, 6, 1), T)
check("before_bdd key deadline = one year after separation", r["key_deadline"]["label"] == "One year after separation")
print(f"\n{'ALL PASSED' if not fails else str(fails) + ' FAILED'}")
raise SystemExit(1 if fails else 0)
