/* Reproducible browser checks for the StutterTurn call console.
 *
 * Run from the repository root:
 *   node web/demo-ui/dev/checks/browser-checks.mjs
 *
 * Requires Playwright's chromium. If the module is not resolvable, run
 *   npx -y playwright@1.64.0 install chromium
 *   npx -y -p playwright@1.64.0 node web/demo-ui/dev/checks/browser-checks.mjs
 * (the script also finds a playwright copy left in the npx cache).
 *
 * The script serves web/demo-ui itself, starts the committed dev mock
 * (dev/mock-agent-server.py) and asserts the console's honest-labeling
 * invariants in blocked, preview and mock-backend modes. Everything on
 * screen is synthetic: a pass is not audio, model or benchmark evidence.
 */
'use strict';

import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const demoUiRoot = path.resolve(here, '..', '..');
const mockScript = path.join(demoUiRoot, 'dev', 'mock-agent-server.py');

/* ---------- locate playwright without a package manifest ---------- */
function loadPlaywright() {
  const require = createRequire(import.meta.url);
  try { return require('playwright'); } catch (_) { /* keep looking */ }
  const candidates = [];
  for (const entry of (process.env.PATH || '').split(path.delimiter)) {
    if (/node_modules[\\/]\.bin[\\/]?$/.test(entry)) { candidates.push(path.join(entry, '..', 'playwright')); }
  }
  const caches = [path.join(os.homedir(), '.npm', '_npx')];
  if (process.env.LOCALAPPDATA) { caches.push(path.join(process.env.LOCALAPPDATA, 'npm-cache', '_npx')); }
  for (const cache of caches) {
    let entries = [];
    try { entries = fs.readdirSync(cache); } catch (_) { continue; }
    for (const entry of entries) { candidates.push(path.join(cache, entry, 'node_modules', 'playwright')); }
  }
  for (const candidate of candidates) {
    if (!fs.existsSync(path.join(candidate, 'package.json'))) { continue; }
    try { return require(candidate); } catch (_) { /* try the next copy */ }
  }
  return null;
}

/* ---------- helpers ---------- */
function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const port = probe.address().port;
      probe.close(() => resolve(port));
    });
  });
}
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json',
  '.woff2': 'font/woff2', '.png': 'image/png', '.md': 'text/plain; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
};
function startStaticServer(root, port) {
  const server = http.createServer((request, response) => {
    const clean = decodeURIComponent(new URL(request.url, 'http://x').pathname);
    const file = path.join(root, clean === '/' ? 'index.html' : clean.replace(/^\/+/, ''));
    if (!file.startsWith(root) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
      response.writeHead(404); response.end('not found'); return;
    }
    response.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(response);
  });
  return new Promise((resolve) => server.listen(port, '127.0.0.1', () => resolve(server)));
}
function startMock(port) {
  const interpreters = process.platform === 'win32' ? ['python', 'py'] : ['python3', 'python'];
  return new Promise((resolve, reject) => {
    function attempt(index) {
      if (index >= interpreters.length) { reject(new Error('No python interpreter found for the dev mock')); return; }
      const child = spawn(interpreters[index], [mockScript, '--port', String(port), '--speed', '8'],
        { stdio: ['ignore', 'pipe', 'pipe'] });
      const timer = setTimeout(() => { child.kill(); reject(new Error('dev mock did not start in time')); }, 15000);
      child.once('error', () => { clearTimeout(timer); attempt(index + 1); });
      child.stdout.on('data', (chunk) => {
        if (String(chunk).includes('DEVELOPMENT MOCK')) { clearTimeout(timer); resolve(child); }
      });
      child.stderr.on('data', () => {});
    }
    attempt(0);
  });
}

/* ---------- tiny harness ---------- */
let passed = 0;
const failures = [];
function assert(condition, message) { if (!condition) { throw new Error(message || 'assertion failed'); } }
async function test(name, fn) {
  try { await fn(); passed += 1; console.log('ok   ' + name); }
  catch (error) {
    failures.push({ name, error });
    console.log('FAIL ' + name + ' — ' + ((error && error.message) || error));
  }
}

