#!/usr/bin/env python3
"""Tests for status.py. Created by EhrenAL (CC BY-NC-SA 4.0)."""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove
import json, os, tempfile, unittest
from status import compute, bar, board, html_page

EL3 = {"diagnosis": "found", "in_service": "found", "nexus": "found"}


def setup(steps, claims, cur=None):
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "Claims"))
    json.dump({"steps": steps, "current_claim": cur, "updated": "2026-10-09"}, open(os.path.join(d, "progress.json"), "w"))
    json.dump({"claims": claims}, open(os.path.join(d, "Claims", "claims.json"), "w"))
    return d


class T(unittest.TestCase):
    def test_new_claim_folder(self):
        S = compute(setup({"start": "done"}, []))
        self.assertEqual(S["current"]["key"], "intake"); self.assertEqual(S["pct"], 3)

    def test_claim_stages(self):
        c1 = {"id": "C01", "condition": "Right knee (ACL)", "vet_status": "confirmed", "elements": EL3, "evidence": [{}],
              "details": {"answers": {"a": 1}, "impact": {"work": []}}, "story": {"events": []}}
        c2 = {"id": "C02", "condition": "Left knee", "vet_status": "confirmed", "elements": {"diagnosis": "found"}, "evidence": []}
        c3 = {"id": "C03", "condition": "Shoulder", "vet_status": "removed", "elements": {}}
        S = compute(setup({k: "done" for k in ("start", "intake", "cfr", "records", "claims")}, [c1, c2, c3], "C02"))
        r = {x["id"]: x for x in S["claims"]}
        self.assertEqual(r["C01"]["stages"]["described"], "done")
        self.assertEqual(r["C01"]["stages"]["evidence"], "done")
        self.assertEqual(r["C02"]["stages"]["evidence"], "partial"); self.assertEqual(r["C02"]["evidence_count"], "1/3")
        self.assertTrue(r["C03"]["removed"]); self.assertEqual(S["n_confirmed"], 2); self.assertEqual(S["n_described"], 1)
        self.assertEqual(S["current"]["key"], "claims_work")
        self.assertIn("Now: Left knee", bar(S)); self.assertIn("~~Shoulder~~", board(S))
        self.assertIn("My VA Claim Progress", html_page(S))

    def test_all_done(self):
        c = {"id": "C01", "condition": "X", "vet_status": "confirmed", "elements": EL3, "evidence": [{}],
             "details": {"answers": {"a": 1}, "impact": {}}, "story": {"events": []}, "writeup": {"status": "done"}}
        S = compute(setup({k: "done" for k in ("start", "intake", "cfr", "records", "claims", "evidence", "file")}, [c]))
        self.assertEqual(S["pct"], 100); self.assertIsNone(S["current"])


if __name__ == "__main__":
    unittest.main()
