#!/usr/bin/env python3
"""
Sync the launch calendar from the Asana 2026 Marketing Calendar.

The marketing calendar is the team's source of truth for launch dates. This
script snapshots it into config/launch_calendar.json, which the refresh then
reads. Writing a committed snapshot rather than querying Asana from
refresh_data.py keeps the Snowflake pipeline independent of Asana being
reachable, and makes every date change visible in git history — the same
pattern as config/plan_fallback.json.

REVIEW & DRY-RUN FIRST
----------------------
Read-only against Asana. `--dry-run` prints what would change without
writing. The only file written is config/launch_calendar.json.

Deliberately does NOT rewrite launch dates for launches that already have
data. Changing a live launch's launch_date silently restates its entire
history — every query window, day count, plan curve and decay boundary moves.
Mismatches are reported instead, and surfaced in the dashboard, so a human
decides. Asana is authoritative for what is *upcoming*; for launches already
running it is advisory.

Environment:
  ASANA_TOKEN   Asana personal access token (read-only use). Without it the
                script exits 0 without writing, so the workflow degrades to
                the committed snapshot instead of failing.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "launches.json"
OUT_PATH = ROOT / "config" / "launch_calendar.json"

API = "https://app.asana.com/api/1.0"
PROJECT_GID = "1216777821260255"          # 🗓️ 2026 Thrive Causemetics Marketing Calendar

# Sections that describe product launches. Promotions, Events, Beauty Boxes and
# Editorial Moments are on the same calendar but are not product launches, so
# they are deliberately excluded rather than filtered out later.
LAUNCH_SECTIONS = {
    "1216777821260256": "GTM Campaigns",
    "1216777622961360": "Product Spotlights (Relaunches, Reanimations, Restocks)",
}

FIELD_LIVE_DATE = "Live Date"
FIELD_INTERNAL = "Internal Due Date"

# "GTM | Lip Stain Marker 💄" -> "Lip Stain Marker"
PREFIX_RE = re.compile(r"^\s*(GTM|Spotlight)\s*\|\s*", re.I)
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE0F\U00002B00-\U00002BFF]+"
)


def clean_name(raw):
    name = PREFIX_RE.sub("", raw or "")
    name = EMOJI_RE.sub("", name)
    return " ".join(name.split()).strip(" -–—")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def api_get(path, token, params=None):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())["data"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300].replace("\n", " ")
        raise RuntimeError(f"Asana {path} -> HTTP {e.code} {detail}") from None


def date_field(task, field_name):
    for f in task.get("custom_fields") or []:
        if f.get("name") == field_name:
            dv = f.get("date_value") or {}
            return dv.get("date")
    return None


def fetch_calendar(token):
    """One entry per launch task, newest sections first, sorted by live date."""
    out = []
    for section_gid, section_name in LAUNCH_SECTIONS.items():
        tasks = api_get(f"/sections/{section_gid}/tasks", token, {
            "opt_fields": "name,due_on,completed,permalink_url,"
                          "custom_fields.name,custom_fields.date_value",
            "limit": 100,
        })
        for t in tasks:
            live = date_field(t, FIELD_LIVE_DATE) or t.get("due_on")
            if not live:
                # A launch with no date cannot be placed on a timeline; skip it
                # loudly rather than inventing one.
                print(f"NOTE: skipping {t.get('name')!r} — no {FIELD_LIVE_DATE} or due date")
                continue
            name = clean_name(t.get("name"))
            out.append({
                "name": name,
                "slug": slugify(name),
                "launch_date": live,
                "internal_date": date_field(t, FIELD_INTERNAL),
                "section": section_name,
                "completed": bool(t.get("completed")),
                "asana_gid": t.get("gid"),
                "asana_url": t.get("permalink_url"),
            })
    out.sort(key=lambda e: (e["launch_date"], e["name"]))
    return out


def compare_with_config(entries):
    """Report where the calendar and config/launches.json disagree.

    Matching is by slug against both the tracked launches and the existing
    upcoming list. Anything unmatched is reported, not guessed at — a launch
    still needs its SKUs added by hand before it can pull data.
    """
    cfg = json.loads(CONFIG_PATH.read_text())
    locals_ = [("tracked", l) for l in cfg.get("launches", [])] + \
              [("upcoming", u) for u in cfg.get("upcoming", [])]

    # Matched by an explicit asana_gid in config, never by name. The calendar
    # and the dashboard genuinely use different names for the same launch —
    # "Lip Stain Marker" on the calendar ships as "Lasting Mark Lip-Defining
    # Stain" — so inferring the link from the name would be guesswork, and a
    # wrong guess would restate a launch's dates. The link is declared instead.
    by_gid = {e["asana_gid"]: e for e in entries}
    linked_gids = set()

    mismatches, unlinked_config = [], []
    for kind, local in locals_:
        gid = local.get("asana_gid")
        if not gid:
            unlinked_config.append({"name": local["name"], "kind": kind,
                                    "config_launch_date": local.get("launch_date")})
            continue
        linked_gids.add(gid)
        e = by_gid.get(gid)
        if not e:
            mismatches.append({"name": local["name"], "kind": kind,
                               "config_launch_date": local.get("launch_date"),
                               "asana_launch_date": None,
                               "note": "asana_gid not found on the calendar"})
            continue
        if local.get("launch_date") != e["launch_date"]:
            mismatches.append({
                "name": local["name"], "kind": kind,
                "config_launch_date": local.get("launch_date"),
                "asana_launch_date": e["launch_date"],
                "asana_url": e["asana_url"],
            })
    unmatched = [e for gid, e in by_gid.items() if gid not in linked_gids]
    return mismatches, unmatched, unlinked_config


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the result without writing the snapshot")
    args = ap.parse_args()

    token = os.environ.get("ASANA_TOKEN")
    if not token:
        print("ASANA_TOKEN not set — leaving config/launch_calendar.json as-is. "
              "The dashboard will keep using the committed snapshot.")
        return 0

    entries = fetch_calendar(token)
    if not entries:
        # Never blank out a good snapshot because a query came back empty.
        print("ERROR: Asana returned no launch tasks; refusing to overwrite the "
              "existing snapshot.", file=sys.stderr)
        return 1

    mismatches, unmatched, missing = compare_with_config(entries)
    payload = {
        "_readme": [
            "GENERATED by scripts/sync_launch_calendar.py from the Asana",
            "2026 Thrive Causemetics Marketing Calendar. Do not hand-edit.",
            "Asana's 'Live Date' field is the source of truth for launch dates.",
            "Dates for launches that already have data are NOT auto-applied;",
            "they are reported in mismatches[] for a human to action.",
        ],
        "asana_project_gid": PROJECT_GID,
        "asana_project_url": f"https://app.asana.com/0/{PROJECT_GID}/list",
        "entries": entries,
        "mismatches": mismatches,
        "not_in_config": [
            {"name": e["name"], "launch_date": e["launch_date"],
             "section": e["section"], "asana_url": e["asana_url"]}
            for e in unmatched
        ],
        "config_without_asana_gid": missing,
    }

    print(f"Asana calendar: {len(entries)} launch entries")
    for m in mismatches:
        scope = "TRACKED LAUNCH" if m["tracked"] else "upcoming"
        print(f"  MISMATCH ({scope}): {m['name']} — config {m['config_launch_date']} "
              f"vs Asana {m['asana_launch_date']}")
    for e in unmatched:
        print(f"  ON CALENDAR, NOT LINKED: {e['name']} — {e['launch_date']} "
              f"({e['section']}) gid={e['asana_gid']}")
    for m in missing:
        print(f"  IN CONFIG, NO asana_gid: {m['name']} ({m['kind']}) — "
              f"config says {m['config_launch_date']}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
