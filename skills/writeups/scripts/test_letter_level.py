"""Doctor's letter levels (answer-key lesson). Run: python3 test_letter_level.py"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove
from writeups_tools import letter_level

I = {"separation_date": "2027-03-01", "filing_window": {"window": "bdd"}}
ev = [{"role": "diagnosis", "date": "2025-06-06"}]
assert letter_level({"vet_status": "confirmed", "elements": {"nexus": "found"}, "evidence": ev}, I) == "no"
assert letter_level({"vet_status": "confirmed", "elements": {}, "evidence": ev, "type": "direct"}, I) == "optional"
assert letter_level({"vet_status": "confirmed", "elements": {}, "evidence": ev, "type": "aggravation"}, I) == "needed"
late = {"separation_date": "2020-01-01", "filing_window": {"window": "after_first_year"}}
assert letter_level({"vet_status": "confirmed", "elements": {}, "evidence": ev, "type": "direct"}, late) == "needed"
assert letter_level({"vet_status": "removed", "elements": {}, "evidence": ev}, I) == "no"
print("ALL PASSED")
