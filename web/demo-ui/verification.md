# UI verification — October 10, 2026

This report covers the console and **synthetic contract fixtures**. It does not
pass F2/I1, validate speech labels, establish efficacy or prove audible output.

## Phase A — contract and lifecycle

The Node adapter suite was observed failing before implementation. Its final
29 checks then passed, including discovery, async acknowledgement, unavailable
candidate, source/configuration mismatch, sequence/version errors, timeouts,
stop/reset, stale callbacks and persistent mock attribution.

Run through Node's built-in test runner. The harness is retained in the local
handoff scratch directory, alongside the Playwright checks; test tooling is not
part of the repository. The only committed test helper is the development mock.

The Python development mock was also exercised through actual HTTP discovery and
WebSocket transport using Node's native client. All five scenarios completed:
overlap, held, cancelled, timeout and no-response. Every message was explicitly
mock-tagged, sequence numbers were contiguous, and named terminal outcomes were
checked. No audio, speech service or model was involved.

Browser verification on the functional phase passed **103/103 checks**:
24 smoke/keyboard/responsive checks, 21 lifecycle/race regressions and 58 actual
HTTP/WebSocket fixture checks. There were no uncaught browser JavaScript errors.
The transport checks covered all five scenarios, stock/patient fixture parity,
metadata/summary attribution, unavailable candidate, stop-to-start reconnection,
active disconnect, explicit reconnect and an absent server.

An independent code review found a legacy nameless-preview metric fallback;
it was removed and the reviewer confirmed the correction. All timing summaries
now require `turn_complete` and `agent_audio_start` by name, in every mode.
The lifecycle suite was rerun after that correction. Phase A is commit `4f2b24b`.

Two browser-harness adjustments were needed: expand the metadata details before
checking visibility, and test reconnection after Stop closes the socket instead
of clicking an appropriately disabled Disconnect button. These were test setup
corrections; product expectations were retained.

The resumed tests adapt the previously accepted smoke/regression scenarios and
add the new transport path. They do not merely repeat the old fixed event counts;
the preview now exercises the larger named vocabulary.

## Phase B — console and event timeline

The console uses local Archivo and JetBrains Mono fonts, a persistent state tally,
shared caller/agent event time, decision flags, holding spans and reported overlap.
It renders received events, not a waveform or an audio player. Terminal event time
freezes; an unreported endpoint remains dashed. An overlap total in a summary
never supplies an invented location on the timeline.

An independent review of desktop and mobile idle/holding/overlap captures found
undersized labels, an unclear mobile scroll affordance, and an overlap edge case.
The latter was reproduced before correction: overlap at 2.4, caller speech-stop
at 2.7 and agent audio-end at 3.0 incorrectly drew 0.60 s. The corrected interval
ends at the explicit caller boundary and measures 0.30 s. The reported summary
remains a separate backend value.

The final pass also retains probabilities on decision flags, amber holding
intervals, the active configuration near the tally, and synthetic-specific
holding copy. Mock state changes are not model output.

Final frozen implementation: **29/29 Node adapter checks and 142/142 browser
checks passed**, with zero uncaught JavaScript errors. Browser breakdown: 24 smoke,
21 lifecycle, 58 HTTP/WebSocket, 35 timeline/visual-behavior and 4 targeted overlap
regression checks. Coverage includes unknown versus explicit endpoints, holding
boundaries, supplied/missing probabilities, active run configuration, native
Left/Right scrolling to the mobile timeline endpoint, overflow-only hints,
responsive containment, keyboard focus, reduced motion, both local fonts and no
external page requests. No harness expectations changed after the final freeze.

Screenshots were inspected in one initial batch and one confirmation batch at
1280 × 900 and 390 × 844. The independent reviewer cleared the final code and all
eight refreshed renders with no remaining blocking findings. These images show
**synthetic fixtures only: no audio, no model output, no benchmark evidence**.

| State | Desktop | Mobile |
|---|---|---|
| Disconnected / idle | [Screenshot](screenshots/desktop-idle.png) | [Screenshot](screenshots/mobile-idle.png) |
| Synthetic holding | [Screenshot](screenshots/desktop-holding.png) | [Screenshot](screenshots/mobile-holding.png) |
| Synthetic overlap / completed run | [Screenshot](screenshots/desktop-overlap.png) | [Screenshot](screenshots/mobile-overlap.png) |
| Overlap, first viewport | [Screenshot](screenshots/desktop-first-viewport.png) | [Screenshot](screenshots/mobile-first-viewport.png) |

The standard overlap fixture in these captures has a 0.60 s interval. The separate
earlier-caller-stop regression has a 0.30 s interval; neither is an audio result.
Page content fits phone width; the timeline and event ledger scroll internally
to preserve readable labels and shared time coordinates.

## Real integration handoff

Inspected producer revision: `origin/guttuu/web-agent` at `a229787`. It contains
`engine.py` and `run.py`, but no `server.py` or saved accepted replay. The contract
is still proposed. The UI can target that interface without claiming it exists
as a running service.

Producer items to resolve before real acceptance:

- Supply HTTP discovery, WebSocket run control, CORS and allowed local sources.
- Clarify response playback: current engine onset records PCM receipt, not sound.
  The UI calls these backend-reported timings with playback unverified.
- Preserve version/run/sequence identity, source offset and model/config metadata.
- Clarify the contract's 20 ms frames versus engine 32 ms frames and publish the
  implemented patient settings. The page displays supplied parameters.
- Supply candidate artifact/provenance before enabling it. Services-off runs must
  remain distinguishable from a complete response pipeline.
- Verify stop/reset/reconnection on the real service, then replay matched real
  sources and save the complete interaction evidence separately.

## Scope

All implementation and development helpers remain under `web/demo-ui/`. No
teammate backend, model, benchmark, judges-page or root manifest is changed.
Fonts include their redistribution licenses and source hashes. Fixtures exercise
the same sequence for every arm and must never appear in an efficacy comparison.
