#!/usr/bin/env python3
"""
Post launch alerts to Slack after the daily refresh.

Reads the signals scripts/refresh_data.py wrote into data.js — the same ones
the dashboard's "Needs attention" panel renders — ranks them across every live
launch and posts the top few.

WHY IT DOES NOT POST EVERYTHING, EVERY DAY
------------------------------------------
"Kaisa projects out of stock" stays true until somebody reorders. Posting the
same five lines every morning gets the channel muted inside a week, and then
the one that mattered gets missed too. So:

  * A weekday run posts only alerts that are NEW, or whose severity changed.
    Nothing new means no message at all.
  * Monday posts the full top-N digest regardless, plus anything that cleared
    since the last digest, so nothing quietly disappears.

State lives in config/alert_state.json, committed by the workflow, so the
history of what was alerted and when is in git rather than in a database this
static site does not have.

REVIEW & DRY-RUN FIRST
----------------------
Read-only apart from config/alert_state.json. `--dry-run` prints the message
that would be posted and writes nothing.

Environment:
  SLACK_WEBHOOK_URL   Slack incoming webhook. Without it the script exits 0
                      without posting, so a missing secret degrades instead of
                      failing the refresh.
  SLACK_ALERT_LIMIT   How many alerts to post (default 5).
  DASHBOARD_URL       Base URL used for the links (default: the internal
                      portal route).
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data.js"
STATE_PATH = ROOT / "config" / "alert_state.json"

DEFAULT_LIMIT = 5
DEFAULT_BASE = "https://internal.thrivecausemetics.com/launch-dashboards/"
DIGEST_WEEKDAY = 0                      # Monday

# Plain-language labels for the signal ranks, so a reader who has never opened
# the dashboard can tell an out-of-stock from a soft conversion problem.
RANK_LABEL = {
    0: ":red_circle: Out of stock",
    1: ":warning: Stock running out",
    2: ":chart_with_downwards_trend: PDP conversion",
    3: ":chart_with_downwards_trend: Behind plan",
    4: ":chart_with_downwards_trend: Pacing",
}


def load_data():
    src = DATA_PATH.read_text()
    return json.loads(src.split("window.DASHBOARD_DATA = ", 1)[1].rstrip().rstrip(";\n").rstrip(";"))


def load_state():
    if not STATE_PATH.exists():
        return {"alerts": {}, "lastDigest": None}
    try:
        return json.loads(STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        # A corrupt state file must not stop the alert. Starting from empty
        # re-posts today's alerts once, which is a far smaller problem than a
        # silent channel.
        print(f"WARNING: {STATE_PATH.name} unreadable ({e}); starting from empty")
        return {"alerts": {}, "lastDigest": None}


def collect(data, base):
    """Every attention signal across live launches, ranked, newest launch first
    within a rank so a launch in its opening week is not buried under a
    four-month-old one raising the same flag."""
    out = []
    for l in data.get("launches", []):
        if l.get("archived") or not l.get("signals"):
            continue
        for s in l["signals"].get("attention", []):
            out.append({
                "id": f"{l['launchId']}|{s['key']}",
                "rank": s["rank"],
                "launch": l["name"],
                "launchDate": l.get("launchDate") or "",
                "title": s["title"],
                "detail": s["detail"],
                "url": base.rstrip("/") + "/launch.html?id=" + l["launchId"],
            })
    # Rank first, then newest launch: a launch in its opening week should not
    # be buried under a four-month-old one raising the same flag.
    out.sort(key=lambda a: a["launchDate"], reverse=True)
    out.sort(key=lambda a: a["rank"])
    return out


def blocks_for(alerts, header, footer):
    blocks = [{"type": "header", "text": {"type": "plain_text", "text": header, "emoji": True}}]
    for a in alerts:
        label = RANK_LABEL.get(a["rank"], ":small_orange_diamond:")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn",
                     "text": f"{label}  *<{a['url']}|{a['title']}>*\n"
                             f"{a['detail']}\n_{a['launch']}_"},
        })
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": footer}]})
    return blocks


def post(webhook, payload, dry_run):
    if dry_run:
        print(json.dumps(payload, indent=2))
        print("\n--dry-run: nothing posted")
        return True
    req = urllib.request.Request(
        webhook, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        return True
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:200].replace("\n", " ")
        print(f"::warning::Slack post failed (HTTP {e.code} {detail}). "
              f"Alerts are still on the dashboard.")
        return False
    except Exception as e:
        print(f"::warning::Slack post failed ({e}). Alerts are still on the dashboard.")
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the message without posting or writing state")
    ap.add_argument("--digest", action="store_true",
                    help="force the full digest, whatever day it is")
    args = ap.parse_args()

    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook and not args.dry_run:
        print("SLACK_WEBHOOK_URL not set — skipping the Slack alert. "
              "Alerts are still on the dashboard.")
        return 0

    limit = int(os.environ.get("SLACK_ALERT_LIMIT") or DEFAULT_LIMIT)
    base = os.environ.get("DASHBOARD_URL") or DEFAULT_BASE

    data = load_data()
    cutoff = data["meta"]["dataCutoff"]
    state = load_state()
    known = state.get("alerts") or {}

    alerts = collect(data, base)
    today = dt.date.today()
    digest = args.digest or today.weekday() == DIGEST_WEEKDAY

    # New, or the same alert at a different severity — a SKU moving from
    # "projects out of stock" to "is out of stock" changes rank and re-fires.
    fresh = [a for a in alerts
             if a["id"] not in known or known[a["id"]].get("rank") != a["rank"]]

    dash = f"<{base.rstrip('/')}/|Open the Launch Intelligence Hub>"
    if digest:
        top = alerts[:limit]
        cleared = [known[k]["title"] for k in known
                   if k not in {a["id"] for a in alerts}]
        if not top:
            payload = {"text": f"Launch alerts — nothing above threshold (data through {cutoff})",
                       "blocks": [{"type": "section", "text": {"type": "mrkdwn",
                                   "text": f":white_check_mark: *No launch alerts this week.* "
                                           f"Data through {cutoff}.  {dash}"}}]}
        else:
            footer = (f"Top {len(top)} of {len(alerts)} open alerts · data through {cutoff} · "
                      f"{dash}")
            if cleared:
                footer += "\n:white_check_mark: Cleared since the last digest: " + "; ".join(cleared[:5])
            payload = {"text": f"Weekly launch alerts — top {len(top)} (data through {cutoff})",
                       "blocks": blocks_for(top, "Launch alerts — weekly digest", footer)}
    elif fresh:
        top = fresh[:limit]
        footer = (f"{len(fresh)} new since yesterday, {len(alerts)} open in total · "
                  f"data through {cutoff} · {dash}")
        payload = {"text": f"{len(top)} new launch alert(s) (data through {cutoff})",
                   "blocks": blocks_for(top, "New launch alerts", footer)}
    else:
        print(f"No new alerts ({len(alerts)} open, all previously posted) — staying quiet.")
        payload = None

    if payload and not post(webhook, payload, args.dry_run):
        return 0                       # already warned; never fail the refresh

    if args.dry_run:
        print(f"\n{len(alerts)} open alerts, {len(fresh)} new, digest={digest}")
        return 0

    STATE_PATH.write_text(json.dumps({
        "_readme": [
            "GENERATED by scripts/post_slack_alerts.py. Do not hand-edit.",
            "Tracks which launch alerts have already been posted to Slack so a",
            "standing alert is not re-posted every morning. Delete an entry to",
            "make that alert fire again on the next run.",
        ],
        "lastRun": str(today),
        "lastDigest": str(today) if digest else state.get("lastDigest"),
        "dataCutoff": cutoff,
        "alerts": {a["id"]: {"rank": a["rank"], "title": a["title"],
                             "firstSeen": (known.get(a["id"]) or {}).get("firstSeen", str(today)),
                             "lastPosted": str(today) if (digest or a in fresh)
                             else (known.get(a["id"]) or {}).get("lastPosted")}
                   for a in alerts},
    }, indent=2) + "\n")
    print(f"Posted. {len(alerts)} open alerts, {len(fresh)} new, digest={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
