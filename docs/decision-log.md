# StutterTurn decision log

Dated entries, newest first. Confirmed team choices vs. proposals are kept distinct. A result claim requires saved test evidence.

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
