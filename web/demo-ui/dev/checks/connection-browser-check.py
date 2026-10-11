"""Hosted connection UX with intercepted HTTPS + WebSocket; no real API calls."""
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[2]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for scenario in ('healthy', 'unavailable', 'authentication', 'dropped', 'fixed'):
        context = browser.new_context()
        page = context.new_page()
        errors, requests, sockets, messages = [], [], [], []
        failure = [503 if scenario == 'unavailable' else 401 if scenario == 'authentication' else 0]
        page.on('pageerror', lambda error: errors.append(str(error)))

        def route(request):
            path = urlparse(request.request.url).path
            if path.startswith('/v0/'):
                requests.append(path)
                if failure[0]:
                    request.fulfill(status=failure[0], body='Unavailable')
                    return
                data = {
                    '/v0/health': dict(ok=True, contract='0.1', browser_audio='pcm16-v1',
                                       response=dict(mode='fixed' if scenario == 'fixed' else 'live_api', delay_s=1.0)),
                    '/v0/configurations': [dict(id='stock', label='Stock model', available=True),
                                           dict(id='candidate', label='Candidate model', available=True)],
                    '/v0/sources': [dict(source_id='First recording', file='first.wav', duration_s=3),
                                   dict(source_id='Second recording', file='second.wav', duration_s=10)]
                }[path]
                request.fulfill(json=data)
            else:
                relative = path.removeprefix('/demo-ui/') or 'index.html'
                file = (root / relative).resolve()
                assert file.is_relative_to(root)
                request.fulfill(status=200 if file.exists() else 404,
                                body=file.read_bytes() if file.exists() else b'',
                                content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream')

        page.route('https://console.example/**', route)

        def socket(ws):
            sockets.append(ws)
            ws.on_message(lambda message: messages.append(message))

        page.route_web_socket('wss://console.example/v0/ws', socket)
        page.goto('https://console.example/demo-ui/')
        expect(page.locator('.connection-settings')).not_to_have_attribute('open', '')
        expect(page.locator('#backend-url')).to_be_hidden()
        if failure[0]:
            expect(page.locator('#status-banner')).to_contain_text('sign in' if failure[0] == 401 else '503', timeout=5000)
            expect(page.locator('#btn-retry')).to_be_visible()
            expect(page.locator('#btn-start')).to_be_disabled()
            failure[0] = 0
            page.locator('#btn-retry').click()
        expect(page.locator('#source-select')).to_be_enabled(timeout=5000)
        expect(page.locator('#source-select option')).to_have_count(2)
        expect(page.locator('#config-group input:enabled')).to_have_count(2)
        expect(page.locator('#btn-start')).to_be_enabled()
        if scenario == 'fixed':
            expect(page.locator('#response-mode-banner')).to_be_visible()
            expect(page.locator('#response-mode-banner')).to_contain_text('1.0 s simulated delay')
            expect(page.locator('#response-mode-banner')).to_contain_text('No Gemini or ElevenLabs calls')
        else:
            expect(page.locator('#response-mode-banner')).to_be_hidden()
        expect(page.locator('#btn-retry')).to_be_hidden()
        page.locator('#source-select').select_option('second.wav')
        page.locator('input[value="candidate"]').check()
        if scenario == 'dropped':
            sockets[-1].close(code=1011, reason='Test disconnect')
            expect(page.locator('#btn-retry')).to_be_visible()
            page.locator('#btn-retry').click()
            expect(page.locator('#btn-retry')).to_be_hidden()
            expect(page.locator('#source-select')).to_be_enabled()
        # Discovery must never start a paid run or unlock/play audio.
        assert not messages, messages
        assert len(sockets) >= 1
        assert not errors, errors
        print(json.dumps({'scenario': scenario, 'requests': requests, 'paid_runs_started': 0}))
        context.close()
    browser.close()
