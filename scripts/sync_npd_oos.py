#!/usr/bin/env python3
"""
Sync Demand Planning's OOS figures from the NPD OOS Tracking sheet.

Reads the "Summary Launch Dashboard" tab — SKU, Decay Curve OOS, Real
Inventory — and snapshots it into config/npd_oos_tracking.json, which the
refresh then reads. Same pattern as scripts/sync_launch_calendar.py: writing a
committed snapshot rather than querying Google from refresh_data.py keeps the
Snowflake pipeline independent of Google being reachable, and makes every
change to Demand Planning's numbers visible in git history.

These figures are shown next to the Snowflake-derived inventory and OOS on the
dashboard, never in place of them. They disagree — Snowflake reports what the
inventory tables say, Demand Planning reports their own model — and deciding
which is right is their call, not this script's.

REVIEW & DRY-RUN FIRST
----------------------
Read-only against Google. `--dry-run` prints what would change without
writing. The only file written is config/npd_oos_tracking.json.

Environment:
  GOOGLE_SERVICE_ACCOUNT_JSON
      A Google service account key, as JSON (or a path to one). The sheet must
      be shared with that account's client_email as a Viewer. Without it the
      script exits 0 without writing, so the workflow degrades to the committed
      snapshot instead of failing the whole refresh.
"""

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "config" / "npd_oos_tracking.json"

SPREADSHEET_ID = "1by_O_UW2oa9mDzF73f5PmCdfIrkOCghVZTa2P7LhXfs"
SHEET_NAME = "Summary Launch Dashboard"
SHEET_GID = "915600089"
SHEET_TITLE = "NPD OOS Tracking"
SHEET_OWNER = "bkennedy@thrivecausemetics.com"
SHEET_URL = (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
             f"/edit#gid={SHEET_GID}")

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

# Column headers, matched case-insensitively so a tidy-up in the sheet doesn't
# silently produce a snapshot of empty values.
COL_SKU = "sku"
COL_OOS = "decay curve oos"
COL_INV = "real inventory"

# Sheets hands dates back either as a serial number or as a string, depending
# on how the cell was written. Both appear in this tab.
EPOCH = dt.date(1899, 12, 30)          # Google/Excel serial-date epoch


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def access_token(key):
    """Service-account JWT -> OAuth access token.

    Hand-rolled rather than pulling in google-auth: the workflow already
    installs cryptography for Snowflake, and this is one signature and one
    POST. Adding a dependency tree for that is not a trade worth making.
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": key["client_email"],
        "scope": SCOPE,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = (b64url(json.dumps(header).encode()) + b"." +
                     b64url(json.dumps(claims).encode()))
    private_key = serialization.load_pem_private_key(
        key["private_key"].encode(), password=None)
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input + b"." + b64url(signature)

    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion.decode(),
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())["access_token"]


def fetch_rows(token):
    """The tab's used range, as a list of rows of strings."""
    rng = urllib.parse.quote(f"'{SHEET_NAME}'!A:C")
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}"
           f"/values/{rng}?valueRenderOption=UNFORMATTED_VALUE"
           f"&dateTimeRenderOption=SERIAL_NUMBER")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()).get("values") or []
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300].replace("\n", " ")
        raise RuntimeError(f"Sheets API -> HTTP {e.code} {detail}") from None


def parse_date(v):
    """A cell -> an ISO date, or None. Serial number or text, both appear."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        # The fractional part is a time of day; the dashboard shows dates, and
        # an OOS projection to the minute would imply a precision that model
        # does not have.
        return (EPOCH + dt.timedelta(days=int(v))).isoformat()
    s = str(v).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%b %d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    print(f"NOTE: unparseable date {s!r} — leaving blank")
    return None


def parse_units(v):
    if v is None or v == "":
        return None
    try:
        return int(round(float(str(v).replace(",", "").strip())))
    except ValueError:
        print(f"NOTE: unparseable inventory {v!r} — leaving blank")
        return None


def build(rows):
    if not rows:
        raise RuntimeError("the tab came back empty")
    header = [str(c).strip().lower() for c in rows[0]]
    try:
        i_sku, i_oos, i_inv = (header.index(COL_SKU), header.index(COL_OOS),
                               header.index(COL_INV))
    except ValueError:
        raise RuntimeError(
            f"expected columns {COL_SKU!r}, {COL_OOS!r}, {COL_INV!r}; "
            f"the tab has {header}. Refusing to guess.") from None

    out = {}
    for r in rows[1:]:
        cell = lambda i: r[i] if i < len(r) else None
        sku = str(cell(i_sku) or "").strip().upper()
        if not sku:
            continue
        out[sku] = {"decayCurveOOS": parse_date(cell(i_oos)),
                    "realInventoryUnits": parse_units(cell(i_inv))}
    return out


def load_key():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        return None
    if not raw.startswith("{"):
        p = Path(raw)
        if not p.exists():
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is neither JSON nor "
                               "a path to a key file")
        raw = p.read_text()
    key = json.loads(raw)
    for f in ("client_email", "private_key"):
        if f not in key:
            raise RuntimeError(f"service account key is missing {f!r}")
    return key


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the result without writing the snapshot")
    args = ap.parse_args()

    existing = json.loads(OUT_PATH.read_text()) if OUT_PATH.exists() else {}

    # A missing, expired or de-permissioned credential must not take the daily
    # data refresh down with it. Demand Planning's figures going stale is a far
    # smaller problem than no Snowflake refresh at all, so every failure below
    # keeps the committed snapshot and exits 0.
    try:
        key = load_key()
        if not key:
            print("GOOGLE_SERVICE_ACCOUNT_JSON not set — leaving "
                  f"config/{OUT_PATH.name} as-is ({len(existing.get('bySku') or {})} "
                  "SKUs from the committed snapshot).")
            return 0
        by_sku = build(fetch_rows(access_token(key)))
    except Exception as e:
        print(f"::warning::NPD OOS sync failed ({e}). Keeping the committed "
              f"snapshot; Demand Planning's figures may be stale until this is fixed.")
        return 0

    if not by_sku:
        print("ERROR: the tab returned no SKUs; refusing to overwrite the "
              "existing snapshot.", file=sys.stderr)
        return 1

    old = existing.get("bySku") or {}
    changed = [s for s, v in by_sku.items() if old.get(s) != v]
    print(f"{SHEET_TITLE} / {SHEET_NAME}: {len(by_sku)} SKUs, {len(changed)} changed")
    for s in changed[:20]:
        print(f"  {s}: {old.get(s)} -> {by_sku[s]}")
    for s in sorted(set(old) - set(by_sku)):
        print(f"  DROPPED FROM SHEET: {s}")

    payload = {
        "_readme": existing.get("_readme") or [],
        "source": {
            "title": SHEET_TITLE, "spreadsheetId": SPREADSHEET_ID,
            "sheet": SHEET_NAME, "gid": SHEET_GID, "owner": SHEET_OWNER,
            "url": SHEET_URL,
        },
        "syncedAt": dt.date.today().isoformat(),
        "syncedBy": "scripts/sync_npd_oos.py",
        "bySku": by_sku,
    }

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
