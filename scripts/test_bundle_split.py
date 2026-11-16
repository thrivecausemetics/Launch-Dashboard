#!/usr/bin/env python3
"""Tests for the Bundles tab numbers (summarize_bundle_split) and the
"sells inside bundles" signal.

Run: python scripts/test_bundle_split.py

The cases are cut down from Grace & Hope's first 12 days (Nov 2026), where
40% of units sold inside bundles and the affinity-based pairing signal could
not see it.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_data import compute_signals, summarize_bundle_split  # noqa: E402

META = {"TVG6670": {"name": "Grace"}, "TVG6660": {"name": "Hope"}}


def row(sku, bundle, units, net, set_disc=0.0, region="US", name=None):
    return {"SKU": sku, "REGION": region, "BUNDLE": bundle, "SET_NAME": name if bundle else None,
            "UNITS": units, "NET_USD": net, "SET_DISC_USD": set_disc}


ROWS = [
    row("TVG6660", None, 600, 14400.0),
    row("TVG6670", None, 400, 9600.0),
    row("TVG6660", "brilliant-eye-brightener-duo", 300, 6000.0, 1200.0, name="Brilliant Eye Brightener™ Duo"),
    row("TVG6670", "brilliant-eye-brightener-duo", 200, 4000.0, 800.0, name="Brilliant Eye Brightener™ Duo"),
    row("TVG6660", "build-your-own-set-5", 9, 180.0, 27.0, name="Build Your Own Set - 5 Products"),
    row("TVG6660", "buildyour-own-set-5", 1, 20.0, 3.0, region="CA", name="Build Your Own Set - 5 Products"),
]


class Summary(unittest.TestCase):
    def setUp(self):
        self.out = summarize_bundle_split(ROWS, META)

    def test_share_and_net_per_unit(self):
        t = self.out["totals"]
        self.assertEqual((t["units"], t["bundleUnits"], t["standaloneUnits"]), (1510, 510, 1000))
        self.assertAlmostEqual(t["share"], 510 / 1510, places=4)
        self.assertEqual(t["netPerUnitStandalone"], 24.0)
        self.assertEqual(t["netPerUnitBundled"], round(10200 / 510, 2))
        self.assertEqual(t["setDiscount"], 2030.0)

    def test_bundles_ranked_and_split_by_shade(self):
        top = self.out["byBundle"][0]
        self.assertEqual(top["name"], "Brilliant Eye Brightener™ Duo")
        self.assertEqual(top["bySku"], {"TVG6660": 300, "TVG6670": 200})

    def test_typo_handle_merges_by_name(self):
        byos = [b for b in self.out["byBundle"] if b["name"].startswith("Build Your Own Set - 5")]
        self.assertEqual(len(byos), 1)
        self.assertEqual((byos[0]["units"], byos[0]["usUnits"], byos[0]["caUnits"]), (10, 9, 1))

    def test_by_shade(self):
        hope = next(x for x in self.out["bySku"] if x["sku"] == "TVG6660")
        self.assertEqual((hope["name"], hope["units"], hope["bundleUnits"]), ("Hope", 910, 310))
        self.assertEqual(hope["topBundle"], "Brilliant Eye Brightener™ Duo")

    def test_nothing_sold_is_none(self):
        self.assertIsNone(summarize_bundle_split([], META))


class Signal(unittest.TestCase):
    def test_bundle_signal_fires_above_threshold(self):
        working = compute_signals([], [], [], [], [], None,
                                  bundle_split=summarize_bundle_split(ROWS, META))["working"]
        sig = next(s for s in working if s["key"] == "bundles")
        self.assertEqual(sig["title"], "34% of units sell inside bundles")
        self.assertIn("Brilliant Eye Brightener™ Duo (500 units)", sig["detail"])

    def test_no_signal_when_few_bundled(self):
        rows = [row("TVG6660", None, 1000, 24000.0),
                row("TVG6660", "duo", 50, 1000.0, name="Duo")]
        working = compute_signals([], [], [], [], [], None,
                                  bundle_split=summarize_bundle_split(rows, META))["working"]
        self.assertFalse([s for s in working if s["key"] == "bundles"])

    def test_no_bundle_data_no_signal(self):
        working = compute_signals([], [], [], [], [], None, bundle_split=None)["working"]
        self.assertFalse([s for s in working if s["key"] == "bundles"])


if __name__ == "__main__":
    unittest.main()
