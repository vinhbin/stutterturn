# Current-code playback runtime checks

**Code:** `42b86d0` (clean agent tree), contract `0.1`, additive timing
`playback-v1`. These are engineering acceptance checks on one source, not a
stock/patient comparison or a trained-model result. [Manifest](manifest.json)
pins the source, model, dependency versions and raw LF log hashes.
This packet lives under `docs/proofs/` so the Tiger importer does not mix these
engineering checks into its five-clip comparison population.

| Run suffix | Configuration | Providers | Result |
|---|---|---|---|
| `211955Z-stock-9b74` | stock | off | Source playback stopped; terminal message received 6.01 ms after the client sent Stop |
| `211958Z-patient-812f` | patient | off | Fresh run on the same WebSocket completed; generated-audio fields remain null |
| `212006Z-patient-9716` | patient | on | Gemini reply and ElevenLabs output completed; 29 characters used under a 120-character session cap |

The source is `HeStutters_4_32.wav` (3 seconds, plus the engine's 5 seconds of
synthetic trailing silence). Patient completion was **fallback_timeout at
4.992 seconds**, after a negative model decision, not a positive model result.
Its reply occupied scheduled output positions 7.844–9.562 seconds. No source
recording or generated audio is redistributed here. The generated reply text
in the log was reviewed for publication.

The temporary localhost server used the unmodified `agent/server.py` handlers.
Checks covered matching `/v0/health` revision, source/configuration availability,
consecutive sequence numbers, one run identity and terminal record, expected
completion reason, absence of reported timeout/device errors, and record
equality after JSON parsing between streamed messages and the HTTP log. It closed afterward;
the older background service on port 8765 was not restarted.

The selected output was **Speakers (HyperX QuadCast S)** through Windows MME:
16 kHz mono, 256-sample blocks, reported output latency 0.096 seconds. A preceding
digital-silence probe advanced its callback position, aborted and closed in
5.7 ms, stayed at the same position after 100 ms, and opened a fresh device
stream successfully. These measurements describe software/API observations.

**Human listening is pending.** Vinh was on remote desktop and could not hear
the output; he requested a handoff to Guttuu. No microphone/loopback capture
established acoustic start, stop, flush or interruption timing. The stop run
ended 0.3 seconds after its start acknowledgment, before a model decision or
generated reply; it does not validate stopping an active reply. The current
code also lacks callback underrun/status telemetry. Zero reported late chunks
or cleanup errors does not prove glitch-free physical playback.

## Guttuu's acceptance handoff

Use PR #23's `codex/stutterturn-execution` branch in an isolated worktree. Keep
training work intact. Engine/playback code is the same as tested `42b86d0`;
later evidence/document commits do not upgrade any runtime claim. Confirm
`GET /v0/health` names your checked-out revision before capturing new evidence.
Keep keys in the ignored `agent/.env`; do not send them in the issue or logs.

```powershell
python -m venv agent/.venv
.\agent\.venv\Scripts\Activate.ps1
python -m pip install -r agent/requirements.txt
python agent/fetch_assets.py 5
python -m unittest discover -s agent/tests -v
python agent/check_features.py
python agent/run.py --config patient --source HeStutters_4_32.wav --services off --play
$env:ELEVENLABS_MAX_CHARS = '120'
python agent/server.py --services on --play --port 8766
```

Use Python 3.11 for the new environment (the recorded version is 3.11.16).
If this worktree already has its own environment, activate it instead of
recreating it. On Linux/macOS, activate with `source agent/.venv/bin/activate`
and set the cap with `export ELEVENLABS_MAX_CHARS=120`.

In a second terminal at the same worktree root:

```powershell
python -m http.server 8044 --bind 127.0.0.1 --directory web
```

Open `http://127.0.0.1:8044/live/`, set Backend URL to
`http://127.0.0.1:8766`, and connect. Replaying beyond the provider character cap
intentionally returns a visible cap error; do not raise it silently.

1. Confirm the intended output device and that both the real source and a
   generated reply are clearly heard. The browser controls playback on the
   backend machine; it does not transport audio to remote desktop.
2. Stop during source playback, then during an active generated reply. Confirm
   audible output stops and no old audio returns after reset/restart. Save
   separate fresh run IDs for each attempt; do not edit these frozen logs.
3. Exercise cancellation when a permitted source naturally resumes after a
   decision; ensure a later legitimate reply can play. Do not imitate stuttering.
   If the provider is too slow to exercise audible cancellation, report that
   case as untested rather than claiming a pass.
4. Return revision, device/API, settings, run IDs, what was actually heard,
   pass/fail for each case, and remaining limits in issue #3. Any numeric acoustic
   latency claim needs a stated loopback/recording method and uncertainty.

Separately, this worktree's own Python environment passed all 26 deterministic
tests and whole-clip preprocessing/probability parity on 10 sources × INT8/FP32
(maximum differences both zero). Whole-clip parity is not runtime turn-slice
parity, and neither check establishes model improvement.
