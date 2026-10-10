# StutterTurn plan and coordination

**Team:** Vinh · Guttuu · Niko · Kareem · **Repo:** https://github.com/vinhbin/stutterturn

**Deadlines:** feature freeze Sun 1:00 AM · video + Devpost 1:00–8:00 AM · submit by 8:30 AM (official 9:00 AM EDT). Judging: 3 minutes, ~2 judges at the table.

**One outcome:** a judge presses STOCK ↔ STUTTERTURN while a real recorded caller plays into a live agent call, hears the interruption disappear, then talks to the agent themselves and feels no added delay — with the measured table (58% → X%) on the benchmark page behind it.

## Status snapshots

### 2026-10-10 ~11 AM — Repo created; baseline banked; pick pending

- The benchmark ran overnight on real SEP-28k recordings: stock Smart Turn v3.2 interrupts 58% (first check) / 68% (repeated) of 200 stutter blocks; no timeout/threshold fixes it within acceptable latency; ElevenLabs stock handled short blocks well (5–10%, n=20). Full numbers: `benchmark/RESULTS.md`. ✅ with evidence.
- Novelty verified this morning: no stutter-aware turn-taking anywhere (ElevenLabs docs/changelog, Smart Turn repo/forks, LiveKit/Deepgram/AssemblyAI, papers, Devpost). Closest prior art is Apple's closed Siri work. Our claim keeps the words **open** and **public benchmark**.
- **The team confirms the pick at noon.** Tasks below are assigned, not claimed. A kill-test fallback chain exists in the team brief (CrossingClock / StepLimit).

Add future dated snapshots above this line; keep history.

## Roles and boundaries

| Owner | Responsibility | Owned paths | Hands off |
|---|---|---|---|
| **Niko** | Listen-through, fine-tune, two-axis eval, long-block test, the benchmark | `model/`, `benchmark/` | Model file + eval numbers to everyone |
| **Guttuu** | Telephony + Pipecat agent, phone-path audio test, demo rig hardware | `agent/` | A callable number running any given model |
| **Kareem** | Judges page (live-run buttons), Tiger Data results store, disclosures/README upkeep | `web/` | Public-facing claims checked against saved results |
| **Vinh** | Demo UI (toggle + turn-state display), pitch, rehearsals, video, Devpost | `web/demo-ui`, `docs/submission.md` | The 3-minute run; final submission |

One owner per path. Model interface and benchmark schema change only by agreement with Niko (`CONTRACT:` commit prefix). Nobody — ever — imitates stuttering; only real recordings, always labeled.

## Phases and gates

Legend: ⬜ assigned · 🟡 in progress · ✅ proved with evidence · ⛔ blocked · ✂️ cut

| # | Phase (time EDT) | Owner(s) | Exit gate | Status |
|---|---|---|---|---|
| 0 | **Confirm + listen-through** (12:00–12:30) | All; Niko listens | Team pick confirmed; ~30 clips human-checked as real blocks. **No training before this passes.** | ⬜ |
| 1 | **Fine-tune v1 + plumbing** (12:30–3 PM) | Niko; Guttuu number+agent; Vinh UI skeleton; Kareem page skeleton | **3 PM:** fine-tune beats stock on blocks with fluent latency unchanged (both axes, same eval) | ⬜ |
| 2 | **Live integration + long blocks** (3–7 PM) | Guttuu+Niko; Kareem Tiger pipeline | **7 PM:** live call runs our model end to end; long-block set evaluated; Gemini arm run if key obtained | ⬜ |
| 3 | **Demo engineering** (7–10 PM) | Vinh leads; all | Toggle rig works; turn-state display live; reset <60 s; 3 rehearsals with someone unscripted. **10 PM ABORT GATE:** fine-tune still not beating stock → ship benchmark page + stock "patient" agent, honestly labeled. No heroics. | ⬜ |
| 4 | **Judges page + freeze** (10 PM–1 AM) | Kareem; all | Every public claim is a button backed by saved results; README current; **1 AM freeze** | ⬜ |
| 5 | **Video + submit** (1–8:30 AM) | Vinh; Kareem checks | 3–4 h protected for video/Devpost; links checked logged-out; received confirmation by 8:30 | ⬜ |

**Rest and meals (not optional — the demo is judged on evening work):** each person takes one protected 90-minute sleep block between 3 and 10 PM, scheduled at the 3 PM gate. Suggested: Vinh + Kareem 3:00–4:30 (their Phase 1 deliverables land by 3), Guttuu 4:30–6:00 (after integration handoff), Niko 6:00–7:30 if eval is green (the critical path sleeps last, but DOES sleep — a fried Niko at the 10 PM abort gate is how bad calls get made). Real dinner together ~6:30. Vinh has been up since Friday: his 3:00 block is mandatory.

**Build order notes:** Phase 0 is the unblocker (bad labels poison everything). Phase 1's fine-tune is the critical path — Niko gets help before anyone polishes. Phase 2 is the convergence point (model meets telephony); the 10 PM abort gate exists because the benchmark-page fallback is still a submittable project. Phase 5 adds nothing new.

## Shared contracts

| Boundary | Owner | Definition |
|---|---|---|
| Model interface | Niko | Same input/output as stock Smart Turn v3.2 (drop-in); model files named `stutterturn-v{N}.onnx`, never overwritten |
| Eval output schema | Niko | `benchmark/data/*.csv` columns stay stable; every eval run reports BOTH axes |
| Turn-event stream | Guttuu → Kareem/Vinh | JSON events: `{t, state: speaking|silence|holding|agent, prob, model}` over websocket |
| Public claims | Kareem | Nothing on the page or in the pitch without a saved result behind it |

## Open questions

| Question | Owner | Needed by |
|---|---|---|
| Noon pick confirmed by all four? | Vinh | 12:00 |
| Gemini API key (agent brain + rival arm) | anyone | Phase 1 |
| NSA Atlanta outreach for one real user's voice — yes/no | team | afternoon |
| Kareem's GitHub handle (repo access) | Vinh | now |
| 8 kHz phone-path behavior | Guttuu | Phase 2 |
| License choice before publication | team | Phase 5 |

## Pre-submit checklist

- [ ] Repo public; README accurate; license chosen; links checked logged-out.
- [ ] Every number in README/pitch matches `benchmark/` saved results; ElevenLabs n=20 labeled as our own measurement.
- [ ] Demo video (3 min) shows the real rig; recordings labeled; no imitated stuttering anywhere.
- [ ] Disclosures: pre-event planning, AI assistance (benchmark + code), dataset licenses (SEP-28k CC BY-NC, audio not redistributed), Smart Turn BSD-2.
- [ ] Never-say list respected: no "all voice agents fail", no medical claims, no "solved stuttering".
- [ ] Devpost: AI/ML track + MLH Best Use of ElevenLabs; received confirmation before 9:00 AM.
