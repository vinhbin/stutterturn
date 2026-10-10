# Contract development mock

This server emits **synthetic contract fixtures only**. It has no recordings,
microphone, model, API keys, speech services or audio playback. It is not the voice
agent and cannot support efficacy or audible-interruption claims. Stock and patient
receive the same script; the candidate is unavailable.

From the repository root, in two terminals:

```sh
python -m http.server 8040 --bind 127.0.0.1 --directory web/demo-ui
python web/demo-ui/dev/mock-agent-server.py
```

Open `http://127.0.0.1:8040/`, connect to `http://127.0.0.1:8765`, choose a fixture and
start a fresh run. The page must say **MOCK BACKEND — SYNTHETIC**. Choose `overlap.fixture`,
`held.fixture`, `cancelled.fixture`, `timeout.fixture` or `no-response.fixture` to
exercise each outcome. The names identify scripted UI states, not real sources.

Python 3.9+ and its standard library are sufficient. The loopback-only server
implements the proposed v0.1 HTTP discovery and text WebSocket commands needed by
the UI; it is a development helper, not a production WebSocket implementation.
Every response object and socket message contains `mock: true` and a mock label.
Logs for the most recent 20 synthetic runs are held in memory and can be read from
`GET /v0/runs/{run_id}` as JSON lines. Nothing is saved as benchmark evidence.

Optional: `--port 8766` changes the port; `--speed 4` accelerates fixtures while
leaving their **synthetic source timestamps** unchanged. The default runs at 1×.
Stop with Ctrl+C. Stopping the mock during a run exercises the page's connection
failure state; reconnect explicitly to start a new run. Reset must discard late
events and previous results.

The real backend still needs to supply its own server, allowed replay sources and
verified playback evidence. This mock does not fill those acceptance gates.
