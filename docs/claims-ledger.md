# StutterTurn claims ledger

Owner: Vinh (pitch builder lane). Last updated: 2026-10-10, evidence-readiness review. No gate outcome is asserted by this update.

Every result-bearing, novelty, implementation or compatibility sentence we might say — at the table, on the page, in the video, on Devpost — has an entry here. **Anything delivered today uses the entry's READY wording only.** Target wording becomes deliverable the moment its listed evidence exists, and not before.

**Statuses**

- **ready** — deliverable today exactly as worded; saved evidence at the cited path; the required caveats are part of the wording itself.
- **target** — intended final wording; blocked until the listed evidence lands. Until then use the paired ready wording or say nothing.
- **unsupported** — do not deliver in any form; contradicted, on the never-say list, or no evidence path exists.

**Standing interpretation rule (D-006, [PLAN.md](../PLAN.md)):** all 2026-10-10 kill-test numbers are **exploratory**: the eval partition spans all eight SEP-28k shows (show-separated rebuild pending), gap/resume labels are energy-VAD-derived (human listen-through pending), the Smart Turn results are **offline completion predictions**, and the ElevenLabs results are separately defined server-event timings. Neither establishes human-validated audible interruption rates, call abandonment or hang-ups. Automated waveform inspection does not count as human listening. If the evaluation is rebuilt, stock is rerun; the old 58% is not the comparator for any new number.

---

## A. Our measurements — exploratory kill test (run date 2026-10-10)

### L-01 — Stock first-check rate ("the 58%")

- **Ready wording:** "In an offline check of 200 SEP-28k clips labeled as containing blocks, Smart Turn v3.2 predicted 'turn complete' in 116 of the energy-detected gaps, or 58%, at our first checkpoint. The exact gaps and speaker continuation still need human validation; this is not an audible-interruption rate."
- **Target wording:** "Stock interrupted [S]% of validated unfinished blocks" — only with measured audible outcomes on the frozen final test.
- **Metric / population:** 116/200 at p > 0.5, checked 0.2 s after the detected gap starts; selected 16 kHz podcast clips, with detected gaps 0.30–1.59 s. Clip-level Block votes do not locate the block or identify who resumes.
- **Source / run:** `benchmark/data/model_block_results.csv`, `benchmark/data/block_eval.csv`, [run_model_arm.py](../benchmark/scripts/run_model_arm.py). [RESULTS.md](../benchmark/RESULTS.md) is the historical interpretation, not independent validation.
- **Status:** ready for the offline observation; target for validated block or audible-interruption claims.
- **To upgrade:** validate every evaluated boundary and speaker with context; rebuild/freeze partitions and rerun stock; measure decisions and audible outcomes through the same deployed pipeline. The 30-example feasibility set alone cannot validate the old 200-clip result.

### L-02 — Stock any-check rate (68%)

- **Ready wording:** "On the same clips, 136 of 200, or 68%, crossed the threshold at least once on our repeated offline checkpoint schedule. That schedule has not been shown to reproduce a deployed agent."
- **Metric / population:** checkpoints +0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2 and 1.5 s, stopping before detected resumption; same population as L-01.
- **Source / run:** `benchmark/data/model_block_results.csv`; [run_model_arm.py](../benchmark/scripts/run_model_arm.py).
- **Status:** ready as an offline statistic; unsupported as "what a streaming agent actually does."
- **To upgrade:** record the deployed VAD/endpoint configuration and actual check events, including cancellation and speech-resumption handling.

### L-03 — Fluent checkpoint results, not deployed latency

- **Ready wording:** "Of 77 selected clips without labeled stuttered words and with at least half a second of detected trailing silence, 57 crossed the threshold in the tested window. Among those 57, the median first crossing was 0.10 s and p90 0.40 s after the last detected speech. The other 20 were censored; we did not observe their eventual response or timeout."
- **Metric / population:** 57/77 crossings; 20/77 (26.0%) without a crossing before the clip's available silence or +1.0 s, whichever came first. The quantiles exclude those 20. All 77 clips are from HeStutters. The last energy activity is not a verified conversational turn end.
- **Source / run:** `benchmark/data/model_fluent_latency.csv`, `benchmark/data/model_fluent_full_curves.json`, `benchmark/data/fluent_eval.csv`; [run_model_arm.py](../benchmark/scripts/run_model_arm.py).
- **Status:** ready only as this conditional offline statistic. A 26% fallback/nonresponse rate and "stock answers in one tenth of a second" are unsupported.
- **To upgrade:** human-verified completed turns, representative frozen partitions, the same causal check schedule for each group, fine timing resolution, and observation through the deployed timeout or explicit right censoring. Fluent checks currently start at +0.1 s while block checks start at +0.2 s; this is not a matched runtime-latency comparison.

