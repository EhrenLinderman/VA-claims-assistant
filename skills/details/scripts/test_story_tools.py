#!/usr/bin/env python3
"""Tests for story_tools.waits. Created by EhrenAL (CC BY-NC-SA 4.0)."""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove
import unittest
from story_tools import waits, months


def ev(d, k, **kw):
    return {"date": d, "kind": k, **kw}


class T(unittest.TestCase):
    def test_simple(self):
        w = waits([ev("2020-04", "start"), ev("2020-12-07", "surgery")])
        self.assertEqual(len(w), 1); self.assertAlmostEqual(w[0]["months"], 7.8, delta=0.3)

    def test_new_episode_skipped_without_injury(self):
        w = waits([ev("2002-10", "start"), ev("2002-12-10", "surgery"), ev("2004-03-30", "surgery")])
        self.assertEqual(len(w), 1)

    def test_staged_counts_from_injury(self):
        w = waits([ev("2020-04", "worse", injury=True), ev("2020-12-07", "surgery"), ev("2021-04-21", "surgery", staged=True)])
        self.assertEqual([round(x["months"]) for x in w], [8, 12])

    def test_first_seen_only_when_different(self):
        w = waits([ev("2020-04", "start"), ev("2020-04-16", "test"), ev("2020-12-07", "surgery")])
        self.assertEqual(len(w), 1)
        w = waits([ev("2020-01", "start"), ev("2020-07-02", "care_wait"), ev("2020-12-07", "surgery")])
        self.assertEqual(len(w), 2)

    def test_worse_without_injury_is_not_a_start(self):
        w = waits([ev("2022-01-28", "start"), ev("2022-02", "worse"), ev("2022-03-15", "surgery")])
        self.assertEqual(len(w), 1); self.assertAlmostEqual(w[0]["months"], 1.5, delta=0.1)

    def test_undated_ignored(self):
        self.assertEqual(waits([ev(None, "start"), ev("2020-12-07", "surgery")]), [])

    def test_year_only_and_ranges(self):
        w = waits([ev("2007", "start"), ev("2008-2010", "worse"), ev("2008", "surgery")])
        self.assertEqual(len(w), 1); self.assertAlmostEqual(w[0]["months"], 12.0, delta=0.1)
        self.assertIsNone(months("2008-2010", "2012"))

    def test_months(self):
        self.assertAlmostEqual(months("2020-01-15", "2021-01-15"), 12.0, delta=0.1)


if __name__ == "__main__":
    unittest.main()
