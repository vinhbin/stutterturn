# StutterTurn presentation site

The landing page, judge guide and live workspace share a cool charcoal/cyan
studio identity: local Archivo/JetBrains Mono, prominent transport controls,
and distinct caller/agent states. Plain HTML/CSS/JavaScript; no build
step or runtime packages.

## Open locally

From this repository root:

```sh
python -m http.server 8041 --bind 127.0.0.1 --directory web
```

- `/` introduces the project and the recorded-source comparison.
- `/judge/` guides evaluation: the hypothesis, recorded evidence, comparison
  steps, architecture, and limitations. It does not embed or start a console.
- `/live/` presents the operational replay workspace and current run.
- `/judges/` preserves older links by redirecting to `/judge/`, with a visible
  link when JavaScript is disabled.
- `/demo-ui/` opens the console directly, with all run controls and metadata.

The live page embeds the same console rather than maintaining another adapter
or run state. It never connects or starts a run automatically. Open **Connection
& preview**, check the backend URL, then Connect and Start fresh run.

## Real model-only replay

Guttuu's backend landed on main in [PR #11](https://github.com/vinhbin/stutterturn/pull/11).
The integration below was verified against its handoff revision `3ed3786`. Follow its
[pinned setup instructions](https://github.com/vinhbin/stutterturn/blob/3ed3786/agent/README.md)
to install the Python environment and fetch the hash-checked models and local
SEP-28k recordings. No recordings or model weights are included in this site.

From this repository root, with the backend environment active:

```sh
python agent/server.py --services off --port 8765
```

Connect the console to `http://127.0.0.1:8765`. Stock and patient replay the same
chosen recording in separate runs. Patient uses the same model with a provisional
1.0 s silence wait, compared with stock's 0.2 s. A candidate stays unavailable
unless the backend supplies one.

**Services off means real local model decisions, without Gemini, ElevenLabs or
response audio.** This establishes neither audible playback nor benchmark
efficacy. The backend currently counts received PCM in services-on mode rather
than playing it. The page preserves reported timings and playback limitations.

## Synthetic interface check

The no-server development preview is explicitly labeled synthetic. To test the
real HTTP/WebSocket adapter against scripted fixtures alongside the real server:

```sh
python web/demo-ui/dev/mock-agent-server.py --port 8767
```

Set the console's backend URL to `http://127.0.0.1:8767`. Every fixture is labeled
mock, no audio and not evidence. Stock and patient use identical mock scripts.

## Evidence and review

- [Guttuu handoff review](handoff-2026-10-10.md): actual implementation, UI
  compatibility correction, validation and remaining acceptance.
- [Console reference](demo-ui/README.md), [design system](demo-ui/DESIGN.md) and
  [original UI verification](demo-ui/verification.md).
- [Site design extension](DESIGN.md) and [desktop/mobile captures](screenshots/).
- [Studio refresh checks](studio-verification.md), including the reproducible
  site, console, and adapter check commands. Earlier captures are historical.
- [Backend replay logs, v2](https://github.com/vinhbin/stutterturn/tree/9805a06/agent/evidence/2026-10-10-replay-v2)
  (supersede the first replay, whose model input lacked pre-roll): exploratory
  traces, with unreviewed boundaries and no efficacy claim.

The site can be served as static files. A deployed HTTPS page requires a separately
reachable HTTPS/WSS backend for real runs; a visitor's loopback URL does not
connect to the team's laptop. This change does not deploy the site or backend.