/* ---------- run ---------- */
const playwright = loadPlaywright();
if (!playwright) {
  console.error('Playwright is not resolvable. Install the browser once, then rerun through npx:');
  console.error('  npx -y playwright@1.64.0 install chromium');
  console.error('  npx -y -p playwright@1.64.0 node web/demo-ui/dev/checks/browser-checks.mjs');
  process.exit(2);
}

const uiPort = await freePort();
const mockPort = await freePort();
const staticServer = await startStaticServer(demoUiRoot, uiPort);
const mock = await startMock(mockPort);
let browser;
try { browser = await playwright.chromium.launch(); }
catch (error) {
  console.error('Chromium launch failed (run: npx -y playwright@1.64.0 install chromium): ' + error.message);
  mock.kill(); staticServer.close(); process.exit(2);
}
const page = await browser.newPage();
const pageErrors = [];
page.on('pageerror', (error) => pageErrors.push(String(error)));

const text = async (selector) => ((await page.locator(selector).textContent()) || '').trim();
const phaseIs = (phase, timeout = 15000) =>
  page.waitForFunction((value) => document.getElementById('run-phase').textContent === value, phase, { timeout });
const summaryRows = () => page.evaluate(() =>
  Array.from(document.querySelectorAll('#summary-body > div')).map((row) =>
    [row.querySelector('dt').textContent, row.querySelector('dd').textContent]));
const summaryValue = async (label) => {
  const row = (await summaryRows()).find((pair) => pair[0] === label);
  return row ? row[1] : null;
};
const metadataValue = async (label) => {
  const rows = await page.evaluate(() =>
    Array.from(document.querySelectorAll('#metadata-body > div')).map((row) =>
      [row.querySelector('dt').textContent, row.querySelector('dd').textContent]));
  const row = rows.find((pair) => pair[0] === label);
  return row ? row[1] : null;
};
const neutralClick = () => page.locator('#state-heading').click();

