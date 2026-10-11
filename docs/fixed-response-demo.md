# Controlled response timing

The hosted console can run the actual turn models while replacing Gemini and
ElevenLabs calls with identical prerecorded assistant speech for every model.
It removes variable provider response time from this demonstration.

```sh
python agent/server.py --services fixed --fixed-response agent/assets/fixed-reply.wav --fixed-delay 1.0 --browser-audio --port 8765 --max-runs 1
```

The one-second wait starts after the model decision is processed; inference,
transport and the browser buffer still add time. It is a controlled response
delay, not a guarantee of identical wall-clock playback. Resumed speech still
cancels pending/active replies with the same rules for Stock and X1. The
recording, model weights, thresholds and silence gates remain unchanged.

The console displays **CONTROLLED RESPONSE TIMING** before and during runs.
The logs identify `services: fixed`, response mode, audio hash and delay.
Fixed waits are recorded as `fixed_wait_s`, not Gemini latency. No API keys
are required for reply generation and no provider quota is consumed.

For judging: "The turn models are running live on a recording. Both use the
same prerecorded response with a one-second simulated delay, so we can
compare turn decisions without variable API latency."

Existing judge-page snapshots are historical live-API runs and do not change
when this mode is enabled. Controlled results must stay separate from those
snapshots. This is not a real-world interruption-rate evaluation.

To restore the provider path, start the server with `--services on` and its
private provider environment. Do not describe a fixed-mode run as a live
Gemini/ElevenLabs response.
