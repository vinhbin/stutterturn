// Deterministic browser playback lifecycle checks; synthetic PCM, no API calls.
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
const window = { atob };
new Function('window', readFileSync('web/demo-ui/browser-audio.js', 'utf8'))(window);
new Function('window', readFileSync('web/demo-ui/adapter.js', 'utf8'))(window);
class Context {
  currentTime = 10; state = 'running'; destination = {}; created = [];
  resume() { return Promise.resolve(); }
  createGain() { return { connect() {}, gain: { value: 1 } }; }
  createBuffer(_, n, rate) { return { duration: n / rate, getChannelData: () => new Float32Array(n) }; }
  createBufferSource() {
    const node = { connect() {}, disconnect() {}, start(...args) { this.started = args; },
      stop(at) { this.stopped = at ?? 0; }, onended: null };
    this.created.push(node); return node;
  }
}
const pcm = Buffer.from(new Int16Array(1600).fill(8192).buffer).toString('base64');
const packet = (action, extra = {}) => ({ run_id: 'one', sample_rate: 16000, action, sample: 0, pcm, ...extra });
function fixture() {
  const context = new Context(); const audio = new window.StutterTurnBrowserAudio({ context });
  audio.begin('one'); audio.receive(packet('source')); return { audio, context };
}
test('source and agent share one timeline; volume clamps', () => {
  const { audio, context } = fixture();
  audio.receive(packet('agent', { sample: 8000, generation: 1 }));
  assert.deepEqual(context.created.map(n => n.started[0]), [10.25, 10.75]);
  audio.setVolume(0); assert.equal(audio.output.gain.value, 0);
  audio.setVolume(2); assert.equal(audio.output.gain.value, 1);
});
test('barge-in cancels only matching generation; retired chunks stay silent', () => {
  const { audio, context } = fixture();
  audio.receive(packet('agent', { generation: 1 }));
  audio.receive(packet('cancel', { generation: 1, sample: 512 }));
  audio.receive(packet('agent', { generation: 1 }));
  audio.receive(packet('agent', { generation: 2 }));
  assert.equal(context.created.length, 3);
  assert.equal(context.created[0].stopped, undefined);
  assert.equal(context.created[1].stopped, 10.282);
  assert.equal(context.created[2].stopped, undefined);
});
test('Stop silences source and reply, new run ignores previous packets', () => {
  const { audio, context } = fixture();
  audio.receive(packet('agent', { generation: 1 })); audio.stop();
  assert.ok(context.created.every(n => n.stopped === 0)); assert.equal(audio.nodes.size, 0);
  audio.begin('two'); audio.receive(packet('source'));
  assert.equal(audio.epoch, null); assert.equal(context.created.length, 2);
});
test('normal completion drains the final buffer before resolving', async () => {
  const { audio, context } = fixture(); audio.receive(packet('finish'));
  let done = false; const drained = audio.drain().then(() => { done = true; });
  await Promise.resolve(); assert.equal(done, false);
  context.created[0].onended(); await drained; assert.equal(done, true);
});
test('malformed, oversized and duplicated audio fail; late audio skips elapsed samples', () => {
  const { audio, context } = fixture();
  assert.throws(() => audio.receive(packet('source')), /Duplicate/);
  assert.throws(() => audio.receive(packet('agent', { generation: 1, pcm: 'AA==' })), /PCM/);
  assert.throws(() => audio.receive(packet('agent', { generation: 1, pcm: 'A'.repeat(22000) })), /bounds/);
  context.currentTime = 10.30;
  audio.receive(packet('agent', { generation: 1 }));
  assert.ok(Math.abs(context.created[1].started[1] - .05) < .00001);
});
function adapterFixture() {
  const adapter = new window.StutterTurnAdapters.live({ baseUrl: 'https://example.com' });
  const { audio, context } = fixture(); const ends = [], errors = [];
  adapter._audio = audio;
  adapter._run = { id: 'one', seq: 0, audio: true, audioSeq: -1, pending: false,
    handlers: { onEnd: x => ends.push(x), onError: x => errors.push(x) } };
  const send = message => adapter._message(JSON.stringify({ v: '0.1', ...message }));
  return { adapter, audio, context, ends, errors, send };
}
test('audio sequence is separate from event sequence; end waits for browser drain', async () => {
  const f = adapterFixture();
  f.send({ type: 'browser_audio', audio_seq: 0, ...packet('finish') });
  assert.equal(f.adapter._run.seq, 0);
  f.send({ type: 'run_ended', run_id: 'one', seq: 1, t: 1, reason: 'completed', summary: {} });
  assert.equal(f.ends.length, 0); f.context.created[0].onended();
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(f.ends.length, 1); assert.deepEqual(f.errors, []);
});
test('audio sequence gaps fail closed and immediately silence source', () => {
  const f = adapterFixture();
  f.send({ type: 'browser_audio', audio_seq: 2, ...packet('agent', { generation: 1 }) });
  assert.equal(f.errors.length, 1); assert.equal(f.audio.nodes.size, 0);
});
test('Stop during draining never delivers an old end to a fresh run', async () => {
  const f = adapterFixture();
  f.send({ type: 'browser_audio', audio_seq: 0, ...packet('finish') });
  f.send({ type: 'run_ended', run_id: 'one', seq: 1, t: 1, reason: 'completed', summary: {} });
  f.adapter.stop(); await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(f.ends.length, 0); assert.equal(f.audio.nodes.size, 0);
});
