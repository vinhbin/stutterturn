"""Chromium Web Audio rendering checks, plus optional real hosted API smoke runs.

python web/demo-ui/dev/checks/audio-browser-check.py
Add --access-file PRIVATE_JSON --out OUTPUT_DIR for paid hosted checks.
Access JSON holds url, username, password; no credentials or PCM are saved.
Requires Python playwright and its Chromium browser.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ap = argparse.ArgumentParser()
ap.add_argument('--access-file', type=Path)
ap.add_argument('--out', type=Path)
args = ap.parse_args()
root = Path(__file__).resolve().parents[4]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.add_script_tag(path=str(root / 'web/demo-ui/browser-audio.js'))
    rendered = page.evaluate('''async () => {
      const results = [];
      for (const stop of [false, true]) {
        const context = new OfflineAudioContext(1, 24000, 16000);
        const player = new StutterTurnBrowserAudio({context});
        const pcm = n => btoa(String.fromCharCode(...new Uint8Array(new Int16Array(n).fill(8192).buffer)));
        const send = (action, extra = {}) => player.receive({run_id:'test', action, sample_rate:16000, sample:0, ...extra});
        player.begin('test');
        send('source', {pcm:pcm(16000)});
        send('agent', {pcm:pcm(1600), generation:1});
        send('cancel', {generation:1, sample:800});
        send('agent', {pcm:pcm(1600), generation:1});
        if (stop) player.stop();
        const buffer = await context.startRendering();
        const samples = buffer.getChannelData(0);
        results.push({stop, before:samples[4200], after:samples[5200], tail:samples[22000]});
      }
      return results;
    }''')
    assert rendered == [dict(stop=False, before=.5, after=.25, tail=0),
                        dict(stop=True, before=0, after=0, tail=0)], rendered
    print(json.dumps({'synthetic_web_audio_render': rendered}))
    page.close()
    if args.access_file:
        assert args.out, '--out is required for hosted evidence'
        args.out.mkdir(parents=True, exist_ok=True)
        access = json.loads(args.access_file.read_text())
        context = browser.new_context(http_credentials={k: access[k] for k in ('username', 'password')},
                                      viewport={'width': 1440, 'height': 1100})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(access['url'], wait_until='networkidle')
        frame = page.frame_locator('#console-frame')
        iframe = page.locator('#console-frame').element_handle().content_frame()
        iframe.evaluate('''() => {
          const proto = StutterTurnBrowserAudio.prototype;
          const begin = proto.begin, receive = proto.receive;
          proto.begin = function(id) {
            begin.call(this, id); window.audioPlayer = this;
            const probe = window.audioProbe = {id, peaks:{source:0, agent:0, mixed:0}, latest:0, state:this.context.state};
            const mute = this.context.createGain(); mute.gain.value = 0; mute.connect(this.context.destination);
            const analysers = {};
            for (const name of ['source', 'agent', 'mixed']) {
              const analyser = this.context.createAnalyser(); analyser.fftSize = 256; analyser.connect(mute);
              analysers[name] = analyser;
            }
            this.output.connect(analysers.mixed);
            this._testAnalysers = analysers;
            const timer = setInterval(() => {
              if (window.audioProbe !== probe) { clearInterval(timer); return; }
              for (const [name, analyser] of Object.entries(analysers)) {
                const samples = new Float32Array(256); analyser.getFloatTimeDomainData(samples);
                const peak = Math.max(...samples.map(Math.abs)); probe.peaks[name] = Math.max(probe.peaks[name], peak);
                if (name === 'mixed') probe.latest = peak;
              }
            }, 10);
          };
          proto.receive = function(message) {
            const before = new Set(this.nodes); receive.call(this, message);
            for (const node of this.nodes) {
              if (!before.has(node)) node.node.connect(this._testAnalysers[message.action]);
            }
          };
        }''')
        expect(frame.locator('#source-select')).to_be_enabled(timeout=20000)
        runs = []
        for config in ('stock_fp32', 'candidate'):
            frame.locator('#source-select').select_option('HeStutters_4_32.wav')
            frame.locator(f'input[value="{config}"]').check()
            frame.locator('#btn-start').click()
            expect(frame.locator('#summary-note')).to_contain_text('End reason: completed', timeout=60000)
            result = iframe.evaluate('''() => ({...audioProbe, stats:audioPlayer.stats,
                pendingNodes:audioPlayer.nodes.size, status:document.querySelector('#audio-status').textContent,
                reply:document.querySelector('#reply-text').textContent})''')
            assert result['state'] == 'running' and result['pendingNodes'] == 0, result
            assert all(result['peaks'][kind] > .001 for kind in ('source', 'agent', 'mixed')), result
            assert result['reply'] != 'No reply yet.', result
            response = context.request.get(access['url'].split('/live/')[0] + '/v0/runs/' + result['id'])
            assert response.ok
            log = response.text()
            assert '"pcm"' not in log and '"browser_audio"' not in log
            (args.out / (result['id'] + '.jsonl')).write_text(log, encoding='utf-8')
            runs.append({'config': config, **result})
            print(json.dumps({'completed': config, 'run_id': result['id'], 'peaks': result['peaks']}), flush=True)
        # Stop during a real generated reply, then reset and restart the source.
        stop_attempts = []
        for attempt in range(2):
            frame.locator('#btn-start').click()
            expect(frame.locator('#run-phase')).to_have_text('running', timeout=20000)
            iframe.wait_for_function("(window.audioProbe && audioProbe.peaks.agent > .001 && audioPlayer.nodes.size > 0) || document.querySelector('#run-phase').textContent === 'ended'", timeout=45000)
            stop_attempts.append(iframe.evaluate('({id:audioProbe.id, agentPeak:audioProbe.peaks.agent})'))
            if stop_attempts[-1]['agentPeak'] > .001:
                break
        assert stop_attempts[-1]['agentPeak'] > .001, stop_attempts
        frame.locator('#btn-stop').click()
        page.wait_for_timeout(300)
        stop_reply = iframe.evaluate('({pending:audioPlayer.nodes.size, peak:audioProbe.latest})')
        assert stop_reply['pending'] == 0 and stop_reply['peak'] < .00001, stop_reply
        frame.locator('#btn-reset').click()
        frame.locator('#source-select').select_option('demo-long-WomenWhoStutter_19_1238s.wav')
        frame.locator('#btn-start').click()
        iframe.wait_for_function('window.audioProbe && audioProbe.peaks.source > .001 && audioPlayer.nodes.size > 0', timeout=30000)
        frame.locator('#btn-reset').click()
        page.wait_for_timeout(300)
        reset_source = iframe.evaluate('({pending:audioPlayer.nodes.size, peak:audioProbe.latest})')
        assert reset_source['pending'] == 0 and reset_source['peak'] < .00001, reset_source
        assert not errors, errors
        report = {'url': access['url'], 'browser': 'Chromium', 'tls_verification': True,
                  'synthetic_render': rendered, 'real_runs': runs, 'stop_generated_reply': stop_reply,
                  'reset_source_after_restart': reset_source, 'stop_attempts': stop_attempts, 'page_errors': errors,
                  'limit': 'Digital Web Audio graph measured; human listening and acoustic latency not measured.'}
        (args.out / 'browser-audio-check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        page.screenshot(path=str(args.out / 'hosted-audio-console.png'), full_page=True)
        print(json.dumps({'hosted_audio_checks': 'passed', 'stop_reply': stop_reply, 'reset_source': reset_source}))
    browser.close()
