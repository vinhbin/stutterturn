# Vultr replay-backend deployment proof

Recorded October 11, 2026 (EDT), application revision `cad4d50fa292`.
Existing Vultr Ubuntu 24.04 instance, 1 CPU / 1 GB RAM, no GPU or new instance.

## Evidence

- `verification.json`: authenticated HTTPS discovery, rejected unauthenticated
  controls, rejected foreign WebSocket origin, single-run admission, and two real
  provider-enabled replay summaries.
- `20261011T044851Z-stock_fp32-8df2.jsonl` and
  `20261011T044902Z-candidate-d48b.jsonl`: complete WebSocket records, checked for
  equality against each server-side HTTP run log.
- `browser-check.json` and `hosted-console.png`: Chromium interaction through the
  deployed `/live/` page and its console iframe, using HTTPS with certificate
  verification and demo authentication.
- `linux-tests.txt`: all 30 backend tests passed on the deployment host.
- `requirements-lock.txt`: actual installed server dependencies.

Both API smoke runs used `HeStutters_4_32.wav`, a three-second real recording from
a **training show**, followed by the agent's normal five seconds of silence.
Each completed, received generated speech PCM and reported no timeouts or
nonresponse. The candidate finished via the configured fallback in this run.
The four measured model calls took 175.8–213.0 ms on this server; this small
deployment check establishes no response-latency or general performance claim.

The headless service has playback **off**. Audio-start events have
`timing.basis=pcm_receipt`. No loudspeaker or browser audio was tested or delivered.
The log's `audible_interruption=false` must not be interpreted as an acoustic
finding. Candidate loading and provider execution do not establish model efficacy.

X1 remains the post-hoc exploratory candidate chosen after v4 results (fifth
adaptive look at reused development/guard data), not a v4 pass or promoted release.

No source audio, model weights, passwords or provider keys are in this packet.
The run endpoint, console and WebSocket are authentication-protected; the project
site and judge guide remain public. Private asset URL probes returned 404.

See [deployment and rollback instructions](../../vultr-backend.md).
