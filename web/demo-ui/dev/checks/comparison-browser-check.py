"""Judge evidence and replay presets, using intercepted HTTPS; no paid runs."""
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

WEB = Path(__file__).resolve().parents[3]
SOURCE = 'demo-long-WomenWhoStutter_19_1238s.wav'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for scenario in ('desktop', 'mobile', 'missing-data', 'missing-provenance', 'candidate', 'stock_fp32', 'invalid'):
        context = browser.new_context(viewport={'width': 390 if scenario == 'mobile' else 1440, 'height': 1000})
        page = context.new_page()
        errors, sent = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))

        def route(request):
            path = urlparse(request.request.url).path
            if path.startswith('/v0/'):
                data = {
                    '/v0/health': dict(ok=True, contract='0.1', browser_audio='pcm16-v1'),
                    '/v0/configurations': [dict(id=c, label=c, available=True) for c in ('stock', 'stock_fp32', 'candidate')],
                    '/v0/sources': [dict(file='first.wav', source_id='First', duration_s=3),
                                   dict(file=SOURCE, source_id=SOURCE, duration_s=10.4)]
                }[path]
                request.fulfill(json=data)
                return
            file = (WEB / path.lstrip('/')).resolve()
            assert file.is_relative_to(WEB)
            if file.is_dir():
                file /= 'index.html'
            if path == '/tiger/comparison.json' and scenario.startswith('missing-'):
                data = json.loads(file.read_text())
                data.pop('offline_fallback')
                request.fulfill(status=503 if scenario == 'missing-data' else 200, json=data)
                return
            request.fulfill(status=200 if file.exists() else 404,
                            body=file.read_bytes() if file.exists() else b'',
                            content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream')

        page.route('https://demo.example/**', route)
        page.route_web_socket('wss://demo.example/v0/ws', lambda ws: ws.on_message(lambda msg: sent.append(msg)))
        if scenario in ('candidate', 'stock_fp32', 'invalid'):
            requested = scenario if scenario != 'invalid' else 'unknown'
            source = SOURCE if scenario != 'invalid' else '../../secret.wav'
            page.goto(f'https://demo.example/live/?source={source}&config={requested}')
            frame = page.frame_locator('#console-frame')
            expect(frame.locator('#source-select')).to_be_enabled()
            expect(frame.locator('#source-select')).to_have_value(source if scenario != 'invalid' else 'first.wav')
            expect(frame.locator(f'input[value="{requested if scenario != "invalid" else "stock"}"]')).to_be_checked()
            expect(frame.locator('#btn-start')).to_be_enabled()
            # User choice after applying a preset stays authoritative.
            frame.locator('#source-select').select_option('first.wav')
            frame.locator('input[value="stock"]').check()
            expect(frame.locator('#source-select')).to_have_value('first.wav')
        else:
            page.goto('https://demo.example/judge/')
            comparison = page.locator('#model-comparison')
            if scenario.startswith('missing-'):
                expect(comparison).to_contain_text('could not be loaded')
                expect(comparison.locator('table')).to_have_count(0)
            else:
                expect(comparison).to_contain_text('Our model held the early pause')
                expect(comparison.locator('tbody tr')).to_have_count(7)
                # Stock has an earlier interrupted reply; final timing must ignore it.
                expect(comparison.locator('.cmp-waiting')).to_contain_text('1.916 s')
                expect(comparison.locator('.cmp-waiting')).to_contain_text('2.421 s')
                final_decision = comparison.locator('tr').filter(has_text='Decision after final detected speech stop')
                expect(final_decision.locator('td')).to_have_text(['0.192 s', '0.192 s'])
                expect(comparison).to_contain_text('0.050 s')
                expect(comparison).to_contain_text('None reported')
                expect(comparison).to_contain_text('Both runs completed with Gemini replies')
                expect(comparison).not_to_contain_text('Empty Gemini reply')
                expect(page.locator('#tiger-chart .tgr-lane')).to_have_count(10)
                expect(page.locator('#tiger-chart .tgr-lane-tag').filter(has_text='Our X1')).to_have_count(10)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert comparison.locator('svg text').first.evaluate("e => getComputedStyle(e).stroke") == 'none'
                if scenario == 'mobile':
                    cell = comparison.locator('thead th').last.bounding_box()
                    assert cell['x'] + cell['width'] <= 390
                    assert comparison.locator('td').evaluate_all('cells => cells.every(c => c.scrollWidth <= c.clientWidth)')
                comparison.locator('summary').click()
                expect(comparison).to_contain_text('p=0.5432, threshold=0.6')
                expect(comparison).to_contain_text('20261011T061006Z-stock_fp32-8d16')
                page.locator('a:has-text("Hear our model")').click()
                frame = page.frame_locator('#console-frame')
                expect(frame.locator('#source-select')).to_have_value(SOURCE)
                expect(frame.locator('input[value="candidate"]')).to_be_checked()
        assert not errors, errors
        assert not sent, sent
        print(json.dumps({'scenario': scenario, 'passed': True, 'paid_runs': 0}))
        context.close()
    browser.close()