### L-04 — Predictions during gaps in fluent-labeled clips

- **Ready wording:** "The model crossed the threshold in 34 of 57 tested gaps in clips labeled without stuttered words. Those gaps have not been established as unfinished turns; some may follow completed sentences."
- **Metric / population:** 34/57 (59.6%) checkpoint predictions across 51 clips; this is not a verified fluent-interruption rate.
- **Source / run:** `benchmark/data/model_fluent_pause_results.csv`; [run_model_arm.py](../benchmark/scripts/run_model_arm.py).
- **Status:** ready as an offline observation; human-validated continuation labels and matched runtime checks are required for regression claims.

### L-05 — Calculated silence-timeout arms

- **Ready wording:** "Forty of the 200 detected gaps exceed 0.8 s, and one exceeds 1.5 s. A simple timeout measured from those gap starts would expire inside those gaps. That is a duration calculation, not a live-agent interruption measurement."
- **Metric / population:** gaps longer than 0.5/0.8/1.5/3.0 s: 61.5%/20.0%/0.5%/0.0%. A pure timeout waits its configured duration after its detected silence onset; actual endpoint and response delays depend on the deployed pipeline.
- **Source / run:** `benchmark/data/block_eval.csv`; [build_eval_sets.py](../benchmark/scripts/build_eval_sets.py).
- **Status:** ready as a calculated baseline. These selected short gaps do not establish a real-world lower bound or latency for every caller.
- **To upgrade:** validated boundaries, longer real samples and a matched deployed timeout arm.

### L-06 — Confidence-threshold sweep

- **Ready wording:** "At threshold 0.95, 45 of 200 first checkpoints crossed the threshold; 37 of 77 fluent-labeled clips had no crossing in the tested window. At 0.99, no tested block checkpoint crossed, and 76 of 77 fluent-labeled clips had no crossing in-window. What happened after that window was not measured."
- **Metric / population:** threshold 0.9: 35.5% first / 48.5% any, 31/77 censored; 0.95: 22.5% / 37.0%, 37/77 censored; 0.99: 0% / 0%, 76/77 censored. The fluent window ends at available silence or +1.0 s, not the deployed timeout.
- **Source / run:** `benchmark/data/threshold_sweep.json`, `benchmark/data/model_fluent_full_curves.json`; [threshold_sweep.py](../benchmark/scripts/threshold_sweep.py).
- **Status:** ready as a sweep of saved probabilities. "The model stops firing," a measured three-second fallback rate, and whether changing thresholds requires a fork of a particular runtime remain unsupported here.
- **To upgrade:** pin the deployed model/runtime/configuration; observe validated completed turns through its timeout, retaining censoring explicitly. Recompute with model-specific caches and matched schedules.

### L-07 — "No setting fixes it" (aggregate)

- **Ready wording:** "We saved exploratory timeout and threshold comparisons. They do not yet establish which configurations meet both our interruption and response-delay targets."
- **Target wording:** "None of the configurations we tested met both targets on this evaluation" — name those configurations, populations, metrics and uncertainty, if a matched evaluation supports it.
- **Unsupported wording:** "No existing knob fixes it," "the fix has to be in the model," or treating the current experiment as a completed rejection of existing settings.
- **Source / run:** L-01–L-06 and L-08–L-10; the limitations supersede the verdict in [RESULTS.md](../benchmark/RESULTS.md) §10.
- **Status:** ready for the limitation statement; target for the scoped comparison conclusion; unsupported as a universal claim.
- **To upgrade:** the same validated inputs and causal pipeline, completed turns from both groups, real delay/fallback observations, and the simple patient/wait baseline. The ElevenLabs proxy is a different outcome from model-only completion predictions.

### L-08 — ElevenLabs normal arm

