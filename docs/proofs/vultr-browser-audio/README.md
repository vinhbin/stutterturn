# Vultr browser audio verification — October 11, 2026

Application revision **667460f45fdd** is deployed to the existing Vultr instance.
The same authenticated WebSocket now delivers source and generated speech to
Web Audio. No new server or GPU was provisioned; keys remain server-side.

## Observed results

- `browser-audio-check.json`: Chromium rendered real source and ElevenLabs reply
  audio from stock FP32 run `20261011T052044Z-stock_fp32-43a0` and exploratory X1
  run `20261011T052053Z-candidate-7d76`. Both completed with no reported provider
  timeouts, no skipped late samples, and no pending browser buffers at completion.
- Measured digital peak amplitudes: source/reply approximately **0.934/0.568**
  for stock and **0.926/0.659** for candidate. Both mixed outputs were nonzero.
  These are audio-graph measurements, not a microphone or human listening test.
- Stopping generated speech in run `20261011T052102Z-candidate-d1d4` left zero
  queued nodes and zero measured mixed output after 300 ms. Resetting a restarted
  10.4-second source also left zero nodes and zero output. No uncaught page errors.
- Synthetic PCM rendered in Chromium's OfflineAudioContext confirms that a
  generation cancellation cuts the reply while preserving the source; Stop
  silences both. This is a lifecycle test, not natural-interruption evidence.
- `hosted-boundary-check.json`: valid HTTPS, public landing/guide, authenticated
  console/script/API, no public environment or source-WAV endpoint. Service active,
  zero restarts, about 276 MiB cgroup memory at the final check.
- `linux-tests.txt`: 40 backend tests passed on Vultr; the same 40 passed locally.
  Eight audio lifecycle, 38 adapter, 20 console, and 52 site checks passed locally.

The earlier two successful browser runs at 05:19 UTC are also retained as JSONL.
The next run, `20261011T051928Z-candidate-5033`, hit Gemini's ten-second timeout and
produced no reply audio. That failed active-reply-stop attempt is retained. The
subsequent full browser check passed. These few runs do not establish reliability.

## Scope and reproduction

Run `python web/demo-ui/dev/checks/audio-browser-check.py` for the synthetic
render check. Add `--access-file PRIVATE_JSON --out OUTPUT_DIR` for real hosted
provider calls. The access file is private and is not included. See the check
script for its schema. The screenshot shows the console after the Reset check.

Both complete runs used `HeStutters_4_32.wav`, an existing three-second
training-show demonstration clip. The longer clip was used only for reset/restart.
PCM is transported to the authenticated run owner and is absent from these logs
and the public static bundle. Provider response text is preserved in the logs.

Audio events use a **server sample schedule**, with a browser buffer of 250 ms
from source receipt. Network and device latency are separate. Human listening,
acoustic stop/flush timing, natural resumption during an already audible reply,
and non-Chromium browser coverage remain unverified by this packet. X1 remains
post-hoc exploratory and unpromoted. The historical Tiger Data chart has not
ingested these runs; this packet is not a benchmark or efficacy result.
