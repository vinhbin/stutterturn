# Worktree handoff for Vinh's tasks

Use this after reading [PLAN.md](../PLAN.md), especially the 2 PM/3 PM decisions. **Two independent builders plus one read-only reviewer** are enough. These are executable task boundaries, not an instruction to start model training, contact people, purchase services or claim a gate passed.

## All four teammates work in parallel

| Teammate | Branch/worktree lane | Exclusive writes | Starts without waiting for |
|---|---|---|---|
| Niko | `niko/model-benchmark` | `model/**`, `benchmark/**` | UI, hosted page or phone number; checkpoint smoke test proceeds while humans label |
| Guttuu | `guttuu/web-agent` | `agent/**`, including `agent/CONTRACT.md` | Candidate model; use stock and document the proposed event/run contract first |
| Kareem | `kareem/judges-page` | `web/**` excluding `web/demo-ui/**`; `README.md` | Final metrics; build the shell with labeled previews, replace with real runs later |
| Vinh | Builder A/B branches below | `web/demo-ui/**`; listed pitch/evidence docs | Tuned weights; UI adapter and pitch checklist proceed while Vinh labels audio |

Niko owns `model/CONTRACT.md`; Guttuu owns `agent/CONTRACT.md`. Draft these within the first 15 minutes of the sprint, mark unimplemented behavior proposed, and version changes. Consumers can scaffold against that contract before live integration. Keep root manifests/lockfiles out of concurrent writer scopes; Vinh coordinates any required shared-file change. Human annotation is split between Vinh A01–A15 and Kareem B01–B15, five distinct examples per category each; see PLAN.md. One owner merges reviewed increments at a time.

## Start and integration rules

1. Fetch latest `main`, inspect repo instructions/status and create a separate branch/worktree per builder. Do not reset or clean another person's working directory.
2. Check the actual repo before choosing tools. The planned minimal demo is plain web UI plus the agent's documented event stream; reuse any stack already landed rather than creating a competing scaffold.
3. Respect the file ownership below. Shared interface changes go through Guttuu (agent) or Niko (model/evaluation); flag dependency gaps instead of inventing working endpoints or statistics.
4. Commit only owned changes and open a focused PR with the working command, evidence and remaining blockers. Vinh coordinates merges one at a time against latest `main`; do not merge a teammate's branch automatically.
5. A UI fixture is allowed only as a clearly labeled development preview, never as live agent output or benchmark evidence. No fabricated speech/metrics and no imitated stuttering.

## Builder A — minimal demo UI

**Suggested branch:** `vinh/demo-ui`. **Write scope:** `web/demo-ui/**` only. Kareem owns the surrounding judges page. Root manifests, shared types or page integration require coordination with Kareem/Guttuu before editing.

**Task prompt:**

> Build Vinh's minimal StutterTurn demo surface in `web/demo-ui/`. Read PLAN.md, this handoff and the current agent implementation first. Before wiring controls, use Guttuu's documented run-control and event contract, including run ID and timestamp origin. If no backend contract exists, prepare a passive UI and documented adapter boundary; mark live integration blocked rather than inventing endpoints. Show selected model/configuration, run status, caller/agent state, source recording label and observed timing events. Separate internal completion decisions from audible responses. Provide keyboard-accessible controls, visible loading/disconnection/error states and a reset. Permit model changes between fresh runs so stock/candidate comparisons replay the same source; do not silently switch weights mid-call. Use a labeled preview only if needed for development, with no real-result claims. Keep styling minimal until the core proof passes. Do not modify agent/, model/, benchmark/ or Kareem's page. Document how Kareem embeds or links this surface and how to run it.

**Dependencies:** Guttuu's implemented connection/control contract and allowed replay sources; Niko's model IDs if a candidate exists. The UI must handle a stock-only/comparison fallback without presenting a nonexistent StutterTurn model as available.

**Done when:** the page runs with a documented command; controls work by keyboard; a fresh run resets prior events; failures are visible; events are attributed to the correct run/configuration. Once backend is available, demonstrate one actual run and reconnection/reset. Until then, mark integration pending. Review development previews separately from live evidence. Follow project checks if present; do not add a heavy test stack for a static shell.

## Builder B — strong pitch and evidence checklist

**Suggested branch:** `vinh/pitch-evidence`. **Write scope:** `docs/pitch-and-qa.md`, `docs/submission.md`, `docs/claims-ledger.md`. Do not edit PLAN.md, the decision log, README, benchmark results or sponsor documentation concurrently with their owners.

**Task prompt:**

> Prepare Vinh's strongest supportable three-minute pitch and Q&A. Preserve the ambitious pitch draft; Vinh specifically does not want it replaced by a tentative “we're testing whether…” script. Clearly separate intended final wording from statements ready to deliver today. Create `docs/claims-ledger.md` with each claim, proposed wording, exact metric/population, source or run ID, status (ready/target/unsupported) and evidence needed. Treat the 58% as exploratory model completion predictions until human labels and pipeline outcomes are validated; do not translate it into callers interrupted, call abandonment or hang-ups. Keep the scope of “first” narrow and sourced, and replace universal setting claims with the tested configurations only when that test exists. Leave candidate results as explicit placeholders until Niko supplies immutable evidence. Prepare both the successful-model pitch and corrected-benchmark fallback, with real recording and recorded-video disclosures. Align docs/submission.md and Q&A to the current gates; do not invent personal testimony or promise commercial deployment of a research-only artifact. Return a list of evidence requests for Niko/Guttuu and publish-ready wording for Vinh to review.

**Dependencies:** saved verified runs, annotation/split manifests, source references and actual build status. Missing evidence blocks the claim, not preparation of the draft.

**Done when:** every quantitative, novelty, implementation and compatibility claim has a status and source/evidence request; current deliverable wording contains no target represented as an achieved result; the successful-model and fallback scripts match their actual artifacts; links resolve; the spoken script fits three minutes in a timed rehearsal by Vinh. The agent can estimate length but cannot claim that Vinh rehearsed it.

## Reviewer — read only

> Review both branches against PLAN.md and the actual implementation. Check ownership conflicts, invented API behavior, run/state isolation, accessible controls, preview/live labeling and unsupported claims. Verify that all candidate percentages use the same final test as stock and that completed stuttered turns are included in response-delay/nonresponse checks. Identify anything that would mislead a judge or prevent a live run. Do not edit files, change issues or merge branches. Report blockers first, with file/line references and the smallest correction.

## Human tasks and blockers

- **Vinh + Kareem:** listen to and label their disjoint halves of the 30 feasibility examples using context; agents may prepare the annotation sheet and organize files but must not mark human verification complete.
- **Vinh:** record the 2 PM and 3 PM scope decisions with the team, review claims and perform rehearsals. Keep tasks open until evidence exists.
- **Niko/Guttuu:** own training, evaluation and the real audio path; a UI agent cannot certify these by simulating events.
- Optional sponsor integrations, phone transport and visual polish become eligible after the core proof; the 1 AM freeze still applies.
