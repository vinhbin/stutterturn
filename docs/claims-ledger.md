# StutterTurn claims ledger

Owner: Vinh (pitch builder lane). Last updated: Sat 2026-10-10 afternoon, before the 2 PM gate outcome was recorded.

Every result-bearing, novelty, implementation or compatibility sentence we might say — at the table, on the page, in the video, on Devpost — has an entry here. **Anything delivered today uses the entry's READY wording only.** Target wording becomes deliverable the moment its listed evidence exists, and not before.

**Statuses**

- **ready** — deliverable today exactly as worded; saved evidence at the cited path; the required caveats are part of the wording itself.
- **target** — intended final wording; blocked until the listed evidence lands. Until then use the paired ready wording or say nothing.
- **unsupported** — do not deliver in any form; contradicted, on the never-say list, or no evidence path exists.

**Standing interpretation rule (D-006, [PLAN.md](../PLAN.md)):** all 2026-10-10 kill-test numbers are **exploratory**: the eval partition spans all eight SEP-28k shows (show-separated rebuild pending), gap/resume labels are energy-VAD-derived (human listen-through pending), and the measurements are the model's **internal completion predictions**, not observed audible interruptions, call abandonment or hang-ups. Automated waveform inspection does not count as human listening. If the evaluation is rebuilt, stock is rerun; the old 58% is not the comparator for any new number.

---

## A. Our measurements — exploratory kill test (run date 2026-10-10)

### L-01 — Stock first-check rate ("the 58%")

