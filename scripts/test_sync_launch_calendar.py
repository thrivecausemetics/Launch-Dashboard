#!/usr/bin/env python3
"""Tests that the Asana calendar sync gets from a fetch to a written snapshot.

Run: python scripts/test_sync_launch_calendar.py

Why this exists: the sync runs with continue-on-error, so a crash anywhere
after the fetch leaves the run green and the snapshot frozen. A KeyError in
the mismatch report did exactly that from 2026-10-09: every run fetched the
calendar fine and then died before writing it. Asana is mocked here; nothing
touches the network.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_launch_calendar as sync  # noqa: E402


ENTRIES = [
    {"name": "Tracked Launch", "slug": "tracked-launch", "launch_date": "2026-11-04",
     "internal_date": None, "section": "GTM Campaigns", "completed": False,
     "asana_gid": "111", "asana_url": "https://app.asana.com/x/111"},
    {"name": "Upcoming Launch", "slug": "upcoming-launch", "launch_date": "2026-11-25",
     "internal_date": None, "section": "GTM Campaigns", "completed": False,
     "asana_gid": "222", "asana_url": "https://app.asana.com/x/222"},
    {"name": "Unlinked Launch", "slug": "unlinked-launch", "launch_date": "2026-10-22",
     "internal_date": None, "section": "GTM Campaigns", "completed": False,
     "asana_gid": "333", "asana_url": "https://app.asana.com/x/333"},
]

# Both linked launches disagree with Asana, one tracked and one upcoming, so
# the mismatch report prints both branches.
CONFIG = {
    "launches": [{"name": "Tracked Launch", "launch_date": "2026-10-14", "asana_gid": "111"}],
    "upcoming": [{"name": "Upcoming Launch", "launch_date": "2026-11-26", "asana_gid": "222"}],
}


class SyncWritesSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cfg = self.tmp / "launches.json"
        cfg.write_text(json.dumps(CONFIG))
        self.out = self.tmp / "launch_calendar.json"
        self.patches = [
            mock.patch.object(sync, "CONFIG_PATH", cfg),
            mock.patch.object(sync, "OUT_PATH", self.out),
            mock.patch.object(sync, "ROOT", self.tmp),
            mock.patch.object(sync, "fetch_calendar", return_value=[dict(e) for e in ENTRIES]),
            mock.patch.object(sync, "fetch_learnings", return_value={}),
            mock.patch.dict(os.environ, {"ASANA_TOKEN": "test"}),
            mock.patch.object(sys, "argv", ["sync_launch_calendar.py"]),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def run_main(self):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = sync.main()
        return code, out.getvalue()

    def test_mismatches_are_reported_and_snapshot_written(self):
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("MISMATCH (TRACKED LAUNCH): Tracked Launch", out)
        self.assertIn("MISMATCH (upcoming): Upcoming Launch", out)
        snap = json.loads(self.out.read_text())
        self.assertEqual([e["asana_gid"] for e in snap["entries"]], ["111", "222", "333"])
        self.assertEqual(len(snap["mismatches"]), 2)
        self.assertEqual([e["name"] for e in snap["not_in_config"]], ["Unlinked Launch"])
        self.assertRegex(snap["synced_at"], r"^\d{4}-\d{2}-\d{2}$")

    def test_unexpected_error_is_annotated_not_silent(self):
        with mock.patch.object(sync, "compare_with_config", side_effect=KeyError("boom")):
            code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("::warning title=Launch calendar sync failed::", out)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
