#!/usr/bin/env python3
"""Tests for the "launched with no SKUs" check.

Run: python scripts/test_launch_gaps.py

Why this exists: three launches this quarter went live and showed nothing on
the dashboard — Triple Threat, Pumpkin Spice Latte, Eyeshadow Quads Drop 2.
Each was a calendar entry with a date and no SKUs, which the pipeline cannot
query, so it produced no data and therefore no alerts. All three were caught
by a person noticing. This check is what should have caught them.

The two cases worth guarding are the ones that make it useless: not firing on
the launch day itself, and firing forever afterwards.
"""

import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_data import launch_gaps, GAP_REPORT_DAYS  # noqa: E402
import post_slack_alerts as slack  # noqa: E402

TODAY = dt.date(2026, 11, 4)


def days_ago(n):
    return str(TODAY - dt.timedelta(days=n))


def cfg(*launches):
    return {"launches": list(launches)}


def entry(name, when, **kw):
    e = {"name": name, "launch_date": when, "section": "GTM Campaigns",
         "asana_url": f"https://app.asana.com/{name}"}
    e.update(kw)
    return e


def tracked(lid, when, skus):
    return {"id": lid, "name": lid, "launch_date": when, "skus": skus}


class CalendarEntries(unittest.TestCase):
    def test_entry_live_today_is_reported(self):
        gaps = launch_gaps(cfg(), {"not_in_config": [entry("BEB Holiday", days_ago(0))]}, TODAY)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["daysLate"], 0)
        self.assertEqual(gaps[0]["source"], "calendar")

    def test_future_entry_is_not_reported(self):
        future = str(TODAY + dt.timedelta(days=3))
        self.assertEqual(launch_gaps(cfg(), {"not_in_config": [entry("Later", future)]}, TODAY), [])

    def test_stops_after_the_window(self):
        # Giveaways and promos share this calendar and will never be tracked
        # launches. Reporting them forever is the noise problem this system
        # already had once.
        late = {"not_in_config": [entry("Old promo", days_ago(GAP_REPORT_DAYS + 1))]}
        self.assertEqual(launch_gaps(cfg(), late, TODAY), [])

    def test_last_day_of_the_window_still_reported(self):
        edge = {"not_in_config": [entry("Edge", days_ago(GAP_REPORT_DAYS))]}
        self.assertEqual(len(launch_gaps(cfg(), edge, TODAY)), 1)

    def test_entry_without_a_date_is_skipped(self):
        self.assertEqual(launch_gaps(cfg(), {"not_in_config": [entry("No date", None)]}, TODAY), [])

    def test_asana_link_is_carried_through(self):
        gaps = launch_gaps(cfg(), {"not_in_config": [entry("BEB Holiday", days_ago(1))]}, TODAY)
        self.assertIn("asana.com", gaps[0]["asanaUrl"])


class StaleSnapshot(unittest.TestCase):
    """The calendar sync fails soft, so not_in_config can lag config by hours
    or — as happened on 3 Nov, when a crash in the sync went unnoticed for
    weeks — by much longer. A launch linked in config must not be reported as
    untracked just because the snapshot has not caught up."""

    def test_linked_and_populated_launch_is_not_reported(self):
        cal = {"not_in_config": [entry("BEB Holiday", days_ago(1), asana_gid="123")]}
        c = cfg({"id": "beb", "name": "BEB Holiday", "launch_date": days_ago(1),
                 "asana_gid": "123", "skus": [{"sku": "TVG1"}]})
        self.assertEqual(launch_gaps(c, cal, TODAY), [])

    def test_linked_but_still_empty_launch_is_still_reported(self):
        # Linking the Asana task is not the fix; adding SKUs is.
        cal = {"not_in_config": [entry("BEB Holiday", days_ago(1), asana_gid="123")]}
        c = cfg({"id": "beb", "name": "BEB Holiday", "launch_date": days_ago(1),
                 "asana_gid": "123", "skus": []})
        self.assertEqual(len(launch_gaps(c, cal, TODAY)), 1)

    def test_unrelated_gid_is_unaffected(self):
        cal = {"not_in_config": [entry("Other", days_ago(1), asana_gid="999")]}
        c = cfg({"id": "beb", "name": "BEB", "launch_date": days_ago(1),
                 "asana_gid": "123", "skus": [{"sku": "TVG1"}]})
        self.assertEqual(len(launch_gaps(c, cal, TODAY)), 1)


class ConfigEntries(unittest.TestCase):
    def test_config_launch_with_empty_skus_is_reported(self):
        gaps = launch_gaps(cfg(tracked("beb-holiday", days_ago(1), [])), {}, TODAY)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["source"], "config")
        self.assertEqual(gaps[0]["launchId"], "beb-holiday")

    def test_config_launch_with_skus_is_not_reported(self):
        c = cfg(tracked("fine", days_ago(1), [{"sku": "TVG1"}]))
        self.assertEqual(launch_gaps(c, {}, TODAY), [])

    def test_missing_calendar_snapshot_is_not_an_error(self):
        # The calendar sync fails soft, so None must not take the refresh down.
        gaps = launch_gaps(cfg(tracked("x", days_ago(2), [])), None, TODAY)
        self.assertEqual(len(gaps), 1)


class Ordering(unittest.TestCase):
    def test_oldest_gap_first(self):
        cal = {"not_in_config": [entry("New", days_ago(0)), entry("Older", days_ago(5))]}
        self.assertEqual([g["name"] for g in launch_gaps(cfg(), cal, TODAY)], ["Older", "New"])


class SlackRendering(unittest.TestCase):
    def alerts(self, gaps):
        return slack.collect({"launchGaps": gaps, "launches": []}, "https://example.test/")

    def test_gap_outranks_every_signal(self):
        gaps = [{"name": "BEB Holiday", "launchDate": days_ago(0), "daysLate": 0,
                 "source": "calendar", "asanaUrl": "https://asana.test/1"}]
        a = self.alerts(gaps)[0]
        self.assertEqual(a["rank"], -1)
        self.assertLess(a["rank"], min(slack.RANK_LABEL) + 1)
        self.assertIn("Launch not tracked", slack.RANK_LABEL[-1])

    def test_message_says_nothing_is_measured_and_what_to_do(self):
        gaps = [{"name": "BEB Holiday", "launchDate": days_ago(1), "daysLate": 1,
                 "source": "calendar", "asanaUrl": None}]
        a = self.alerts(gaps)[0]
        self.assertIn("launched yesterday", a["detail"].lower())
        self.assertIn("no alerts", a["detail"])
        self.assertIn("SKUs", a["action"])

    def test_links_to_the_asana_task_when_there_is_one(self):
        gaps = [{"name": "X", "launchDate": days_ago(0), "daysLate": 0,
                 "source": "calendar", "asanaUrl": "https://asana.test/42"}]
        self.assertEqual(self.alerts(gaps)[0]["url"], "https://asana.test/42")

    def test_falls_back_to_the_hub_without_a_link(self):
        gaps = [{"name": "X", "launchDate": days_ago(0), "daysLate": 0,
                 "source": "config", "launchId": "x", "asanaUrl": None}]
        self.assertEqual(self.alerts(gaps)[0]["url"], "https://example.test/")

    def test_key_is_stable_so_it_posts_once_not_daily(self):
        gaps = [{"name": "X", "launchDate": days_ago(0), "daysLate": 0,
                 "source": "calendar", "asanaUrl": None}]
        first = self.alerts(gaps)[0]["id"]
        gaps[0]["daysLate"] = 3          # same launch, three days later
        self.assertEqual(self.alerts(gaps)[0]["id"], first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
