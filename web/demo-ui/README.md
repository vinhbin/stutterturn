# StutterTurn call console

Vinh's comparison surface. Plain HTML/CSS/JavaScript, no build or runtime packages.
Owned paths: `web/demo-ui/**`; Kareem owns the surrounding judges page.

Targets Guttuu's [proposed v0.1 contract](https://github.com/vinhbin/stutterturn/blob/a229787/agent/CONTRACT.md).
UI checks and fixtures do not establish a working voice agent, audible output,
trained candidate or matched evaluation. PLAN.md remains the task-status authority.

## Run

From the repository root:

```sh
python -m http.server 8040 --bind 127.0.0.1 --directory web/demo-ui
```

Open `http://127.0.0.1:8040/`. Connect explicitly to the agent URL, or enable the
labeled synthetic preview. Nothing connects or starts a recording automatically.

To exercise the full HTTP/WebSocket path without a voice backend:

```sh
python web/demo-ui/dev/mock-agent-server.py
```

Connect the page to `http://127.0.0.1:8765`, select a fixture and start. The page
must say **MOCK BACKEND — SYNTHETIC**. No audio plays. Stock and patient receive identical
scripts; the candidate stays unavailable. See [mock instructions](dev/README.md)
for overlap, holding, cancellation, timeout, no-response and disconnect scenarios.
The separate preview requires no server and also remains labeled synthetic.

A real server must permit the page's HTTP origin for discovery. An HTTPS page
needs an HTTPS/WSS backend. Never put API keys in the page or URL. The proposed
contract carries events, **not browser audio**.

## Reading the display

- Run identity comes from `run_started`. Configuration/source changes are locked
  during pending and active runs. Reset discards previous callbacks and results.
- Completion means `turn_complete`, not `turn_incomplete`. A `fallback_timeout`
  completion is agent logic rather than a model prediction.
- Audio onset means `agent_audio_start`, not `agent_audio_end` or `overlap`.
  Timings are **backend-reported, playback unverified**: at inspected engine commit
  `a229787`, onset means first PCM received, with no output playback implemented.
- `services: off` means model-only with no generated response. Mock/preview audio
  events only illustrate UI states and prove no playback or interruption.
- Cancellation, resumption, timeouts, no response and final summary stay visible.
  Missing values stay missing, not zero. Logs retain the run and configuration.
- Caller and reported-agent tracks share event time. Decision flags and amber
  holding spans come from reported events. Red overlap spans close at the first
  explicit caller speech-stop or agent audio-end; aggregate summary durations
  never supply a guessed position. Dashed endpoints remain unreported.
- Metadata preserves source identity/offset, configuration parameters, model hash
  and commit when supplied. `t` is seconds since the source entered the pipeline;
  add `source_offset_s` to align with the named source. Human labels are separate.

Only verified real provenance supports a real-recording label. Nobody imitates
stuttering; fixtures and automated waveforms do not count as human listening.

## Adapter boundary

The live adapter uses `/v0/health`, `/v0/configurations`, `/v0/sources`, `/v0/ws`.
Backend IDs are preserved (`candidate`); the preview's `stutterturn` is a fixture
label. Unavailable arms stay unavailable.

```js
const adapter = new window.StutterTurnAdapters.live({baseUrl});
const {configurations, sources, health} = await adapter.connect();
const info = await adapter.start(configId, {
  onEvent(event) {}, // full named event with run_id, seq, t
  onEnd(message) {}, // run_ended with summary
  onError(message) {}
}, source.file);
// info: {runId, runIdNote, sourceRecording, metadata: fullRunStartedMessage}
adapter.stop();
adapter.disconnect();
```

`getConfigurations()`/`getSources()` return discovery data. Connection/start waits
are bounded, versions validated, sequence disorder surfaced and stale-run events
discarded. Reconnection never replays a source by itself. Runtime strings are
rendered as text. `health.mock: true` selects mock labeling; mock socket messages
must also carry `mock: true`.

## Keyboard and embedding

Native controls retain visible focus. Arrow keys choose a radio. Outside editable
text/select controls: `1`–`3` choose an arm, `S` starts, `X` stops, `R` resets, `P`
switches preview. Focus the timeline and use arrow keys to scroll when it overflows.
Reduced motion disables animation without hiding state.

Serve `web/` and link `/demo-ui/`, or embed:

```html
<iframe src="/demo-ui/" title="StutterTurn call console"
        style="width:100%;height:1100px;border:0"></iframe>
```

## Validation and real acceptance

Development test harnesses stay outside the repository, as requested in the
builder handoff. The stdlib contract mock is the only repository test helper.
See [verification notes](verification.md) for recorded checks and their scope. F2/I1
still need an actual server, real source replay and playback, stop/reset/reconnect
against that service, and attributable saved evidence. Candidate acceptance also
needs Niko's export and compatibility proof. A fixture pass satisfies neither gate.

## Fonts and design reference

Archivo supplies the wordmark/tally; JetBrains Mono supplies measurements; body
text uses the system stack. Both fonts are hosted locally under the SIL Open Font
License. `fonts/` contains licenses, source URLs and SHA-256 hashes. Latin subsets
fall back to system fonts for other scripts; venue Wi-Fi is unnecessary for styling.

The recovered brief specifies a broadcast console with an event timeline. The
[ElevenLabs waveform reference](https://ui.elevenlabs.io/docs/components/live-waveform)
informed audio-state clarity; its microphone waveform needs real input. This UI
therefore draws timestamped events, never an invented waveform. No ElevenLabs
React component or SDK integration is implied by the visual reference.

The implemented tokens and responsive rules are recorded in [DESIGN.md](DESIGN.md).
