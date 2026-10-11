/* Site interaction and responsive checks. No backend, paid calls, or captures.
 * Run from the repository root: node web/demo-ui/dev/checks/site-checks.mjs
 * Requires the same cached Playwright/Chromium as browser-checks.mjs.
 */
'use strict';

import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, '..', '..', '..');

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  try { return require('playwright'); } catch (_) { /* Try the npx cache. */ }
  const candidates = [];
  for (const entry of (process.env.PATH || '').split(path.delimiter)) {
    if (/node_modules[\\/]\.bin[\\/]?$/.test(entry)) candidates.push(path.join(entry, '..', 'playwright'));
  }
  const caches = [path.join(os.homedir(), '.npm', '_npx')];
  if (process.env.LOCALAPPDATA) caches.push(path.join(process.env.LOCALAPPDATA, 'npm-cache', '_npx'));
  for (const cache of caches) {
    let entries;
    try { entries = fs.readdirSync(cache); } catch (_) { continue; }
    for (const entry of entries) candidates.push(path.join(cache, entry, 'node_modules', 'playwright'));
  }
  for (const candidate of candidates) {
    try { return require(candidate); } catch (_) { /* Try the next cached copy. */ }
  }
  return null;
}

const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.woff2': 'font/woff2', '.png': 'image/png', '.json': 'application/json', '.md': 'text/plain', '.txt': 'text/plain' };
function serveSite() {
  const server = http.createServer((request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
      let file = path.resolve(webRoot, '.' + pathname);
      if (file !== webRoot && !file.startsWith(webRoot + path.sep)) {
        response.writeHead(403).end(); return;
      }
      if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
      if (!fs.existsSync(file) || !fs.statSync(file).isFile()) { response.writeHead(404).end(); return; }
      response.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(response);
    } catch (_) { response.writeHead(400).end(); }
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server)));
}

let passed = 0;
const failures = [], pageErrors = [], unexpectedRequests = [], unexpectedSockets = [];
function assert(condition, message) { if (!condition) throw new Error(message); }
async function test(name, fn) {
  try { await fn(); passed++; console.log('ok   ' + name); }
  catch (error) { failures.push(name); console.log('FAIL ' + name + ' — ' + error.message); }
}
const playwright = loadPlaywright();
if (!playwright) {
  console.error('Playwright unavailable. Run npx -y playwright@1.64.0 install chromium, then');
  console.error('npx -y -p playwright@1.64.0 node web/demo-ui/dev/checks/site-checks.mjs');
  process.exit(2);
}
const server = await serveSite();
const origin = 'http://127.0.0.1:' + server.address().port;
let browser;
try { browser = await playwright.chromium.launch(); }
catch (error) {
  server.close();
  console.error('Chromium unavailable: ' + error.message);
  console.error('Run npx -y playwright@1.64.0 install chromium');
  process.exit(2);
}
async function context(options = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce', ...options });
  ctx.on('page', page => page.on('pageerror', error => pageErrors.push(error.message)));
  await ctx.route('**/*', route => {
    if (route.request().url().startsWith(origin + '/')) return route.continue();
    unexpectedRequests.push(route.request().url());
    return route.abort();
  });
  await ctx.routeWebSocket('**/*', socket => {
    unexpectedSockets.push(socket.url());
    socket.close();
  });
  return ctx;
}
async function settled(page, route = '/') {
  await page.goto(origin + route);
  await page.evaluate(() => document.fonts.ready);
}
async function isPlaying(page, expected) {
  await page.waitForFunction(value => document.querySelector('.turn-figure').classList.contains('is-playing') === value,
    expected, { timeout: 2500 });
}
async function stablePosition(page) {
  const before = await page.locator('#sequence-position').inputValue();
  await page.waitForTimeout(180);
  assert(await page.locator('#sequence-position').inputValue() === before, 'paused illustration continued moving');
}
async function enablePreview(pageOrFrame) {
  const toggle = pageOrFrame.locator('#preview-toggle');
  const disclosure = toggle.locator('xpath=ancestor::details[1]');
  if (await disclosure.count() && await disclosure.getAttribute('open') === null) {
    await disclosure.locator('summary').click();
  }
  await toggle.check();
}
async function contained(pageOrFrame) {
  const sizes = await pageOrFrame.evaluate(() => ({ viewport: innerWidth,
    html: document.documentElement.scrollWidth, body: document.body.scrollWidth }));
  assert(sizes.html <= sizes.viewport + 1 && sizes.body <= sizes.viewport + 1,
    'document overflow: ' + JSON.stringify(sizes));
}
async function routeLink(scope, pathname) {
  const links = scope.locator('a[href]');
  const index = await links.evaluateAll((elements, target) =>
    elements.findIndex(element => new URL(element.href).pathname === target), pathname);
  assert(index >= 0, 'link to ' + pathname + ' missing');
  return links.nth(index);
}
async function navigateHeader(page, pathname) {
  await (await routeLink(page.locator('.site-header nav'), pathname)).click();
  await page.waitForURL(origin + pathname);
  const current = page.locator('.site-header nav a[aria-current="page"]');
  assert(await current.count() === 1, 'navigation must identify one current page');
  assert(await current.evaluate(link => new URL(link.href).pathname) === pathname,
    'navigation identifies the wrong current page');
}

