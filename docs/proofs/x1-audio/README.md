# X1 candidate: audio acceptance runbook (promotion check c)

**Candidate:** `stutterturn-x1-blend-a0.75-W3e1.00-th0.60`: post-hoc exploratory candidate selected after v4 results; not a v4 pass; fifth adaptive look at dev/guard ([X1 result](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104584978)). **Not promoted.** This checks playback mechanics with the candidate loaded. It is **not** evidence that the model is better, and it does not replace human endpoints on the frozen confirmation set (promotion check d).

Anyone on the team can run it on their own machine.

## What you need
- An isolated checkout of `main` (don't use your training or labeling worktree) with `agent/.venv` (Python 3.11) and your own ignored `agent/.env`. **Never paste keys anywhere.**
- **The model file:** `stutterturn-x1-blend-a0.75-W3e1.00-th0.60.onnx`, 32,065,795 bytes, sha256 `d1a503fee1eca1e6d6ffe78e918d8ed312922eddb5f3dd19cc5315c1b824c025`. Weights are not in git; ask Guttuu for the file through the team's private channel. It is the X1 export, byte-identical, and the agent refuses any file whose sha256 differs.
- **The metadata** next to it, with the same base name: [`stutterturn-x1-blend-a0.75-W3e1.00-th0.60.json`](stutterturn-x1-blend-a0.75-W3e1.00-th0.60.json) from this folder. It is **derived** from the X1 export metadata (sha256 `aaa5db8e…75af2`). The only change is `threshold` 0.5 → **0.6**, the threshold X1 was decided at, because the agent reads its threshold from this file. The model sha256 inside is unchanged.

## Setup
```powershell
# in the isolated checkout
$env:CANDIDATE_MODEL = "C:/path/to/stutterturn-x1-blend-a0.75-W3e1.00-th0.60.onnx"
cd agent
.venv\Scripts\python.exe -m unittest discover -s tests        # expect 27 OK
.venv\Scripts\python.exe -c "import engine; print([(c['id'], c['available'], c['params']['threshold']) for c in engine.configurations()])"
# expect ('candidate', True, 0.6)
$env:ELEVENLABS_MAX_CHARS = "120"
.venv\Scripts\python.exe server.py --services on --play --port 8766
```
Check `GET /v0/health` shows your checkout's commit. Open the console (`/live/`) against `http://127.0.0.1:8766`, live mode. Listen on the backend machine's speakers.

## Sources: rules
- The agent's bundled sources are **HeStutters** clips, a **training show**: the candidate may have seen them. Use them for **mechanics only**. Never describe "the candidate waited on this clip" as a model result.
- Extra clips may come only from the already-exposed `benchmark/items/v1` dev items.
- **Never** use any key in `benchmark/confirm/v1/` (PR #38). Those must not meet a model before their labels are frozen.

## Checklist (candidate first, then `stock_fp32`, then `patient`, same sources)
Record for each case: commit, device/API, configuration, run ID, what you heard, and **pass / fail / untested**.
1. **Source and generated reply** both clearly heard on the intended device.
2. **Stop during source:** audible output stops, and nothing old returns after Reset or a fresh run.
3. **Stop during an active reply:** same as 2.
4. **Cancellation before audio:** the speaker resumes after a decision, the pending reply is cancelled, and a later valid reply still plays.
5. **Audible cancellation:** the agent is mid-reply when the source resumes. Mark it **untested** if provider latency can't put a reply in flight before resumption (as on #3).
6. **Reply content:** the revised prompt (PR #27) shouldn't comment on how the caller speaks. Note any reply that does.
7. **Timing (report, don't judge):** log `first_turn_complete_t`, trigger (smart_turn vs fallback), `first_agent_audio_t`, timeouts and nonresponses per run. Acoustic latency is unmeasured unless you do a loopback recording; say so.

## Report
Post on issue #2, as promotion check (c) for X1:
- the commit, `/v0/health` output, Python, output device, `ELEVENLABS_MAX_CHARS`;
- the candidate sha256, and that `params.threshold` = 0.6 in the run logs;
- the table of cases with run IDs and pass / fail / untested.

Keep raw run logs (`agent/runs/`) and attach or push them. Use the mandatory X1 wording, and no improvement claims.
