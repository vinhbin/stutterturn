# Vultr backend — October 11, 2026

The existing Vultr instance now runs the replay backend as well as the public
presentation site. Deployed application revision: `667460f45fdd` (browser audio increment).

## Open it

1. Open <https://64-177-51-1.sslip.io/live/> and sign in with the demo credentials
   supplied separately. Credentials are not stored in the repository.
2. The hosted console connects automatically and loads recordings/models. If it fails, use **Retry connection**; the error appears beside it. Backend URL and manual controls are under **Advanced settings**.
3. Select a source and configuration, then **Start fresh run**. Only one replay
   can run at a time on this 1-CPU / 1-GB instance.

The landing page and judge guide stay public. The console, HTTP API and WebSocket
require HTTPS Basic Authentication. The Python listener binds only to 127.0.0.1.

## What actually runs on Vultr

- Silero VAD and ONNX Runtime inference, including stock INT8, stock FP32 and the
  privately staged X1 exploratory candidate.
- Gemini requests using captured source audio, then ElevenLabs streaming TTS.
- Run logging and the HTTP/WebSocket event service.
- Caddy HTTPS and the presentation site.

**Browser audio is enabled.** The service runs with `--browser-audio`; the browser
requests PCM on its authenticated WebSocket and uses Web Audio to play the source
recording and generated reply. Click Start to unlock sound. Volume, Stop, and
Reset control playback; caller resumption cancels the corresponding reply.
Generated reply text appears in the console; the source has no verified transcript.

The player buffers 250 ms from source receipt. Logged audio times are server
sample schedules, not measured acoustic output. Chromium checks measured nonzero
digital source/reply output. Hosting and playback do not establish interruption
rates, unchanged response latency, or candidate promotion. See the new
[browser audio verification packet](proofs/vultr-browser-audio/README.md).

Two real API smoke runs completed with provider replies and no reported timeouts,
one stock FP32 and one candidate, on the same three-second training-show clip.
These are deployment checks, not efficacy evaluation. See the
[saved verification packet](proofs/vultr-backend/README.md).

## Service and files

| Item | Location |
|---|---|
| Service | `stutterturn-agent.service` |
| Active source | `/opt/stutterturn/current` → `releases/667460f45fdd` |
| Environment / provider keys | `/opt/stutterturn/shared/agent.env` (mode 600) |
| Private model files / audio | `/opt/stutterturn/shared/models`, `shared/audio` |
| Saved server logs | `/opt/stutterturn/shared/runs` |
| Python environment | `/opt/stutterturn/venv` |
| Public files | `/var/www/stutterturn` |
| HTTPS configuration | `/etc/caddy/Caddyfile` |
| Prior static-site configuration | `/opt/stutterturn/backups/cad4d50fa292/` |

The service runs as the unprivileged `stutterturn` user. systemd restarts it on
failure and starts it on boot. Filesystem writes are restricted to `shared/`.
Concurrent replays are capped at one; foreign browser WebSocket origins and
unlisted source names are rejected. Caddy removes the upstream wildcard CORS
headers and does not forward the demo password to the Python backend.

`ELEVENLABS_MAX_CHARS=3000` is a **per-process** character cap; restarting resets it.
It is not a persistent account budget or a cap on Gemini spend. Login protection
limits who can initiate paid runs. API keys remain server-side. The candidate is
post-hoc exploratory, not promoted; its checksum and threshold are logged per run.

## Operations

Run through SSH on the existing instance:

```sh
systemctl status stutterturn-agent
journalctl -u stutterturn-agent -n 50 --no-pager
curl --fail http://127.0.0.1:8765/v0/health
systemctl restart stutterturn-agent
```

Templates live in [`deploy/vultr`](../deploy/vultr/). Caddy 2.6 uses `basicauth`;
newer Caddy versions call the directive `basic_auth`. Validate before reloading.
To redeploy: archive the intended Git revision, extract into a new private release
directory, link the shared models/audio/runs, set `STUTTERTURN_REVISION` to that
exact archive revision, switch `current`, restart and verify the service. Transfer
credentials securely outside the source archive; never place them in the web root.

To roll back to the prior static-only deployment:

```sh
cp /opt/stutterturn/backups/cad4d50fa292/Caddyfile /etc/caddy/Caddyfile
cp /opt/stutterturn/backups/cad4d50fa292/app.js /var/www/stutterturn/demo-ui/app.js
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl reload caddy
systemctl disable --now stutterturn-agent
```

## Submission wording

“Vultr hosts our public site and runs our Python voice-agent backend, including
ONNX turn-model inference, Gemini response requests, ElevenLabs speech generation,
and the HTTPS/WebSocket API used by our comparison console. The hosted console
shows live decision and response-generation events and plays the source recording
and generated speech in the browser through an authenticated audio transport.”

The older judge-page snapshot remains a historical replay packet; these deployment
runs have not been ingested into its Tiger Data chart.

## Roll back just the browser audio increment

The prior event-only release is retained. Its static files and service unit are
backed up under `/opt/stutterturn/backups/667460f45fdd/`. Restore that unit, the
saved `demo-ui/` and `live/` files, point `current` to `releases/cad4d50fa292`, and
set the existing env file's `STUTTERTURN_REVISION` back to `cad4d50fa292`.
Then run `systemctl daemon-reload` and `systemctl restart stutterturn-agent`.
Keep the existing credentials and provider keys. The older static-only rollback
above disables the backend entirely and is a different operation.