- **Ready wording:** "On 200 real recordings of people who stutter — clips Apple's annotators labeled as stutter blocks — the standard open turn-taking model, Smart Turn v3.2, predicted 'turn complete' during 58% of the silent gaps on its first check, the moment production agents consult it. That's the model's internal decision; we are validating the audible outcome in a live pipeline, and our own listen-through of the clips, today."
- **Target wording:** "The standard open model interrupted [S]% of stutter blocks" — where [S]% is stock on the frozen, show-separated final test, with audible interruption measured through the deployed pipeline.
- **Metric / population:** 58.0% "complete" predictions (N=200; the 116/200 count is stated in [PLAN.md](../PLAN.md)'s historical status, consistent with RESULTS.md's 58.0%) at p > 0.5 on first check, 0.2 s into the silent gap. Population: SEP-28k clips with ≥2/3 annotator Block votes, quality-gated, energy-VAD gap ≥ 300 ms with detected resume; all gaps 0.30–1.59 s; wideband 16 kHz podcast audio; Smart Turn v3.2 int8 CPU with the repo's own preprocessing.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §5; `benchmark/data/model_block_results.csv`; exploratory all-eight-show partition.
- **Status:** ready (ready wording) · target (interruption wording)
- **To upgrade:** (1) human listen-through / 30-example feasibility labels (issue #1, Vinh + Kareem + Niko); (2) Guttuu's pipeline timestamps showing whether a premature decision becomes an audible interruption; (3) Niko's show-separated partition rebuild + stock rerun. **Never** translate into callers interrupted, hang-ups or abandonment. 58% of tested blocks is not 58% of callers.

### L-02 — Stock any-check rate (68%)

- **Ready wording:** "Checked repeatedly during the gap — what a streaming agent actually does — the prediction rate rises to 68%."
- **Metric / population:** 68.0% "complete" on any check before the labeled resume (N=200); same population as L-01.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §5; `benchmark/data/model_block_results.csv`.
- **Status:** ready (as completion predictions, exploratory) · same upgrade path as L-01.

### L-03 — Fluent latency axis of stock

- **Ready wording:** "For fluent callers stock adds a median 0.10 s on the 77 clips with measurable trailing silence (p90 0.40 s) — but 26% of fluent turns were never judged complete and fell to the 3-second fallback timeout. We report that nonresponse rate; we don't hide it in an average."
- **Metric / population:** median added latency 0.10 s, p90 0.40 s, on the N=77 fluent latency subset (clips with ≥ 0.5 s trailing silence out of 200 fluent clips); 26% fallback-timeout rate; 100 ms measurement checkpoints.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §3, §5; `benchmark/data/model_fluent_latency.csv`, `benchmark/data/model_fluent_full_curves.json`.
- **Status:** ready (as worded, exploratory). The pitch line "one tenth of a second" may be used only with the fallback-rate caveat available in Q&A.
- **To upgrade:** finer-than-100 ms timing (needed before any ±50 ms comparison); rebuilt partition rerun.

### L-04 — Stock on fluent speakers' own mid-utterance pauses

- **Ready wording:** "Stock also predicted 'complete' at 59.6% of fluent speakers' own mid-utterance pauses in our exploratory run — on conversational audio it endpoints most sub-second pauses, stuttered or not. Many such pauses do follow complete sentences; our human listen-through has to split those before we lean on this number."
- **Metric / population:** 59.6% of 57 testable pauses (≥ 300 ms with resume) across 51 fluent clips, checked at +0.2–0.3 s of silence.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §5; `benchmark/data/model_fluent_pause_results.csv`.
- **Status:** ready (with the listen-through caveat spoken).

### L-05 — Silence-timeout arms

- **Ready wording:** "A silence timeout trades one failure for another in our data: 0.8 s still expires inside 20% of the measured block gaps and adds 0.8 s for every caller on every turn; 1.5 s expires inside almost none of our short-block gaps but adds 1.5 s for everyone. And every gap we could measure was under 1.6 s — so for real multi-second blocks these timeout numbers are lower bounds."
- **Metric / population:** timeout-expiry-during-gap rates on the N=200 block gap-duration distribution: 0.5 s → 61.5%, 0.8 s → 20.0%, 1.5 s → 0.5%, 3.0 s → 0.0% (censored at 1.59 s max gap).
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §4–5; `benchmark/data/eval_tallies.json`, `benchmark/data/block_eval.csv`.
- **Status:** ready (censoring caveat is mandatory, not optional).

### L-06 — Confidence-threshold arms

- **Ready wording:** "Raising the model's confidence bar isn't even an exposed knob — it needs a fork — and it fails anyway: at 0.95 it still predicts 'complete' in 22.5% of block gaps while sending 48% of fluent turns to the 3-second fallback; at 0.99 it stops predicting on blocks only because it nearly stops firing at all — 98.7% of fluent turns fall to the fallback, which is a 3-second timeout for everyone."
- **Metric / population:** threshold 0.9 → 35.5% first / 48.5% any, 40% fluent fallback; 0.95 → 22.5% / 37.0%, 48% fallback; 0.99 → 0.0%, 98.7% fallback. Same populations as L-01/L-03.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §5; `benchmark/data/threshold_sweep.json`.
- **Status:** ready (exploratory).

### L-07 — "No setting fixes it" (aggregate)

- **Ready wording:** "None of the configurations **we tested** — silence timeouts at 0.5/0.8/1.5/3 s, Smart Turn confidence thresholds 0.9/0.95/0.99, and ElevenLabs' patient mode in our own small live test — kept block completion-predictions under 10% without multi-second delay or nonresponse for other callers. That's the configurations we tested, on short blocks, not every possible setting or system."
- **Unsupported wording:** "No existing knob fixes it" / "no setting fixes it" stated universally.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §5, §7, §10.
- **Status:** ready (narrowed form only) · unsupported (universal form)
- **To upgrade:** nothing upgrades the universal form; it stays narrowed. Matched baseline comparisons on the rebuilt partition let us drop "exploratory."

### L-08 — ElevenLabs stock (normal) arm

- **Ready wording:** "In **our own small live test — 20 clips, unpublished, our measurement** — an agent we built on ElevenLabs' platform, stock settings, barged in on 1 of 20 blocks strictly scored (2 of 20 on a looser score). Their closed platform already handles short blocks well, and we credit that. All tested gaps were 0.5–0.96 s; what it does on a real 3–10 s block is unknown."
- **Metric / population:** 1/20 strict (5%), 2/20 likely (10%); N=20 live ConvAI sessions, block clips with gap ≥ 0.5 s, `turn_eagerness=normal`; 95% CI on 1/20 is roughly 0.1–25%.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §7; `benchmark/data/elevenlabs_normal_results.csv`; agent `agent_9901m4k3jsfyehcry084sqnk3vyv`; `benchmark/scripts/elevenlabs_arm.py`.
- **Status:** ready (n=20/unpublished/own-measurement labels are mandatory).

### L-09 — ElevenLabs patient arm

- **Ready wording:** "Their 'patient' setting barged in on 1 of 20 in the same test — but 6 of 20 sessions got no response at all inside our ~6-second window, and the response-time proxy ran about +3.0 s. Patience costs responsiveness there too. The proxy includes ASR, LLM and TTS time, so it is not a clean end-of-speech latency."
- **Metric / population:** 1/20 strict and likely (5%); 6/20 no response in ~6 s window; mean first-agent-event +2.99 s (proxy); same 20 clips, `turn_eagerness=patient`.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §7; `benchmark/data/elevenlabs_patient_results.csv`.
- **Status:** ready (same mandatory labels as L-08).
- **To upgrade:** Niko's planned fluent-latency arm (stream the 77 fluent clips normal vs patient) isolates the patient latency cost from LLM/TTS.

### L-10 — Harness sanity controls

- **Ready wording:** "Three controls order correctly: audio cut mid-word — which should read 'not done' — drew a 'done' prediction 31% of the time; genuine sentence ends, 70%; stutter blocks, 58%. The ordering mid-speech < block < true-end says the harness measures real signal — and that the model treats a block far more like 'done' than like mid-speech."
- **Metric / population:** 31% (N=49 mid-speech cuts), 70% (N=50 true ends + 0.4 s silence), 58% (N=200 blocks).
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §5; `benchmark/scripts/sanity_controls.py`.
- **Status:** ready. Say "order correctly," not "prove the harness is correct."

### L-11 — Stock inference cost

- **Ready wording:** "Stock Smart Turn costs about 25 ms per inference on CPU in our runs (mean 25 ms, p95 28 ms, n=1,164) — an 8M-parameter model."
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §5 (timing); model size per [README.md](../README.md) / the Smart Turn repo.
- **Status:** ready (stock only — candidate cost is L-24).

### L-12 — Spot-check of eval structure

- **Ready wording:** "Automated RMS spot-checks of 10 eval clips all show the expected speech → gap → resumption structure. That's waveform inspection, not human listening — the team listen-through is running today and nothing graduates past exploratory until it's done."
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §6; `benchmark/data/spotcheck/block_spotcheck_rms.png`.
- **Status:** ready (only with the "not human listening" clause).
- **Unsupported wording:** "we listened to the clips" / "human-verified labels" — until issue #1's annotation sheet exists.

### L-13 — Gap durations and censoring

- **Ready wording:** "Every block gap we could measure was under 1.6 seconds, because the dataset's clips are 3 seconds long — median gap 0.58 s. Real blocks can last many seconds. That regime is untested for every system, including ours, including the commercial ones."
- **Metric / population:** N=200 gaps; median 0.58 s, p90 0.93 s, max 1.59 s; 79 further block clips excluded as right-censored.
- **Source / run:** [benchmark/RESULTS.md](../benchmark/RESULTS.md) §4; `benchmark/data/eval_tallies.json`.
- **Status:** ready — and **mandatory** alongside any timeout or ElevenLabs number.

## B. External sources (not our measurements — attribute, never blend with ours)

### L-14 — 160,000 patient calls a month

- **Ready wording:** "One health system reports its AI agent handles 160,000+ patient calls a month."
- **Source:** WellSpan announcement, Jul 2026 — linked in [README.md](../README.md) (The problem). One health system; not an industry total — do not multiply or generalize.
- **Status:** ready.

### L-15 — Prevalence

- **Ready wording:** "More than three million Americans stutter — about 1%."
- **Source:** NIDCD quick statistics — linked in [README.md](../README.md).
- **Status:** ready.

### L-16 — Survey: people who stutter report this

- **Ready wording:** "In a 2026 survey of 53 people who stutter, 58% report interrupted or timed-out voice input; Apple's own study of 61 people who stutter found they're 'frequently cut off, misunderstood.'"
- **Source:** Liu et al., ASSETS 2026; Lea et al. 2023 — both linked in [README.md](../README.md).
- **Status:** ready. **Caution:** this 58% is a coincidence with our exploratory 58% (L-01). Never present them adjacent without naming each denominator, or a judge will think we laundered one number into two findings.

### L-17 — Apple / Siri prior art

- **Ready wording:** "Apple's published work cut Siri's premature cut-offs by roughly 79% — shipped as Siri-only accessibility settings, model closed. Nothing comparable exists in the open agent stack."
- **Source:** Lea et al. 2023 (arXiv, linked in README); Siri accessibility settings page.
- **Status:** ready ("nothing comparable exists" is scoped by our documented search, L-26/L-27 — say "we searched and found none," not "none exists anywhere").

### L-18 — "0.2 s is the production default" / Smart Turn is the open-stack default

- **Ready wording:** "Pipecat consults the turn model when its VAD reports 0.2 s of silence (default `stop_secs` 0.2) — that's the first-check moment we test. Smart Turn is the pipecat ecosystem's standard open turn model."
- **Source:** pipecat defaults recorded in [benchmark/RESULTS.md](../benchmark/RESULTS.md) §5; Smart Turn repo (BSD-2) linked in README.
- **Status:** ready.

### L-19 — "Pharmacy refill lines are among the most automated calls in the country"

- **Status:** **unsupported** — no source saved anywhere in the repo.
- **To upgrade:** a citable source; otherwise cut the clause from every script (the WellSpan number carries the hook alone).

## C. Candidate / fine-tune claims — all placeholders until Niko's immutable evidence

No `stutterturn-vN.onnx` exists in the repo as of this writing. Every entry below is **target**; the placeholder text is what the docs carry today.

### L-20 — Headline improvement

- **Placeholder:** "[X]% — pending Niko's immutable `stutterturn-vN.onnx` eval (run ID, model hash, data-manifest hash, config, per [PLAN.md](../PLAN.md) evaluation contract)."
- **Target wording:** "Block completion-predictions drop from [S]% to [X]% on the frozen, show-separated final test" — [S]% is the stock **rerun** on that same final test; the exploratory 58% is not the comparator.
- **Status:** target.
- **Evidence needed:** 3 PM DEV gate pass; frozen final-test manifest; one pre-registered final run of stock and candidate; human-validated labels in the test set.

### L-21 — "Same speed for fluent callers / unchanged latency"

- **Placeholder:** "[fluent and stuttered completed-turn medians each within +50 ms of stock — pending final-test run at fine timing resolution]."
- **Status:** target. The 100 ms checkpoints of the exploratory run **cannot** establish ±50 ms; Niko must measure finer.
- **Evidence needed:** per-group (completed fluent AND completed stuttered) medians + tail latency + fallback/no-response rates, stock vs candidate, same run records.

### L-22 — No worse fallback / nonresponse

- **Placeholder:** "[fallback-timeout and no-response rates no worse than stock for each caller group — pending same run]."
- **Status:** target. Also required: human-validated unfinished **fluent** pauses must not regress (new interruptions of fluent callers fail the gate).

### L-23 — "Drop-in: loads anywhere stock Smart Turn does"

- **Status:** target.
- **Evidence needed:** Niko's export→reload→output-comparison evidence (issue #2) **plus** the candidate actually loading and running in Guttuu's pipeline. `model/CONTRACT.md` (not yet created) must mark compatibility verified, not proposed.

### L-24 — Candidate inference cost ("no slower than stock")

- **Status:** target (same architecture makes it expected, not shown).
- **Evidence needed:** timed inference on the exported candidate ONNX, same machine/method as L-11.

### L-25 — Training-data description ("fine-tuned on real recordings of people who stutter, ~50/50 mix")

- **Status:** target.
- **Evidence needed:** actual usable training counts after exclusions, frozen train manifest, recorded mix ratio. Until then say "the training recipe we're running is…" only as plan, in present/future tense.

## D. Novelty claims — narrow, sourced, search-scoped

### L-26 — "First open stutter-trained turn-taking model"

- **Ready wording (today):** "To our knowledge no open turn-taking model trained on stuttered speech exists — we searched ElevenLabs docs/changelog, the Smart Turn repo and its public fine-tunes, LiveKit/Deepgram/AssemblyAI docs, papers and hackathon galleries, and documented it ([decision log D-003](decision-log.md)). We're building the first one we know of."
- **Target wording:** "StutterTurn is, to our knowledge, the first **open** turn-taking model trained on stuttered speech" — only once the model exists (L-20 evidence).
- **Status:** target (model must exist) · the search-scoped absence statement is ready.
- **Never:** "first ever," unscoped; a search finding nothing is not proof of universal absence.

### L-27 — "First public benchmark of voice-agent turn-taking on stuttered speech"

- **Ready wording (today):** "We found no public benchmark of how voice-agent turn-taking treats stuttered speech (search documented, D-003). We built one this weekend and will publish it."
- **Target wording:** "…the first **public** benchmark…" — only once the repo/benchmark is actually public with the corrected method (show-separated splits, validated labels) and license/permissions resolved (issue #5).
- **Status:** target (publication + corrected method pending) · search-scoped version ready.

### L-28 — "Apple fixed this inside Siri and kept it closed; we take Apple's dataset where Apple stopped"

- **Ready wording:** as written, with "fixed" scoped: "Apple's published work cut Siri's cut-offs ~79%, shipped as Siri-only settings; no open model was released. We use Apple's own dataset — SEP-28k — where Apple stopped."
- **Status:** ready (rhetoric is fine; the factual load sits on L-17, which is sourced).

### L-29 — "It didn't exist before this weekend"

- **Status:** unsupported as an absolute. Use L-27's search-scoped form.

## E. Demo and implementation claims

### L-30 — Live-demo claims ("decisions happen live," "judge presses the toggle," fresh call per press, reset < 60 s)

- **Status:** target — no demo rig exists yet (issue #4, 7–10 PM). Until the rig runs: these sentences are run-of-show **plans**, not descriptions.
- **Evidence needed:** Guttuu's working agent + toggle rig; saved endpoint/resume/cancellation/TTS timestamps from the actual demo recording; verified one-tap reset; fresh-session-per-toggle confirmed. If only the internal decision differs audibly, present the trace accurately — do not stage an audible interruption.
- **Mandatory disclosures whenever delivered:** the caller is a **real recording** of a person who stutters (SEP-28k), labeled on screen; nobody imitates stuttering; any connectivity-failure video is **labeled as a recording** of the same rig.

### L-31 — "Judge talks to the agent and nothing got slower"

- **Ready form:** the judge's call establishes **liveness** only.
- **Status:** the latency claim itself is target (L-21) — one interaction does not establish unchanged responsiveness for every caller; cite measured completed-turn results or say "feel the speed; the measured number is on the page."

### L-32 — "Live phone agent" / telephony

- **Status:** unsupported today — current scope is a **web** voice agent; telephony is deferred until after the proof (PLAN), and 8 kHz narrowband behavior is untested (L-37). Say "live voice agent" / "web agent," not "phone agent," until Guttuu lands a tested phone path.

### L-33 — "Reproducible from benchmark/"

- **Ready wording:** "Scripts, eval CSVs and results are saved in [benchmark/](../benchmark/) with the method in RESULTS.md."
- **Status:** ready (as "saved and documented") · target (as "reproducible end-to-end"): `benchmark/requirements.txt` referenced by the README **does not exist yet**, and a pinned environment + one-command rerun is not verified. Evidence request to Niko below.

### L-34 — Sponsor-usage claims (Gemini, Vultr, Tiger Data)

- **Status:** target/unsupported today. Gemini Live arm **not run** (no API key — RESULTS §8); Vultr training/hosting **not built**; Tiger Data time series **not built**. ElevenLabs is the only sponsor integration with saved evidence (L-08/L-09).
- **Rule:** enter and list only prizes backed by actual, disclosed use at submission time. README's sponsor table currently reads as present-tense ("doing real work") — flagged to Kareem/Vinh; README is outside this lane's write scope.

## F. Scope limits — must-say list (all ready; deliver proactively)

| ID | Limit | Source |
|---|---|---|
| L-35 | Long blocks (3+ s) untested **everywhere, including by us** — all measured gaps < 1.6 s | RESULTS §4 censoring caveat |
| L-36 | English-only, blocks-only: other languages and other disfluency types (repetitions, prolongations, interjections) untested; model card must say "English fine-tune — use stock for other languages" | RESULTS; Q&A |
| L-37 | Wideband 16 kHz audio only; 8 kHz narrowband phone channel untested | RESULTS §9 |
| L-38 | SEP-28k annotations CC BY-NC 4.0: research/demo with attribution; weights (if released) research + non-commercial; never "fully open" without the qualifier; no commercial deployment promise | RESULTS §1 |
| L-39 | No one on the team stutters; nobody imitates stuttering, ever; real recordings only, labeled; research prototype, not a medical or therapeutic tool; it makes the agent wait — it does not recognize stuttered words better | README, D-004 |

## G. Never-say list (hard rules — no upgrade path)

- "All voice agents fail" (contradicted by our own L-08).
- Any medical, diagnostic or therapeutic claim. "We solved stuttering."
- The 58% as **callers interrupted**, **call abandonment**, or **hang-ups** — it is exploratory internal completion predictions on tested blocks. 58% of tested blocks ≠ 58% of callers.
- "We rehearsed it" before rehearsals happen; "we listened to the clips" before the listen-through is logged.
- Any target, plan or placeholder voiced in past tense as an achieved result.
- First-person or community testimony we don't have; invented consent.
- Multilingual support; long-block performance (anyone's); "fully open" weights.

---

## Evidence requests

### To Niko (model, evaluation)

1. **Immutable candidate artifact + run records:** `stutterturn-vN.onnx` (never overwritten), with run ID, model hash, data-manifest hash, config, counts, per-group premature decisions, median/tail delay, fallback/nonresponse and censoring — per the PLAN evaluation contract. Unblocks L-20–L-25.
2. **Show-separated train/DEV/final-test manifests** + **stock rerun** on the new final test. Unblocks the [S]%→[X]% comparison; without it no stock-vs-candidate sentence is quotable.
3. **Human listen-through log** (10 spot-check clips + HeStutters_21_144 + feasibility-set share) and the 30-example annotation sheet status from issue #1. Upgrades L-01/L-02/L-12 from "exploratory" and unblocks "validated" language.
4. **Fine timing resolution** (better than 100 ms) for completed-turn delay, both groups. Required before any ±50 ms sentence (L-21).
5. **`benchmark/requirements.txt` + pinned env + one verified rerun command** (README already points at it; it doesn't exist). Unblocks L-33's "reproducible" wording.
6. **Candidate inference timing** on the exported ONNX (L-24).
7. **Gemini Live arm**: run it (needs GOOGLE_API_KEY) or confirm we strike every "Gemini benchmarked as a rival" phrase from submitted text (L-34).
8. **`model/CONTRACT.md`** with proposed vs verified compatibility marked (L-23).

### To Guttuu (agent, audio path)

1. **Per-run audio-path timestamps** from the complete web agent: run ID, time origin, endpoint decision, speech resume, cancellation, first audible response, timeout/no-response — stock and the patient/wait configuration, same pipeline, same recordings. Unblocks any "audible interruption" sentence (L-01 upgrade) and the fallback demo numbers.
2. **Does a premature model decision become an audible interruption** on the replayed real recordings? Yes/no with saved trace. This is the single highest-leverage piece of evidence for the hook.
3. **Exact patient/timeout configuration identity** (e.g., "stock + 1.5 s silence timeout" vs an eagerness setting) so the fallback demo's on-screen label is precise.
4. **Phone-path status:** web-only or telephony attempted? If telephony, narrowband (8 kHz) test results — until then every doc says web audio and L-32/L-37 stand.
5. **`agent/CONTRACT.md`** version + run-control/event schema, and demo-rig facts when they exist: fresh session per toggle, one-tap reset time (L-30).

### Flagged for Vinh's personal judgment

1. **Two lines in the preserved pitch draft have no upgrade path:** "Many just hang up." and the 10-second version's "Voice agents hang up on people who stutter." Recommendation: replace even in the final pitch with the survey-backed L-16 wording. Your call — the draft is preserved untouched either way.
2. **The 58/58 coincidence** (our exploratory 58% vs the survey's 58% of 53 respondents): decide whether both appear in one pitch; if so, each needs its denominator spoken (L-16 caution).
3. **"Pharmacy refill lines…" (L-19):** source it or cut it.
4. **README sponsor table vs build status** (L-34): present-tense sponsor claims with nothing built — coordinate with Kareem before submission.
5. **Whether the exploratory 58% headlines the public benchmark page** before the partition rebuild and listen-through land, or the page waits for rebuilt numbers.
6. **Rehearsal:** both scripts are length-estimated only (word count ÷ ~150 wpm). Nobody has rehearsed; issue #4 requires three rehearsals with an unscripted participant before 10 PM.