try {
  await page.goto('http://127.0.0.1:' + uiPort + '/');

  /* ---- blocked state ---- */
  await test('blocked: chip says LIVE INTEGRATION: BLOCKED and no preview banner shows', async () => {
    assert((await text('#connection-chip')) === 'LIVE INTEGRATION: BLOCKED', 'chip text wrong');
    assert(await page.locator('#preview-banner').isHidden(), 'preview banner visible while blocked');
  });
  await test('blocked: start disabled; all arms, including STUTTERTURN, unavailable', async () => {
    assert(await page.locator('#btn-start').isDisabled(), 'start enabled while blocked');
    const badges = await page.locator('#config-group .badge').allTextContents();
    assert(badges.length === 3 && badges.every((badge) => badge === 'unavailable'), 'badges: ' + badges.join(','));
    const labels = await page.locator('#config-group .cfg-label').allTextContents();
    assert(labels.includes('STUTTERTURN'), 'candidate arm missing');
  });
  await test('blocked: keyboard S cannot start a run', async () => {
    await page.keyboard.press('s');
    assert((await text('#run-phase')) === 'idle', 'phase left idle');
    assert(/Cannot start/.test(await text('#status-banner')), 'no cannot-start message');
  });

  /* ---- development preview ---- */
  await test('preview: P shows the labeled banner and NOT LIVE chip', async () => {
    await page.keyboard.press('p');
    assert(await page.locator('#preview-banner').isVisible(), 'banner hidden');
    const banner = await text('#preview-banner');
    assert(banner.includes('DEVELOPMENT PREVIEW') && banner.includes('No audio'), 'banner text: ' + banner);
    const chip = await text('#connection-chip');
    assert(chip.includes('DEVELOPMENT PREVIEW') && chip.includes('NOT LIVE'), 'chip text: ' + chip);
  });
  await test('preview: arms become synthetic-only and the toggle reflects the mode', async () => {
    const badges = await page.locator('#config-group .badge').allTextContents();
    assert(badges.length === 3 && badges.every((badge) => badge === 'synthetic only'), 'badges: ' + badges.join(','));
    assert(await page.locator('#preview-toggle').isChecked(), 'toggle unchecked');
  });
  await test('preview: S starts a run with a synthetic run identity', async () => {
    await page.keyboard.press('s');
    await phaseIs('running');
    const runId = await text('#run-id');
    assert(runId.includes('preview-') && runId.includes('Synthetic preview ID'), 'run id: ' + runId);
    const mode = await text('#timeline-mode');
    assert(mode.includes('SYNTHETIC') && mode.includes('NO AUDIO'), 'timeline mode: ' + mode);
  });
  await test('preview: the fixture run ends with a synthetic, not-evidence summary', async () => {
    await phaseIs('ended');
    assert((await text('#summary-note')).includes('SYNTHETIC SUMMARY'), 'summary note missing synthetic label');
  });
  await test('preview: timings carry synthetic qualifiers and the tally reports the overlap', async () => {
    const decision = await text('#first-decision');
    assert(decision.includes('4.60 s') && decision.includes('Synthetic'), 'first decision: ' + decision);
    const audible = await text('#first-audible');
    assert(audible.includes('5.40 s') && audible.includes('no audio'), 'first audible: ' + audible);
    assert((await text('#current-state')) === 'interrupted', 'tally state not interrupted');
    assert((await text('#tally-note')).includes('SYNTHETIC OVERLAP'), 'tally note missing synthetic overlap');
  });
  await test('preview: X stops a running fixture locally', async () => {
    await page.keyboard.press('s');
    await phaseIs('running');
    await page.keyboard.press('x');
    assert((await text('#run-phase')) === 'stopped', 'phase not stopped');
    assert((await text('#summary-note')).includes('Stopped locally'), 'summary note missing stop text');
  });
  await test('preview: R resets events, identity and the clock', async () => {
    await page.keyboard.press('r');
    assert((await page.locator('#event-body .empty-row').count()) === 1, 'event table not cleared');
    assert((await text('#run-id')) === '—', 'run id not cleared');
    assert((await text('#run-clock')) === '00:00.00', 'clock not reset');
    assert((await text('#current-state')) === 'no run', 'tally not reset');
  });

  /* ---- committed dev mock over real HTTP/WebSocket ---- */
  await test('mock: keys typed in the backend URL field never trigger shortcuts', async () => {
    await page.keyboard.press('p'); // leave preview; back to blocked
    const statusBefore = await text('#status-banner');
    await page.locator('#backend-url').fill('');
    await page.keyboard.type('s');
    assert((await text('#run-phase')) === 'idle', 'typing s in the URL field started a run');
    assert((await text('#status-banner')) === statusBefore, 'status changed while typing in the URL field');
  });
  await test('mock: Connect reaches the dev mock and labels everything synthetic', async () => {
    await page.locator('#backend-url').fill('http://127.0.0.1:' + mockPort);
    await page.locator('#btn-connect').click();
    await page.waitForFunction(() =>
      document.getElementById('connection-chip').textContent.includes('MOCK BACKEND'), null, { timeout: 15000 });
    const chip = await text('#connection-chip');
    assert(chip.includes('MOCK BACKEND') && chip.includes('SYNTHETIC'), 'chip text: ' + chip);
    assert(await page.locator('#preview-banner').isVisible(), 'mock banner hidden');
    assert((await text('#preview-banner')).includes('MOCK BACKEND'), 'banner not mock-labeled');
  });
  await test('mock: five fixtures listed; candidate stays unavailable', async () => {
    const options = await page.locator('#source-select option').allTextContents();
    assert(options.length === 5, 'expected 5 fixtures, got ' + options.length);
    const arms = await page.evaluate(() =>
      Array.from(document.querySelectorAll('#config-group .config-option')).map((option) =>
        [option.querySelector('.cfg-label').textContent, option.querySelector('.badge').textContent]));
    const candidate = arms.find((arm) => arm[0] === 'STUTTERTURN');
    assert(candidate && candidate[1] === 'unavailable', 'candidate badge: ' + JSON.stringify(candidate));
    assert(arms.filter((arm) => arm[1] === 'synthetic only').length === 2, 'stock/patient not synthetic-only');
  });
  let firstRunId = '';
  await test('mock: a stock overlap run starts with MOCK-labeled attribution', async () => {
    await page.locator('#source-select').selectOption('overlap.fixture');
    await page.locator('#btn-start').click();
    await phaseIs('running');
    const runId = await text('#run-id');
    assert(runId.includes('mock-') && runId.includes('MOCK run'), 'run id: ' + runId);
    firstRunId = runId.split(' ')[0];
    const caption = await text('#event-caption');
    assert(caption.includes(firstRunId) && caption.includes('STOCK'), 'caption: ' + caption);
  });
  await test('mock: the overlap run ends with reported-overlap summary values', async () => {
    await phaseIs('ended');
    assert((await text('#summary-note')).includes('SYNTHETIC SUMMARY'), 'summary note missing synthetic label');
    assert((await summaryValue('Audible interruption (reported; unverified)')) === 'Yes', 'interruption not Yes');
    assert((await summaryValue('Overlap (reported)')) === '0.60 s', 'overlap not 0.60 s');
  });
  await test('mock: every ledger row attributes the run; audio start stays "(reported)"', async () => {
    const rows = await page.evaluate(() =>
      Array.from(document.querySelectorAll('#event-body tr')).map((row) =>
        Array.from(row.children).map((cell) => cell.textContent)));
    assert(rows.length >= 8, 'expected a full ledger, got ' + rows.length + ' rows');
    assert(rows.every((row) => row[0].includes('STOCK')), 'a row lost its configuration attribution');
    assert(rows.every((row) => row[0].includes(firstRunId)), 'a row lost its run id');
    assert(rows.some((row) => row[2] === 'agent_audio_start (reported)'), 'reported audio-start row missing');
    assert((await text('#current-state')) === 'interrupted', 'tally not interrupted');
    assert((await text('#tally-note')).includes('SYNTHETIC OVERLAP'), 'tally note missing synthetic overlap');
  });
  await test('mock: metadata shows services OFF, mock model and contract 0.1', async () => {
    assert(((await metadataValue('Services')) || '').includes('OFF'), 'services not OFF');
    assert((await metadataValue('Model')) === 'mock', 'model not "mock"');
    assert((await metadataValue('Contract version')) === '0.1', 'contract version not 0.1');
    assert((await text('#audio-note')).includes('Services OFF'), 'audio note missing services-off caveat');
  });
  await test('mock: R clears the run record but keeps the mock connection', async () => {
    await neutralClick();
    await page.keyboard.press('r');
    assert((await page.locator('#event-body .empty-row').count()) === 1, 'event table not cleared');
    assert((await text('#run-id')) === '—', 'run id not cleared');
    assert((await page.locator('#metadata-body > div').count()) === 0, 'metadata not cleared');
    const chip = await text('#connection-chip');
    assert(chip.includes('MOCK BACKEND') && chip.includes('SYNTHETIC'), 'connection lost on reset: ' + chip);
  });
  await test('mock: a patient cancelled run gets a fresh id and Cancelled: Yes', async () => {
    await page.locator('#source-select').selectOption('cancelled.fixture');
    await neutralClick();
    await page.keyboard.press('2');
    await page.locator('#btn-start').click();
    await phaseIs('running');
    const runId = (await text('#run-id')).split(' ')[0];
    assert(runId && runId !== firstRunId, 'run id did not change: ' + runId);
    assert((await text('#event-caption')).includes('PATIENT'), 'caption not attributed to PATIENT');
    await phaseIs('ended');
    assert((await summaryValue('Cancelled')) === 'Yes', 'Cancelled not Yes');
  });
  await test('no uncaught page errors across the whole session', async () => {
    assert(pageErrors.length === 0, 'page errors: ' + pageErrors.join(' | '));
  });
} finally {
  await browser.close().catch(() => {});
  mock.kill();
  staticServer.close();
}

const total = passed + failures.length;
console.log('\nbrowser-checks: ' + passed + '/' + total + ' passed');
if (failures.length) {
  for (const failure of failures) { console.log('  failed: ' + failure.name); }
  process.exit(1);
}