- **Ready wording:** "In our 20-session normal-mode test, the first agent audio/response event arrived before detected resumption in one session; two met our looser timing rule. These are event-timing results against inferred boundaries, not human-validated audible interruption rates."
- **Metric / population:** 1/20 strict and 2/20 likely under the script's rules; detected gaps 0.5–0.96 s. Three sessions had no response event in the observation window. Text and audio events are both accepted as the first event.
- **Source / run:** `benchmark/data/elevenlabs_normal_results.csv`; [elevenlabs_arm.py](../benchmark/scripts/elevenlabs_arm.py).
- **Status:** ready with the event definition and small-sample limitation; no best-in-class or general commercial-platform conclusion.
- **To upgrade:** validated same-speaker boundaries, audible-response timing and matched completed-turn tests. Our result does not measure anyone's longer-block performance.

### L-09 — ElevenLabs patient arm

- **Ready wording:** "In patient mode, one of the same 20 sessions met the script's strict timing rule, and six had no response event in-window. The reported mean after-clip response proxy was 2.99 s versus 2.71 s for normal, calculated on different responding subsets; it does not isolate the setting's latency cost."
- **Metric / population:** 1/20 strict and likely; 6/20 no event in-window. Means use first events after the three-second clip ends, include ASR/LLM/TTS effects, and exclude nonresponders and earlier events.
- **Source / run:** `benchmark/data/elevenlabs_patient_results.csv`, `benchmark/data/elevenlabs_normal_results.csv`; [elevenlabs_arm.py](../benchmark/scripts/elevenlabs_arm.py).
- **Status:** ready as descriptive event statistics, not a proven fluent-latency penalty.
- **To upgrade:** matched verified completed turns, paired/repeated conditions, explicit censoring and endpoint/audio timestamps. Holding the rest of the pipeline constant reduces confounding; it does not subtract stochastic LLM/TTS time automatically.

### L-10 — Unvalidated sanity controls

- **Ready wording:** "The historical report gives 31% completion at cuts chosen half a second before the last detected speech, and 70% at cuts 0.4 s after it. These cutpoints were not checked as mid-word speech or genuine turn endings, so the ordering does not validate the labels."
- **Metric / population:** reported 31% of 49 early cuts and 70% of 50 late cuts. Raw per-control predictions are not saved. Example: `HeStutters_0_17.wav` is cut at 2.5 s, inside its saved detected pause [2.17, 2.9].
- **Source / run:** [sanity_controls.py](../benchmark/scripts/sanity_controls.py), `benchmark/data/fluent_eval.csv`; historical [RESULTS.md](../benchmark/RESULTS.md) §5.
- **Status:** ready to describe the reported control attempt and defect; unsupported as a validated semantic control or evidence against label noise.
- **To upgrade:** select and human-check truly active-speech cuts and genuine completed turns; save per-example predictions and labels.

### L-11 — Reported stock inference cost

- **Ready wording:** "The original run report records about 25 ms mean CPU inference time, including preprocessing, with a 28 ms p95 over 1,164 calls. That is compute time, not time until the agent answers."
- **Source / run:** [RESULTS.md](../benchmark/RESULTS.md) §5; timing code in [run_model_arm.py](../benchmark/scripts/run_model_arm.py). Per-call timing output is not committed.
- **Status:** ready as a reported exploratory measurement, stock only. A reproducible timing log is needed for a performance comparison; candidate cost is L-24.

### L-12 — Automated spot-check

- **Ready wording:** "The saved plot shows energy profiles for ten selected clips. It does not establish which silence is a block, who resumes, or whether the turn was unfinished. Human annotation is pending."
- **Source / run:** `benchmark/data/spotcheck/block_spotcheck_rms.png`; [spotcheck.py](../benchmark/scripts/spotcheck.py).
- **Status:** ready as automated inspection only. Do not assert listening is underway or completed without the reviewer log.

### L-13 — Gap durations and selection limits

- **Ready wording:** "The 200 selected detected gaps range from 0.30 to 1.59 s, with a median of 0.58 s. Three-second clips and the requirement for detected resumption exclude longer or censored cases. Our experiment has no result for multi-second blocks."
- **Metric / population:** N=200 gaps; p90 0.93 s; 79 candidate clips rejected because sustained resumption was not found. Those rejected silences are not themselves validated ongoing blocks.
- **Source / run:** `benchmark/data/block_eval.csv`, `benchmark/data/eval_tallies.json`; [build_eval_sets.py](../benchmark/scripts/build_eval_sets.py).
- **Status:** ready as a limit of our experiment, not "untested everywhere."

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

