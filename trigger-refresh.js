'use strict';

/*
 * Thrive Causemetics — punctual trigger for the dashboard data refresh.
 *
 * Why this exists: GitHub's `schedule` trigger queues under load. This repo's
 * scheduled refresh runs started 86-163 minutes after their slot every day
 * for two weeks straight, so the nominally-6am data was landing 7:30-8:45am
 * PT and anyone opening the dashboard at 7am saw the previous day's cutoff.
 * Every `workflow_dispatch` run, by contrast, started immediately. So we
 * dispatch the workflow from a scheduler we control instead of waiting on
 * GitHub's cron queue. The in-workflow cron stays as a safety net — a second
 * run the same day finds data.js unchanged and commits nothing.
 *
 * Deployed as a Railway *cron service* (not a web service) — see RAILWAY.md:
 *   Cron Schedule:  0 13,14 * * *      (UTC, both DST offsets)
 *   Start Command:  node trigger-refresh.js
 *
 * Railway's cron is UTC and DST-unaware, so both hours fire and the
 * local-hour check below drops the out-of-season one. That keeps the dispatch
 * at 6:00am America/Los_Angeles year-round. Checking the wall clock is safe
 * here precisely because this scheduler is punctual — the equivalent check
 * would be wrong inside the GitHub workflow, which starts late.
 *
 * Requires REFRESH_DISPATCH_TOKEN: a fine-grained GitHub PAT scoped to this
 * repo only, with Actions: read and write. It cannot reach Snowflake — those
 * credentials stay in GitHub repository secrets.
 */

const TARGET_HOUR = 6; // 6am America/Los_Angeles
const TIMEZONE = 'America/Los_Angeles';
const OWNER = 'thrivecausemetics';
const REPO = 'Launch-Dashboard';
const WORKFLOW = 'refresh-data.yml';
const REF = 'main';

function localHour() {
  // Throws RangeError on a small-icu Node build that lacks tzdata. Better to
  // fail loudly than to dispatch at the wrong hour.
  return Number(new Intl.DateTimeFormat('en-US', {
    timeZone: TIMEZONE,
    hour: 'numeric',
    hourCycle: 'h23',
  }).format(new Date()));
}

async function main() {
  const token = process.env.REFRESH_DISPATCH_TOKEN;
  if (!token) {
    throw new Error(
      'REFRESH_DISPATCH_TOKEN is not set — add it to this Railway service\'s Variables.'
    );
  }

  const hour = localHour();
  if (hour !== TARGET_HOUR) {
    // Expected once a day: the other DST offset's cron entry.
    console.log(
      `${TIMEZONE} local hour is ${hour}, target is ${TARGET_HOUR} — ` +
      'out-of-season cron entry, nothing to dispatch.'
    );
    return;
  }

  const url =
    `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
      'User-Agent': `${REPO}-refresh-trigger`,
    },
    body: JSON.stringify({ ref: REF }),
  });

  if (res.status !== 204) {
    // GitHub returns 204 No Content on success. Anything else is a real
    // failure (401 bad/expired token, 403 missing Actions scope, 404 wrong
    // repo or workflow filename, 422 unknown ref).
    const detail = (await res.text()).replace(/\s+/g, ' ').slice(0, 300);
    throw new Error(`dispatch failed — HTTP ${res.status} ${detail}`);
  }

  console.log(
    `Dispatched ${WORKFLOW} on ${REF} at ${hour}:00 ${TIMEZONE}. ` +
    'Data should be committed and redeployed within ~5 minutes.'
  );
}

main().catch((e) => {
  // Non-zero exit so the Railway run is marked failed and is visible in logs
  // rather than silently skipping a day of data.
  console.error(`Refresh trigger error: ${e.message}`);
  process.exitCode = 1;
});
