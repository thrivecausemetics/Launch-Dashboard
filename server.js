'use strict';

/*
 * Thrive Causemetics — Launch Intelligence Hub server (Railway).
 *
 * Zero-dependency static server (Node core http only — no npm install in
 * the Docker build). Serves the dashboard (index.html, launch.html,
 * data.js, vendor/). Data freshness comes from data.js, which the GitHub
 * Actions workflow regenerates from Snowflake daily and commits to main —
 * each commit triggers a Railway redeploy, so the container needs no
 * database or Snowflake credentials.
 *
 * Answers at both / and /launch-dashboards/* so the internal portal proxy
 * (which rewrites /launch-dashboards/:path*) works unchanged.
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const HOST = '0.0.0.0'; // Railway healthchecks fail on localhost binds
const ROOT = __dirname;

// Only these files/dirs are served; pipeline internals stay private.
const SERVED_FILES = new Set([
  'index.html', 'launch.html', 'data.js',
  'llem-shade-extension.html', 'llemshadeextension.html',
]);
const SERVED_DIRS = new Set(['vendor']);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function health(res) {
  try {
    const raw = fs.readFileSync(path.join(ROOT, 'data.js'), 'utf8');
    const data = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1));
    const body = JSON.stringify({
      ok: true,
      ts: new Date().toISOString(),
      dataCutoff: data.meta.dataCutoff,
      generatedAt: data.meta.generatedAt,
      launches: data.launches.map(l => l.launchId),
    });
    res.writeHead(200, { 'Content-Type': 'application/json' }).end(body);
  } catch (e) {
    res.writeHead(500, { 'Content-Type': 'application/json' })
      .end(JSON.stringify({ ok: false, error: 'data.js unreadable: ' + e.message }));
  }
}

const server = http.createServer((req, res) => {
  let p = decodeURIComponent((req.url || '/').split('?')[0]);
  if (p.startsWith('/launch-dashboards')) p = p.slice('/launch-dashboards'.length) || '/';
  if (p === '/api/health') return health(res);
  if (p === '/' || p === '') p = '/index.html';
  // .html extension optional (e.g. /launch?id=x)
  if (!path.extname(p) && SERVED_FILES.has(p.slice(1) + '.html')) p += '.html';

  const segs = p.replace(/^\/+/, '').split('/');
  const allowed = (segs.length === 1 && SERVED_FILES.has(segs[0]))
    || (segs.length > 1 && SERVED_DIRS.has(segs[0]));
  const file = path.resolve(ROOT, ...segs);
  if (!allowed || !file.startsWith(ROOT + path.sep)) {
    return res.writeHead(404, { 'Content-Type': 'text/plain' }).end('Not found');
  }

  fs.readFile(file, (err, buf) => {
    if (err) return res.writeHead(404, { 'Content-Type': 'text/plain' }).end('Not found');
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'no-cache',
    }).end(buf);
  });
});

server.listen(PORT, HOST, () =>
  console.log(`Thrive Causemetics Launch Intelligence Hub on ${HOST}:${PORT}`)
);
