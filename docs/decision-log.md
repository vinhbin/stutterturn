# StutterTurn decision log

Dated entries, newest first. Confirmed team choices vs. proposals are kept distinct. A result claim requires saved test evidence.

## 2026-10-10 D-012 — Continue the original goal with a bounded interpolation attempt

After W3 failed selection, Vinh rejected treating the stock/patient fallback as the final project scope and asked to continue earning the original claim. Following review of [Guttuu's proposal](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103360382) and the recommendation for bounded interpolation plus parallel human labels, he instructed Codex to respond to Guttuu. [The conditional go-ahead was posted at 19:42 EDT](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103422097).

It authorizes six blends only: the two W3 prescreen checkpoints, e2.00 and e1.00, with pinned stock FP32 parameters at alpha 0.25, 0.50 and 0.75. Keep the frozen selection data, thresholds 0.4/0.5/0.6 and every numerical constraint, including delta M5 >= 0 versus stock (no specificity regression). No new training or expanded grid. Guttuu executes after Niko signs off on the corrected implementation and frozen protocol. Before scores exist, record exact source/configuration/manifest hashes, a correctly described deterministic tie rule, and parity evidence; freeze the procedure for M3s/M3-crop promotion evaluation at the subsequently selected threshold.

The handoff sets **45 minutes from Niko-approved execution start, or 20:45 EDT on October 10, whichever comes first**. Record both timestamps before execution. This replaces D-011's no-v4 rule and 20:00 stop for this attempt only. No automatic v5 or additional sweep follows; report the result and failure analysis before a further decision. Stock/patient remains the backup; this experiment's stopping rule does not abandon the broader improvement goal.

Human A/B labeling proceeds in parallel with a named second-human B cross-check, not agent-generated labels. Supplement the feasibility set with human-reviewed unfinished fluent development examples; compare any eligible candidate with stock FP32, the stock threshold comparator and the patient baseline. Existing matched-input, response-delay, nonresponse and audible acceptance requirements remain. The B reviewer is not yet confirmed.

**D-009 stays in force: reserved final test sealed.** A development pass does not promote the model or establish the audible-interruption claim. Disclose a fourth adaptive attempt on reused development data and the overlap of human feasibility sources with development. This entry records authorization, not executor start, Niko signoff or a passing result.

## 2026-10-10 D-011 — Resume W3 only, keep the test sealed (approved by Vinh)

Historical W3 authorization. W3 subsequently failed selection; D-012 separately authorizes the bounded next attempt.

At approximately 19:00 EDT, Vinh explicitly approved the single W3 experiment with “ok do it” after the bounded recommendation. [Approval was posted on issue #2](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103109431), tagging Guttuu and Niko. This supersedes D-010's training pause and the earlier no-v3 rule for W3 only; **D-009's reserved-test seal is unchanged**.

Execute the [reconciled protocol](../model/specs/training-v3.md), merged in PR #28: stock FP32 initialization; frozen data-v2; 80% original replay / 10% SEP unfinished / 10% SEP completed proxies; learning rate 1e-5; seed 0; two weighted epochs; existing checkpoints and threshold grid. W1/W2/W4 and v4 remain excluded. Preflight, every selection constraint, and additional promotion checks remain mandatory. No final-test run or automatic demo promotion follows a development pass.

Guttuu owns execution and saved audio acceptance; Niko owns selection and the matched input comparison. Target prescreen at resume +20 minutes and full selection at resume +40 minutes, with the unchanged **20:00 EDT hard stop on October 10**. Failed inputs/checks or insufficient remaining time mean report the failure and retain stock/patient, not extend or relax the protocol. Record actual start, run/artifact identities, result, and limitations. **Approval is not evidence of a run starting, completing, or passing.** No start acknowledgment was available when this entry was prepared.

## 2026-10-10 D-010 — Training mixture preference and pause (confirmed by Vinh)

Historical pause; superseded for W3 only by D-011 above.

Vinh clarified that 80/20 means 80% original Smart Turn training examples and 20% stutter-focused adaptation examples, then explicitly said to wait. Subsequent requests ask for a v3 recommendation, a judge-facing training report, and a Git push so Guttuu can read them. Training remains paused; the report and push do not authorize a run. D-009 continues to keep the reserved final test sealed.

The [recommendation](v3-recommendation-2026-10-10.md) proposes W3 only (80% replay, 10% SEP unfinished, 10% SEP completed proxies), with unchanged selection constraints and additional promotion checks. It differs from Niko's proposed required W1/W2/W3 grid and needs a recorded amendment before execution. This entry records the user's preference and pause, not approval of that recommendation. The [training report](training-report-2026-10-10.md) records the failed v1/v2 outcomes and evidence limits.

## 2026-10-10 D-009 — Keep the reserved test untouched (confirmed by Vinh)

Vinh asked to keep the reserved test untouched for later testing. Do not run [Niko's proposed stock-only final comparison](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102597230) or inspect test outcomes. Preserve the frozen test items and hashes in [`benchmark/items/v1/manifest.json`](../benchmark/items/v1/manifest.json): `test.jsonl` SHA-256 `6bddc5b6b59ad2b929b0542828199d13c0130cd450b57394f7ac2488b6c26d32`, and `test_end_of_window.jsonl` SHA-256 `1cd7140f67bffbc30c315b6818b0464a54b8f024674bf2697de691798ab5c5fd`.

This reserves the test; it does not select a model or authorize more training. Vinh remains undecided about [Guttuu's v3 proposal](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102568699), so the existing no-v3 rule and 20:00 hard stop remain unchanged. Training v1 and v2 both returned `dev_nothing_passes`; no final scope choice is recorded by this entry.

## DRAFT — team decision not yet recorded — continue/fallback gate entry template (prepared 2026-10-10 evening)

**This is a prepared template, not a decision.** No gate is recorded as passed, missed or decided here. Vinh records the actual continue/fallback outcome with the team, per D-006/D-007; when recorded, this draft becomes a numbered entry with the fields below filled in.

Evidence available to the decision as of Saturday evening:

- [Replay v2](../agent/evidence/2026-10-10-replay-v2/README.md) (executed on `bcf50d1`, on main via [PR #14](https://github.com/vinhbin/stutterturn/pull/14); supersedes the first replay, whose model input lacked the pre-roll): 5 SEP-28k block clips × stock/patient, 10 logs. Stock decided "complete" inside the labelled gap in 4 of 5 clips; 3 of those replies were cancelled before any audio; the fourth clip was too short to observe overlap; patient made no early in-gap decision; no audible interruption in any run — reply delay, not demonstrated safety. Labels exploratory, energy-derived, not human-reviewed; 5 clips support no rates.
- Niko's training work is in progress on `niko/model-benchmark`; **no candidate artifact** (`stutterturn-vN.onnx`) or matched evaluation exists in the repository.
- To fill at decision time, per the PLAN recording rule: time · actual pass or miss · artifact and input IDs · limits · continue or fallback · recovery owner · next checkpoint.

## 2026-10-10 D-008 — Kareem's departure and lane transfer (confirmed by Vinh)

Kareem left the team on Saturday afternoon; Vinh confirmed the departure. No reason is recorded here. The lane transfers as follows: the landing page, judge view and evidence index had already been delivered via [PR #12](https://github.com/vinhbin/stutterturn/pull/12) and, together with root `README.md` upkeep and disclosures, are now maintained by Vinh's side. The B-batch label cross-check (F4's independence check) needs a new human reviewer — flagged for reassignment to Guttuu or Niko; that reassignment is a pending team decision, not made by this entry. The optional Tiger Data integration is unstaffed and likely cut; also a pending team decision. Gate criteria, evidence standards and the claims ledger are unchanged by this staffing update.

## 2026-10-10 D-007 — Apply evidence, ownership and integration workflow (requested by Vinh)

Vinh asked to apply the reviewed planning/Git practices to StutterTurn. Keep the accepted direction, strong intended pitch and existing 2 PM/3 PM proof gates. PLAN is the single task-status authority; phase issues link deliverables/evidence and remain open until their acceptance gates pass. Vinh coordinates integration; Guttuu verifies full audio behavior and Niko verifies model/evaluation artifacts.

The 1:10 PM EDT repository check found exploratory benchmark work on main `8161223`, UI scaffold PR #7 and pitch/evidence PR #8. No model/export, agent contract/run or human annotation handoff was yet published. This is repository evidence, not a claim about unpushed teammate work. The task table now distinguishes unreported work, scaffold implementation and real acceptance; it names exact annotation files, exclusive writers, consumers, gate evidence and recovery owners. Capture the first real complete run as the backup.

The README is aligned to observed capability and links the intended pitch. Its former confident model/novelty/audible-interruption wording is preserved in Git history and the pitch drafts, not presented as achieved behavior. PR #8's claim statuses require methodological review: copying old figures does not repair incorrect endpoint labels, censored latency, or model-decision versus audible-response distinctions. The claims ledger becomes the single claim-status authority once accepted. Numerical experiment artifacts are unchanged by this workflow update.

The earlier ~11 AM interpretation of 116/200 predictions as a banked interruption baseline, verified novelty and proof that settings cannot work is superseded by D-006's corrections. No implementation PR is merged or gate marked passed by this decision. Optional integrations and polish remain deferred; other independent lanes continue.

## 2026-10-10 D-006 — Bounded proof and earlier decisions (approved by Vinh)

Vinh approved adding the review's concrete tasks to the plan and GitHub issues: Niko proves the trainable-weight/one-batch/export path (45-minute checkpoint-recovery cap); Guttuu runs a complete web-agent baseline and patient/wait comparison; Vinh + Kareem human-check 30 examples across unfinished blocks, completed stuttered turns and completed fluent turns. The 30 examples are a feasibility set, not the final benchmark.

**2 PM EDT:** decide whether model work is feasible and the real agent exposes a meaningful remaining failure. **3 PM:** require development improvement without worse completion delay or nonresponse for either caller group; otherwise commit to a corrected benchmark/comparison scope. The earlier 10 PM model-abandon decision and telephony-first dependency are superseded. Final headline results require a separately frozen test and matched stock/candidate runs.

Review found that existing completion predictions do not establish audible interruption rates; short observation windows do not establish three-second fallback rates; and the fine-tuning checkpoint path remains unproved. D-002/D-003 below record earlier interpretations, **not currently validated conclusions**. Rebuild show-separated partitions, preserve original endpoint labels and prevent mixed-model caches before accepting comparisons.

Vinh explicitly wants to keep the strongest pitch draft. Strong claims can become deliverable wording after their evidence gates pass; this plan does not replace the pitch with a tentative research question. Preserve denominator/outcome distinctions, scope novelty carefully, and treat phone/sponsor/polish work as deferred rather than removed. Worktree agents may prepare Vinh's UI and pitch tasks using `docs/agent-handoff.md`; humans still verify audio labels and make scope decisions.

Approval here is for the planning/task handoff. It does not establish teammate agreement, successful experiments, commercial rights or completed implementation.

Vinh additionally requested that all four teammates work in parallel. The plan now gives each an exclusive write lane, splits listening into disjoint 15-sample batches, requires early model/event contract drafts, and permits frontend scaffolding while model/agent work proceeds. Only dependent training/integration and the gate decisions synchronize the lanes.

## 2026-10-10 D-005 — Repo created ahead of the noon confirmation (Vinh's instruction)

Private repo with planning, phases, roles and a submission-ready README, modeled on the team's previous hackathon repos. The team's noon pick is still the gate for build work; if the pick changes, this repo is archived, not deleted (the benchmark stands on its own).

## 2026-10-10 D-004 — Demo ethics and design (confirmed)

**Nobody imitates stuttering, ever.** The live demo streams real SEP-28k recordings (labeled on screen) into a genuinely live agent call; the agent's decisions happen live. The judge presses the STOCK↔STUTTERTURN toggle and separately speaks to the agent to feel the unchanged fluent latency. 3 minutes, ~2 judges, reset under 60 s, labeled fallback video if connectivity dies.

## 2026-10-10 D-003 — Novelty claim wording (verified)

Searches of ElevenLabs docs/changelog/site, Smart Turn repo and forks, LiveKit/Deepgram/AssemblyAI docs, academic work and Devpost found no stutter-aware turn-taking anywhere. Closest prior art: Apple's closed, Siri-only atypical-speech work (Lea et al. 2023). The claim therefore always includes **"open"** and **"public benchmark"**. ElevenLabs framing is credit, not attack: their stock agents handled short blocks well in our own n=20 live test (labeled as our measurement). Unknown and said so if asked: whether Smart Turn's community training data incidentally contains stuttered speech.

## 2026-10-10 D-002 — Kill test results accepted (evidence: benchmark/RESULTS.md)

Real SEP-28k audio, 200 block + 200 fluent clips. Stock Smart Turn v3.2: 58% block interruptions first-check / 68% repeated, ~0.1 s fluent latency; timeouts and thresholds cannot reach <10% interruptions without multi-second latency for everyone; ElevenLabs stock 5–10% on short blocks (n=20). All measured gaps <1.6 s (3 s clip censoring) — long blocks untested. SEP-28k annotations CC BY-NC 4.0 (benchmark/demo use with attribution; no commercial use; audio not redistributed). None of the pre-registered abandon conditions met.

## 2026-10-10 D-001 — Pivot from CarSweep; StutterTurn selected for the final test round

Friday night an iPhone auto-detected the team's own Bluetooth tracker, confirming phones + free apps already do CarSweep's core job. After researched comparison rounds across all tracks, StutterTurn emerged as the lead: a measured failure in the open voice-agent stack, a named measurable advance, and a self-produced before/after stat. Fallbacks if its gates fail: CrossingClock, then StepLimit (see the team brief).