try {
  const reduced = await context();
  const page = await reduced.newPage();
  await settled(page);
  await test('reduced motion: illustration starts complete and stays paused in view', async () => {
    await page.locator('.turn-figure').scrollIntoViewIfNeeded();
    await isPlaying(page, false);
    assert(await page.locator('#sequence-position').inputValue() === '100', 'initial position is not complete');
    assert(await page.locator('#sequence-phase').textContent() === 'Reply', 'initial phase is not Reply');
    assert(await page.locator('#sequence-toggle').getAttribute('aria-label') === 'Play illustration', 'Play accessible name missing');
    await stablePosition(page);
  });
  await test('explicit Play works with reduced motion; keyboard pause stops progress', async () => {
    await page.locator('#sequence-toggle').click();
    await isPlaying(page, true);
    await page.waitForFunction(() => Number(document.querySelector('#sequence-position').value) > 0 &&
      Number(document.querySelector('#sequence-position').value) < 100);
    await page.locator('#sequence-toggle').press('Space');
    await isPlaying(page, false);
    await stablePosition(page);
  });
  for (const [position, phase, meaning] of [[40, 'Pause', /unfinished|holds/i], [60, 'Continuing', /continues|open/i], [90, 'Reply', /finished|reply/i]]) {
    await test('keyboard scrub to ' + position + '% pauses at ' + phase, async () => {
      const slider = page.locator('#sequence-position');
      await page.locator('#sequence-toggle').click();
      await isPlaying(page, true);
      await slider.focus();
      await slider.press('Home');
      for (let index = 0; index < position; index++) await slider.press('ArrowRight');
      assert(await slider.inputValue() === String(position), 'native range did not reach requested position');
      await isPlaying(page, false);
      assert(await page.locator('#sequence-phase').textContent() === phase, 'phase did not follow seek position');
      assert(meaning.test(await page.locator('#sequence-note').textContent()), 'phase explanation not updated');
      assert((await slider.getAttribute('aria-valuetext')).includes(phase), 'range accessible value lacks phase');
      await stablePosition(page);
    });
  }
  await test('landing keeps illustration and recorded-playback limitations explicit', async () => {
    assert(/concept illustration.*no recorded timing or audio/i.test(await page.locator('.turn-figure figcaption').textContent()), 'illustration provenance missing');
    assert(/no audio/i.test(await page.locator('.figure-chip').textContent()), 'figure badge omitted no-audio disclosure');
    assert(await page.locator('audio, video').count() === 0, 'illustration unexpectedly contains media playback');
  });
  await test('header navigation distinguishes judge guide, live workspace and overview', async () => {
    await navigateHeader(page, '/judge/');
    assert(await page.locator('#console-frame, #btn-start').count() === 0, 'judge guide contains operational console controls');
    await navigateHeader(page, '/live/');
    assert(await page.locator('#console-frame').isVisible(), 'live console missing');
    await navigateHeader(page, '/judge/');
    await navigateHeader(page, '/');
    assert(await page.locator('.hero h1').isVisible(), 'landing hero missing after return');
  });
  await test('landing actions lead separately to the guide and live workspace', async () => {
    const primary = page.locator('.hero-actions .button-primary');
    const secondary = page.locator('.hero-actions .button-quiet');
    assert(await primary.evaluate(link => new URL(link.href).pathname) === '/judge/', 'primary action bypasses the judge guide');
    assert(await secondary.evaluate(link => new URL(link.href).pathname) === '/live/', 'secondary action does not open the live workspace');
    await primary.click();
    await page.waitForURL(origin + '/judge/');
    assert(await page.locator('#guide-title').isVisible(), 'judge guide did not load from the primary action');
  });
  await test('judge guide explains evaluation and system flow without run controls', async () => {
    assert(await page.locator('#console-frame, #btn-start').count() === 0, 'judge guide embeds operational run controls');
    assert(await page.locator('.evaluation-steps > li').count() === 4, 'evaluation itinerary is incomplete');
    const steps = await page.locator('#evaluation-steps').innerText();
    for (const meaning of [/same source/i, /fresh run/i, /reported agent audio/i, /synthetic/i]) {
      assert(meaning.test(steps), 'evaluation guidance omits ' + meaning);
    }
    assert(await page.locator('.architecture-flow > li').count() === 4, 'recorded-input system flow is incomplete');
    const scope = await page.locator('.scope-columns').innerText();
    for (const limit of [/human-reviewed/i, /candidate/i, /completed-turn response delay/i, /speaker playback/i]) {
      assert(limit.test(scope), 'guide omits remaining proof for ' + limit);
    }
    const brokenAnchors = await page.locator('a[href^="#"]').evaluateAll(links => links
      .filter(link => !document.getElementById(decodeURIComponent(link.hash.slice(1))))
      .map(link => link.hash));
    assert(brokenAnchors.length === 0, 'guide has missing anchor destinations: ' + brokenAnchors.join(', '));
    assert(await (await routeLink(page.locator('.guide-next'), '/live/')).isVisible(), 'guide has no actionable live-workspace link');
  });
  await test('judge evidence remains a pinned recorded snapshot with playback limits', async () => {
    const snapshot = page.locator('#replay-evidence');
    const text = await snapshot.innerText();
    assert(/replay v2/i.test(text) && /10 Oct 2026/.test(text), 'recorded snapshot identity or date missing');
    assert(/bcf50d1/.test(text) && /9805a06/.test(text), 'execution and artifact revisions are not distinguished');
    const rows = snapshot.locator('tbody tr');
    assert(await rows.count() === 2, 'snapshot comparison does not contain exactly the two evaluated configurations');
    assert(/Stock.*0\.2 s.*4 of 5/s.test(await rows.nth(0).innerText()), 'stock snapshot changed without revising its evidence check');
    assert(/Patient.*1\.0 s.*0 of 5/s.test(await rows.nth(1).innerText()), 'patient snapshot changed without revising its evidence check');
    assert(/not current backend status/i.test(text), 'recorded result is presented as current backend status');
    assert(/not been human-reviewed/i.test(text) && /speaker playback is unverified/i.test(text) && /browser plays no audio/i.test(text),
      'snapshot omits label or playback limitations');
    const evidence = snapshot.locator('a[href="https://github.com/vinhbin/stutterturn/tree/9805a06/agent/evidence/2026-10-10-replay-v2"]');
    assert(await evidence.isVisible(), 'snapshot does not link directly to the pinned v2 evidence');
  });
  await test('legacy judges route redirects to the guide and preserves the evidence fragment', async () => {
    await page.goto(origin + '/judges/#replay-evidence');
    await page.waitForURL(origin + '/judge/#replay-evidence');
    assert(await page.locator('#guide-title').isVisible(), 'legacy redirect did not load the guided evaluation');
    assert(await page.locator('#replay-evidence').isVisible(), 'preserved evidence fragment has no destination');
    assert(await page.locator('#console-frame').count() === 0, 'legacy alias retained the previous embedded console');
  });
  await test('judge chart renders saved database-query runs with snapshot provenance and reported-audio limits', async () => {
    const chart = page.locator('#tiger-chart');
    assert(await chart.count() === 1, 'judge route has no run-log chart');
    await chart.locator('.tgr-figure').first().waitFor();
    assert(await chart.locator('.tgr-lane').count() === 10, 'timeline omitted recorded runs');
    assert(await chart.locator('.tgr-gap-row').count() === 10, 'audio-gap chart omitted recorded runs');
    assert(await chart.locator('.tgr-head .tgr-badge-live').count() === 1, 'database-query snapshot lost its provenance');
    for (const figure of await chart.locator('.tgr-figure').all()) {
      assert(/snapshot.*Tiger\s?Data|Tiger\s?Data.*snapshot/i.test(await figure.innerText()), 'figure lacks saved database provenance');
    }
    const text = await chart.innerText();
    assert(/reported.*audio|audio.*reported/i.test(text) && /speaker playback.*unverified/i.test(text),
      'chart overstates audio events as verified playback');
    assert(/not.*live.*status/i.test(await page.locator('#run-log-evidence').innerText()),
      'saved chart is not distinguished from live status');
    assert(/0\.512 s/.test(text) && /9\.406 s/.test(text), 'per-run values do not match pinned evidence');
    const clip = chart.locator('.tgr-figure').first().locator('.tgr-clip').filter({ hasText: 'HeStutters_4_32.wav' });
    const modelMarks = clip.locator('.tgr-track .tgr-mark-complete');
    assert(await modelMarks.count() === 1, 'later fallback is incorrectly marked as a model decision');
  });
  for (const scenario of ['unavailable', 'missing provenance', 'database snapshot']) {
    await test('judge chart handles ' + scenario + ' without inventing live database status', async () => {
      const data = JSON.parse(fs.readFileSync(path.join(webRoot, 'tiger', 'snapshot.json'), 'utf8'));
      const chartPage = await reduced.newPage();
      await chartPage.route('**/tiger/snapshot.json', route => {
        if (scenario === 'unavailable') return route.fulfill({ status: 404, body: '' });
        if (scenario === 'missing provenance') delete data.offline_fallback;
        else {
          data.offline_fallback = false;
          data.source_note = 'Generated from TigerData queries over committed run logs.';
        }
        return route.fulfill({ contentType: 'application/json', body: JSON.stringify(data) });
      });
      try {
        await settled(chartPage, '/judge/');
        const chart = chartPage.locator('#tiger-chart');
        assert(await chart.count() === 1, 'judge route has no run-log chart');
        if (scenario === 'database snapshot') {
          await chart.locator('.tgr-badge-live').first().waitFor();
          assert(/snapshot.*Tiger\s?Data|Tiger\s?Data.*snapshot/i.test(await chart.locator('.tgr-badge-live').first().innerText()),
            'database export is presented as a live connection');
          assert(await chart.locator('.tgr-lane').count() === 10, 'database snapshot did not render its runs');
        } else {
          await chart.locator('.tgr-error').waitFor();
          assert(await chart.locator('.tgr-lane, .tgr-gap-row, .tgr-badge-live').count() === 0,
            'unavailable evidence produced a chart or database claim');
          assert(await chartPage.locator('#replay-evidence').isVisible(), 'chart failure hides the static evidence summary');
        }
      } finally { await chartPage.close(); }
    });
  }
  await reduced.close();

  const animated = await context({ reducedMotion: 'no-preference' });
  const motion = await animated.newPage();
  await settled(motion);
  await test('automatic animation pauses offscreen and resumes when visible', async () => {
    await motion.locator('.turn-figure').scrollIntoViewIfNeeded();
    await isPlaying(motion, true);
    await motion.locator('.site-footer').scrollIntoViewIfNeeded();
    await isPlaying(motion, false);
    await stablePosition(motion);
    await motion.locator('.turn-figure').scrollIntoViewIfNeeded();
    await isPlaying(motion, true);
  });
  await test('visibility changes pause and resume the active illustration', async () => {
    // Inject the browser's visibility signal; headless tabs do not reliably
    // become hidden merely because another Playwright tab is brought forward.
    await motion.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await isPlaying(motion, false);
    await stablePosition(motion);
    await motion.evaluate(() => {
      delete document.hidden;
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await isPlaying(motion, true);
  });
  await test('manual pause survives leaving and returning to the illustration', async () => {
    await motion.locator('#sequence-toggle').click();
    await isPlaying(motion, false);
    await motion.locator('.site-footer').scrollIntoViewIfNeeded();
    await motion.locator('.turn-figure').scrollIntoViewIfNeeded();
    await isPlaying(motion, false);
    await stablePosition(motion);
  });
  await animated.close();

  const noJs = await context({ javaScriptEnabled: false });
  const fallback = await noJs.newPage();
  await fallback.goto(origin + '/');
  await test('without JavaScript the story, complete diagram and navigation remain visible', async () => {
    assert(await fallback.locator('.hero h1').isVisible(), 'no-JS headline hidden');
    assert(await fallback.locator('.turn-diagram').isVisible(), 'no-JS diagram hidden');
    assert(await fallback.locator('.seg-reply').isVisible(), 'no-JS complete reply segment hidden');
    await fallback.locator('.seg-reply').scrollIntoViewIfNeeded();
    assert(await fallback.locator('.seg-reply').evaluate(element => {
      const box = element.getBoundingClientRect();
      return element.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2));
    }), 'no-JS completed reply is clipped away');
    assert(/no recorded timing or audio/i.test(await fallback.locator('.turn-figure figcaption').textContent()), 'no-JS provenance missing');
    assert(await fallback.locator('.sequence-transport').isHidden(), 'inert no-JS controls should remain hidden');
    const hiddenSections = await fallback.locator('main section').evaluateAll(sections => sections.filter(section => getComputedStyle(section).opacity === '0').length);
    assert(hiddenSections === 0, 'no-JS sections concealed by animation styles');
    await navigateHeader(fallback, '/judge/');
  });
  await test('without JavaScript the guide and direct-console fallback remain usable', async () => {
    assert(await fallback.locator('#guide-title').isVisible(), 'no-JS guide title hidden');
    assert(await fallback.locator('.evaluation-steps > li').count() === 4, 'no-JS evaluation steps missing');
    assert(await fallback.locator('#replay-evidence').isVisible(), 'no-JS evidence summary hidden');
    assert(await fallback.locator('#tiger-chart a[href="../tiger/snapshot.json"]').isVisible(),
      'no-JS chart fallback provides no direct evidence data');
    assert(await fallback.locator('#console-frame, #btn-start').count() === 0, 'no-JS guide contains run controls');
    await (await routeLink(fallback.locator('.guide-next'), '/live/')).click();
    await fallback.waitForURL(origin + '/live/');
    const direct = await routeLink(fallback.locator('.embed-fallback'), '/demo-ui/');
    assert(await direct.isVisible(), 'no-JS direct-console link hidden');
    await direct.click();
    await fallback.waitForURL(origin + '/demo-ui/');
  });
  await test('legacy judges route offers a working guide link without JavaScript', async () => {
    await fallback.goto(origin + '/judges/#replay-evidence');
    assert(new URL(fallback.url()).pathname === '/judges/', 'legacy no-JS fallback unexpectedly redirects');
    const link = await routeLink(fallback.locator('main'), '/judge/');
    assert(await link.isVisible(), 'legacy no-JS guide link is hidden');
    await link.click();
    await fallback.waitForURL(origin + '/judge/');
    assert(await fallback.locator('#guide-title').isVisible(), 'legacy fallback link did not open the guide');
  });
  await noJs.close();

  for (const width of [360, 390, 1280, 1440]) {
    const responsive = await context({ viewport: { width, height: width < 600 ? 844 : 900 } });
    const view = await responsive.newPage();
    for (const route of ['/', '/judge/', '/live/', '/demo-ui/']) {
      await test(width + 'px ' + route + ' contains content and navigation within the viewport', async () => {
        await settled(view, route);
        if (route === '/judge/') await view.locator('#tiger-chart .tgr-figure').first().waitFor();
        await contained(view);
        const nav = view.locator('.site-header nav');
        if (await nav.count()) {
          const rect = await nav.boundingBox();
          assert(rect && rect.x >= -1 && rect.x + rect.width <= width + 1, 'header navigation extends beyond viewport');
        }
      });
    }
    if (width < 600) {
      await test(width + 'px toolbar link moves keyboard focus to run setup', async () => {
        await settled(view, '/demo-ui/');
        const jump = view.locator('.workspace-toolbar a[href="#run-setup"]');
        assert(await jump.isVisible(), 'mobile setup link hidden');
        const rect = await jump.boundingBox();
        assert(rect && rect.y >= 0 && rect.y + rect.height <= 844, 'setup link is outside the initial mobile viewport');
        await jump.focus();
        await jump.press('Enter');
        await view.waitForFunction(() => {
          const setup = document.getElementById('run-setup');
          return document.activeElement === setup && setup.getBoundingClientRect().top >= 0 && setup.getBoundingClientRect().top < innerHeight;
        });
        assert(await view.locator('#run-setup').getAttribute('tabindex') === '-1', 'setup destination lost its programmatic focus target');
      });
      await test(width + 'px empty ledger caption and message remain readable without horizontal scrolling', async () => {
        await settled(view, '/demo-ui/');
        await view.locator('#event-caption').scrollIntoViewIfNeeded();
        const info = await view.evaluate(() => {
          const caption = document.getElementById('event-caption');
          const region = document.getElementById('event-scroll');
          const message = document.querySelector('#event-body .empty-row td');
          const text = document.createRange(); text.selectNodeContents(message);
          return { captionTag: caption.tagName, captionInside: region.contains(caption),
            captionLeft: caption.getBoundingClientRect().left, captionRight: caption.getBoundingClientRect().right,
            textLeft: text.getBoundingClientRect().left, textRight: text.getBoundingClientRect().right,
            align: getComputedStyle(message).textAlign, scrollLeft: region.scrollLeft, width: innerWidth,
            description: document.getElementById('event-table').getAttribute('aria-describedby') };
        });
        assert(info.captionTag === 'P' && !info.captionInside, 'caption is still inside the overflowing table');
        assert(info.description === 'event-caption', 'table lost its accessible caption description');
        assert(info.captionLeft >= 0 && info.captionRight <= info.width + 1, 'caption extends beyond phone width');
        assert(info.scrollLeft === 0 && info.textLeft >= 0 && info.textRight <= info.width + 1,
          'empty message is clipped at the initial scroll position: ' + JSON.stringify(info));
        assert(['left', 'start'].includes(info.align), 'empty message is centered in the oversized table');
        assert(await view.locator('.ledger-scroll-hint').isVisible(), 'mobile ledger scroll hint hidden');
        await contained(view);
      });
      await test(width + 'px populated ledger supports keyboard horizontal scrolling without moving its caption', async () => {
        await enablePreview(view);
        await view.locator('#btn-start').click();
        await view.waitForFunction(() => document.getElementById('event-scroll').tabIndex === 0 &&
          !document.querySelector('#event-body .empty-row'));
        const ledger = view.locator('#event-scroll');
        await ledger.focus();
        assert(await view.locator('.ledger-keyboard-tip').isVisible(), 'keyboard scrolling hint missing once events exist');
        const captionX = await view.locator('#event-caption').evaluate(element => element.getBoundingClientRect().x);
        await ledger.press('ArrowRight');
        await view.waitForFunction(() => document.getElementById('event-scroll').scrollLeft > 0);
        assert(await view.locator('#event-caption').evaluate(element => element.getBoundingClientRect().x) === captionX,
          'horizontal ledger scrolling also moves the run caption');
        const captionText = await view.locator('#event-caption').evaluate(element => {
          const range = document.createRange(); range.selectNodeContents(element);
          return [...range.getClientRects()].every(rect => rect.left >= 0 && rect.right <= innerWidth + 1);
        });
        assert(captionText, 'populated run caption text does not wrap within the viewport');
        await contained(view);
        await view.locator('#btn-reset').click();
      });
      await test(width + 'px landing diagram preserves readable phases in a keyboard-scrollable track', async () => {
        await settled(view, '/');
        const diagram = view.locator('.turn-diagram');
        assert(await diagram.getAttribute('tabindex') === '0', 'diagram is not keyboard focusable');
        assert(await diagram.getAttribute('aria-describedby') === 'diagram-scroll-note', 'diagram does not identify its scroll instructions');
        assert(await view.locator('#diagram-scroll-note').isVisible(), 'mobile diagram scroll note hidden');
        const sizing = await diagram.evaluate(element => ({ content: element.querySelector('.diagram-grid').getBoundingClientRect().width,
          overflow: element.scrollWidth - element.clientWidth }));
        assert(sizing.content >= 520 && sizing.overflow > 0, 'diagram compressed its phases instead of scrolling internally');
        const tiny = await view.locator('.turn-figure .lane-tag, .turn-figure .ruler-tick, .turn-figure .decision-flag, .turn-figure .seg, .turn-figure .hold-label, .turn-figure .state-chip, .clock-label, #sequence-phase, #sequence-note, .sequence-transport label').evaluateAll(elements =>
          elements.filter(element => element.textContent.trim() && parseFloat(getComputedStyle(element).fontSize) < 11)
            .map(element => element.textContent.trim()));
        assert(tiny.length === 0, 'functional phase labels below 11px: ' + tiny.join(', '));
        await diagram.focus();
        await diagram.press('ArrowRight');
        await view.waitForFunction(() => document.querySelector('.turn-diagram').scrollLeft > 0);
        await contained(view);
      });
    }
    await test(width + 'px live iframe fits its document after enabling preview', async () => {
      await settled(view, '/live/');
      const frame = view.frames().find(item => new URL(item.url()).pathname === '/demo-ui/');
      assert(frame, 'console iframe did not load');
      await frame.waitForSelector('html.embedded-console');
      assert(await view.locator('#evaluation-steps, #replay-evidence').count() === 0, 'live route repeats the static evaluation guide');
      assert(await frame.locator('#btn-start').isDisabled(), 'live workspace can run before an explicit connection or preview choice');
      assert(await frame.locator('#preview-toggle').isChecked() === false, 'live workspace automatically enabled synthetic preview');
      await enablePreview(frame);
      await frame.locator('#btn-start').click();
      await frame.waitForFunction(() => document.getElementById('run-phase').textContent === 'running');
      await view.waitForFunction(() => {
        const element = document.getElementById('console-frame');
        const body = element.contentDocument.body;
        const difference = element.clientHeight - body.getBoundingClientRect().height;
        return difference >= -1 && difference <= 6;
      }, null, { timeout: 5000 });
      await contained(view); await contained(frame);
      assert(/DEVELOPMENT PREVIEW/i.test(await frame.locator('#preview-banner').textContent()), 'embedded preview is not labeled');
      assert(/no (?:response )?audio/i.test(await frame.locator('#audio-note').textContent()), 'embedded no-audio note missing');
      await frame.locator('#btn-reset').click();
    });
    if (width >= 1280) {
      await test(width + 'px standalone preview exposes Start in the first 900px', async () => {
        await settled(view, '/demo-ui/');
        await enablePreview(view);
        await view.evaluate(() => window.scrollTo(0, 0));
        const rect = await view.locator('#btn-start').boundingBox();
        assert(await view.locator('#btn-start').isEnabled(), 'preview start disabled');
        assert(rect && rect.y >= 0 && rect.y + rect.height <= 900, 'Start below first viewport: ' + JSON.stringify(rect));
        await contained(view);
      });
    }
    await responsive.close();
  }
  await test('site interactions produce no browser errors, external requests or backend connections', async () => {
    assert(pageErrors.length === 0, 'page errors: ' + pageErrors.join(' | '));
    assert(unexpectedRequests.length === 0, 'unexpected external requests: ' + unexpectedRequests.join(' | '));
    assert(unexpectedSockets.length === 0, 'unexpected WebSocket connections: ' + unexpectedSockets.join(' | '));
  });
} finally {
  await browser.close();
  server.close();
  server.closeAllConnections();
}

console.log('\nsite-checks: ' + passed + '/' + (passed + failures.length) + ' passed');
if (failures.length) process.exit(1);
