"""Offline tests for cfr_update.run using a fake fetch. Run: python3 test_cfr_update.py"""

_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import json, os, tempfile
from cfr_update import run

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.path.join(HERE, "..", "references", "cfr")
P3 = os.path.join(BUNDLED, "_test_part3.xml")
fails = 0
def check(n, c):
    global fails; print(("PASS " if c else "FAIL ") + n); fails += 0 if c else 1

MINI = {"3": b'<DIV5 N="3" TYPE="PART"><HEAD>PART 3</HEAD><DIV6 N="A"><HEAD>Subpart A</HEAD><DIV8 N="3.1"><HEAD>\xc2\xa7 3.1 Definitions.</HEAD><P>Test.</P></DIV8></DIV6></DIV5>',
        "4": b'<DIV5 N="4" TYPE="PART"><HEAD>PART 4</HEAD><DIV6 N="A"><HEAD>Subpart A</HEAD><DIV8 N="4.1"><HEAD>\xc2\xa7 4.1 Essentials.</HEAD><TABLE><TR><TD>8100 Migraine:</TD><TD/></TR></TABLE></DIV8></DIV6></DIV5>'}

def fake(newest, up_to="2027-03-01"):
    def f(url):
        if url.endswith("titles.json"):
            return json.dumps({"titles": [{"number": 38, "up_to_date_as_of": up_to}]}).encode()
        if "/versions/" in url:
            return json.dumps({"content_versions": [{"amendment_date": "2020-01-01"}, {"amendment_date": newest}]}).encode()
        if "/full/" in url:
            return MINI[url.split("part=")[1]]
        raise AssertionError(url)
    return f

def offline(url): raise OSError("no network")

local = tempfile.mkdtemp()
r = run(BUNDLED, local, offline);                 check("offline -> bundled", r["status"] == "offline" and r["use_dir"] == BUNDLED)
r = run(BUNDLED, local, fake("2025-06-01"));      check("no newer change -> up_to_date", r["status"] == "up_to_date")
r = run(BUNDLED, local, fake("2027-02-15"));      check("newer change -> updated", r["status"] == "updated" and r["as_of"] == "2027-03-01")
check("updated files written", os.path.exists(os.path.join(local, "part-4", "4.1.md")))
r = run(BUNDLED, local, fake("2027-02-15"));      check("second run uses local copy, up_to_date", r["status"] == "up_to_date" and r["use_dir"] == local)
r = run(BUNDLED, local, offline);                 check("offline later -> newer local copy", r["use_dir"] == local)
print("\n" + ("ALL PASSED" if not fails else f"{fails} FAILED")); raise SystemExit(1 if fails else 0)