- **Ready wording:** "Apple's published work on Siri and atypical speech is relevant prior art; we use its SEP-28k dataset to investigate turn-taking in open voice agents."
- **Source:** Lea et al. 2023 and Siri accessibility settings, linked in [README.md](../README.md).
- **Status:** ready for this scoped attribution. The exact ~79% reduction and a claim that a particular research result shipped as a particular setting need direct source/definition checks before use; no absence claim follows from Apple's work.

### L-18 — Harness checkpoint versus deployed configuration

- **Ready wording:** "Our block experiment checks Smart Turn at +0.2 s after detected silence. We still need to pin and trace the deployed agent to establish when it checks or acts."
- **Source:** [run_model_arm.py](../benchmark/scripts/run_model_arm.py); proposed runtime evidence in [PLAN.md](../PLAN.md).
- **Status:** ready for the harness setting; production-default and runtime-equivalence claims are unverified.
- **To upgrade:** versioned runtime configuration, actual VAD/check events and cancellation behavior. A library default alone does not establish an end-to-end agent's behavior.

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

- **Ready wording (today):** "Our goal is an openly available turn-taking model evaluated on stuttered speech."
- **Target wording:** "To our knowledge, the first [precisely scoped contribution]" — only after the artifact exists and a current, documented prior-art review supports that scope.
- **Source / status:** [D-006](decision-log.md) supersedes D-003's earlier novelty conclusion. **Target**, not a verified absence claim.
- **To upgrade:** save primary-source links, search date and relevant alternatives; distinguish stutter-specific work from broader turn-taking benchmarks and adjustable existing systems. A search cannot establish universal absence.

### L-27 — "First public benchmark of voice-agent turn-taking on stuttered speech"

- **Ready wording (today):** "We have saved exploratory evaluation scripts and outputs; our goal is a reproducible public benchmark with validated labels."
- **Target wording:** a narrowly scoped "first" claim, only if current prior-art evidence supports it and the corrected benchmark is publicly usable.
- **Status:** target; the earlier D-003 search conclusion is not current validation under D-006.
- **To upgrade:** scoped primary-source review, corrected labels/splits, verified reproduction and resolved publication terms. Keep all existing general turn-taking benchmarks in the comparison.

### L-28 — "Apple fixed this inside Siri and kept it closed"

- **Ready wording:** "We build on Apple's SEP-28k dataset to study turn-taking in open voice agents."
- **Status:** ready for the dataset attribution. "Fixed this," the ~79% figure and the research-to-shipped-setting link require the checks in L-17; use the narrower wording meanwhile.

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
| L-35 | Long blocks (3+ s) untested **in our evaluation** — all selected detected gaps < 1.6 s | RESULTS §4 censoring caveat |
| L-36 | English-only, blocks-only: other languages and other disfluency types (repetitions, prolongations, interjections) untested; model card must say "English fine-tune — use stock for other languages" | RESULTS; Q&A |
| L-37 | Wideband 16 kHz audio only; 8 kHz narrowband phone channel untested | RESULTS §9 |
| L-38 | SEP-28k annotations are CC BY-NC 4.0; audio/demo permissions and trained-weight release terms need separate resolution before distribution; no unrestricted commercial-use promise | RESULTS §1 |
| L-39 | No one on the team stutters; nobody imitates stuttering, ever; real recordings only, labeled; research prototype, not a medical or therapeutic tool; it makes the agent wait — it does not recognize stuttered words better | README, D-004; model behavior remains a target |

## G. Never-say list (hard rules — no upgrade path)

- "All voice agents fail" (contradicted by our own L-08).
- Any medical, diagnostic or therapeutic claim. "We solved stuttering."
- One-second censoring described as a measured three-second fallback; conditional crossing times described as full-population response latency.
- Energy-derived cutpoints described as verified mid-word cuts or semantic turn ends; repeated offline checks described as a traced deployed schedule.
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
3. **Human annotation manifests** for every evaluated boundary and completed/unfinished-turn label, with context and speaker identity. Track the separate 30-example feasibility sheet from issue #1; that subset does not validate the old 200 examples or establish final-test efficacy (L-01/L-10/L-12).
4. **Matched causal timing and observation through the deployed timeout**, or explicit censoring; use finer than 100 ms resolution for the +50 ms target, both groups. Rebuild active-speech/true-end controls and save per-example outputs (L-02/L-03/L-06/L-10/L-21).
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
6. **Rehearsal:** the revised templates need timing with their actual interaction. No rehearsal is asserted; issue #4 requires three rehearsals with an unscripted participant before 10 PM.
