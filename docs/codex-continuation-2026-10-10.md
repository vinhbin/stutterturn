# Codex continuation — October 10, 2026

Vinh asked Codex to continue after his Claude usage ran out. This increment builds
on merged main `73adb10`; it preserves the approved studio UI and the active
Guttuu/Niko model lane. [PLAN](../PLAN.md) remains the status authority.

## Completed and verified in this branch

- **Playback lifecycle:** reply generations prevent stale PCM from leaking into a
  later turn; barge-in no longer leaves the next reply permanently muted. Stop
  aborts caller/agent output even during pending inference. Fast TTS is paced
  through a 500 ms pending bound, and timeline exhaustion is explicit. Cut/end
  events use accepted sample limits, including partial or stalled responses.
  Timeout and cleanup failures remain visible. These are software guarantees
  checked with fake devices/providers, not acoustic acceptance.
- **Benchmark file integrity:** scoped LF checkout rules restore exact manifest
  hashes on Windows. The original check failed all three split hashes and the
  labels hash; it now passes, including fresh local checkouts with
  `core.autocrlf=true` and `false`. No data values or expected hashes changed.
  These are Windows-hosted checkout checks, not a claim of Linux execution.
- **Judge evidence integration:** the merged Tiger scaffold is embedded in the
  judge guide, matching the charcoal/cyan system. Ten current replay-v2 runs over
  five clips are shown; ten superseded runs are excluded. Data values match the
  original snapshot and committed JSONL. The chart distinguishes a local export
  from an export produced by database queries; neither badge claims live status.
- **Human review materials:** two proposed 15-row worksheets, five candidates per
  feasibility category in each, with exact source mappings and context links.
  Thirty sources are unique, disjoint and development-only. Human fields remain
  blank; no annotation outputs were created. Start at [the listening guide](labeling/README.md).

Validation: **26 offline playback/lifecycle tests**, Python compilation,
`build_splits.py --check`; Tiger ingest dry-run (20 logs, 302 events, 150 current
events); 38 adapter + 20 console browser + 52 site checks = **110 UI checks
passed**. Independent playback review cleared timing, cancellation and timeout
handling, including a separate held-provider stop probe. Four desktop/mobile
captures and independent review cleared the chart integration and packet. Tests
used synthetic services and local files only.

```powershell
python -m unittest discover -s agent/tests -v
python -m py_compile agent/engine.py agent/playback.py
python benchmark/scripts/build_splits.py --check
python web/tiger/ingest.py --dry-run
node web/demo-ui/dev/checks/adapter-checks.mjs
node web/demo-ui/dev/checks/browser-checks.mjs
node web/demo-ui/dev/checks/site-checks.mjs
```

## Next acceptance work

1. Vinh listens to A, then B, and publishes the actual annotation CSVs. A second
   human accepts the B cross-check. Worksheets and energy proxies do not pass
   this requirement.
2. Guttuu/Niko complete the bounded selection work and publish a candidate only
   if it passes. Guttuu now reports full v2 training and two prescreen survivors in
   `a8f9607`; his branch is at `a78f21b`. The final selection decision and
   artifact/hash handoff remain unpublished. V1 failed selection. Keep the
   corrected comparison ready and record
   the actual scope decision by the existing 20:00 EDT stop.
3. Guttuu's requested handoff is to listen locally and test audible output,
   stopping an active reply, cancellation and restart. Vinh is on remote desktop
   and cannot accept listening. The new [runtime packet](proofs/playback-runtime/README.md)
   records three runs at `42b86d0`: real-device source stop/restart and one real
   Gemini/ElevenLabs reply, with 29 characters under a 120-character cap. No
   timeout, late chunk or cleanup error was reported. The 6.01 ms source-stop
   observation is client request to terminal message, not acoustic latency.
   The temporary server closed; the older service on port 8765 was preserved.
4. Configure the Tiger Data connection locally, then separately verify real
   schema/ingestion/query behavior. No connection file was present during this
   continuation; offline verification does not establish database integration.
5. Review/merge the branch, deploy the accepted site revision, rehearse three
   times with reset under 60 seconds, and finish video/submission within the
   existing freeze and submission buffer. The hosted UI still predates PR #21
   at inspection (`/judges/` and `/demo-ui/` work; `/judge/` and `/live/` are 404).
   Windows HTTPS validation succeeds; the separate Python error was local trust
   chain selection. No merge, deployment, database write or human/acoustic
   acceptance was performed. The bounded real provider generation above happened
   after the initial offline-only increment.

The isolated execution worktree now also has its own ignored Python environment,
all three pinned model/VAD assets and ten source clips. All 26 deterministic
tests passed there, and whole-clip feature/probability parity passed on ten
sources × stock INT8/FP32 with zero difference. This is preprocessing parity,
not a completed model comparison. Niko's selector and LF fixture repair are at
`8f732d7`. Guttuu's `a8f9607` commit message reports V1?V4 training runs and
prescreen survivors `V3/ckpt-e0.51` and `V2/ckpt-e2.00`; head `a78f21b` also
incorporates main. These reports still need the selection/immutable artifact
handoff before the demo can use an accepted candidate.

Current status and links should be refreshed in PLAN as those outputs arrive;
this dated handoff records what was actually checked. PR #23 was merged at
`d8cdef4` while this follow-up was being prepared. PR #24 on
`codex/stutterturn-runtime-handoff` carries the new runtime evidence and README
updates, including Kareem's team/contribution credit. The README remains a
working status document; the final submission rewrite is still future work.
