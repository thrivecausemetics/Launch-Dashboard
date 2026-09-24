#!/usr/bin/env python3
"""Tests that every alert naming a shade also names its product.

Run: python scripts/test_alert_labels.py

Why this exists: shade names are not unique across the catalogue. There is a
Rosa in both EmpowerShine and EmpowerMatte, a Liliana in Lasting Mark and
Sheer Strength, a Kaisa and a Tessa in two launches each. "Rosa is out of
stock in Canada" is not actionable until somebody works out which Rosa —
which is exactly the question the alerts channel asked.

The launch name underneath is not a substitute: Winter Berries spans six
products, so it narrows nothing.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_data import _label, _clean_product, _stock_signals, SIGNAL_RULES  # noqa: E402


def variant(sku, name, product, **kw):
    v = {"sku": sku, "name": name, "product": product,
         "usInventoryUnits": None, "caInventoryUnits": None,
         "usDaysToOOS": None, "caDaysToOOS": None,
         "usRunRateUnitsPerDay": 0, "caRunRateUnitsPerDay": 0}
    v.update(kw)
    return v


class Label(unittest.TestCase):
    def test_shade_and_product(self):
        self.assertEqual(
            _label({"name": "Rosa", "product": "EmpowerMatte™ Precision Lipstick Crayon"}),
            "Rosa (EmpowerMatte™ Precision Lipstick Crayon)")

    def test_two_rosas_are_distinguishable(self):
        a = _label({"name": "Rosa", "product": "EmpowerMatte™ Precision Lipstick Crayon"})
        b = _label({"name": "Rosa", "product": "Empowershine™ Satin Lip Cream"})
        self.assertNotEqual(a, b)

    def test_missing_product_falls_back_to_shade(self):
        # Better a bare shade than "Rosa ()".
        self.assertEqual(_label({"name": "Rosa", "product": None}), "Rosa")
        self.assertEqual(_label({"name": "Rosa", "product": ""}), "Rosa")
        self.assertEqual(_label({"name": "Rosa"}), "Rosa")

    def test_emoji_variation_selector_stripped(self):
        # Lasting Mark ships as "Lasting Mark™️", which Slack renders as a
        # coloured emoji beside plain ™ elsewhere in the same message.
        self.assertEqual(_clean_product("Lasting Mark™️ Lip-Defining Stain"),
                         "Lasting Mark™ Lip-Defining Stain")
        self.assertNotIn("️", _label(
            {"name": "Daniella", "product": "Lasting Mark™️ Lip-Defining Stain"}))


class StockAlertTitles(unittest.TestCase):
    def test_out_of_stock_title_names_the_product(self):
        v = variant("TVG4560", "Rosa", "EmpowerMatte™ Precision Lipstick Crayon",
                    caInventoryUnits=0, usInventoryUnits=9340)
        out = _stock_signals([v], SIGNAL_RULES)
        oos = [a for a in out if a["rank"] == 0]
        self.assertEqual(len(oos), 1)
        self.assertIn("EmpowerMatte™ Precision Lipstick Crayon", oos[0]["title"])
        self.assertIn("Rosa", oos[0]["title"])

    def test_runs_out_soon_title_names_the_product(self):
        v = variant("TVG7220", "Brandy", "Lasting Mark™ Lip-Defining Stain",
                    caInventoryUnits=100, caDaysToOOS=5, caRunRateUnitsPerDay=20,
                    usInventoryUnits=5000)
        out = _stock_signals([v], SIGNAL_RULES)
        soon = [a for a in out if a["rank"] == 1]
        self.assertEqual(len(soon), 1)
        self.assertIn("Lasting Mark™ Lip-Defining Stain", soon[0]["title"])

    def test_alert_key_is_unchanged_by_the_label(self):
        # Keys are SKU-based on purpose: renaming an alert must not make a
        # standing problem look new, or clear and re-open in the channel.
        v = variant("TVG4560", "Rosa", "EmpowerMatte™ Precision Lipstick Crayon",
                    caInventoryUnits=0, usInventoryUnits=9340)
        bare = variant("TVG4560", "Rosa", None, caInventoryUnits=0, usInventoryUnits=9340)
        self.assertEqual([a["key"] for a in _stock_signals([v], SIGNAL_RULES)],
                         [a["key"] for a in _stock_signals([bare], SIGNAL_RULES)])

    def test_lopsided_stock_still_reads_as_distribution(self):
        v = variant("TVG4560", "Rosa", "EmpowerMatte™ Precision Lipstick Crayon",
                    caInventoryUnits=0, usInventoryUnits=9340)
        oos = [a for a in _stock_signals([v], SIGNAL_RULES) if a["rank"] == 0][0]
        self.assertIn("distribution problem", oos["detail"])
        self.assertIn("transfer", oos["action"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
