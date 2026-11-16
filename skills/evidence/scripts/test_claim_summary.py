"""Tests for the quote check and 526EZ list limits. Run: python3 test_claim_summary.py"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove
from claim_summary import quote_ok, norm
from ez_list import check

page = norm("Op Date: 10 Dec 02. Doe is a 19 y/o cadet who injured his right Knee while wrestling in October 2002.")
assert quote_ok("cadet who injured his right Knee while wrestling", page)[0]
assert quote_ok("19 y/o cadet ... while wrestling in October 2002", page)[0]
assert not quote_ok("injured his knee during combat deployment", page)[0]
assert not quote_ok("cadet", page)[0]  # too short to prove anything
assert check([{"id": "C1", "disability": "X" * 46}])
assert check([{"id": "C1", "disability": "KNEE", "date": "2020-04"}])
assert not check([{"id": "C1", "disability": "KNEE", "date": "04/2020"}])
print("ALL PASSED")
