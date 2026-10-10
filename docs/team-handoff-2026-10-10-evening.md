# Team handoff — Saturday evening (Oct 10, ~6 PM EDT)

Written from Vinh's side after absorbing Kareem's lane (he left this afternoon — decision log D-008). Main is at `1c8ae78` (PR #19 merged — every surface now cites replay v2); a Tiger Data scaffold PR plus a train-harness review are in flight. Everything below is backed by committed artifacts; links are in-repo.

## The site is hosted

- **https://64-177-51-1.sslip.io** — Vultr (Atlanta), HTTPS, serves `web/` from main. This is the Vultr sponsor integration. Redeploy goes through Vinh's session (seconds, incremental).
- The live-run console on the hosted page correctly shows *blocked* for visitors; live runs need the backend on the demo laptop. That is by design and labeled.

## What landed on main today (since noon)

- **Agent**: contract v0.1 implemented (PR #11), source-name + dirty-stamp fixes (#13), pre-roll model-input fix + **replay v2 evidence** (#14) — v2 **supersedes the first replay** (faulty model input). v2: stock premature in-gap completions on **4 of 5** clips, 3 replies cancelled before audio, no audible interruption in any run. `run_ended.t` clock clamp (#15, awaiting confirmation on a real run).
- **Benchmark**: frozen show-separated splits v1 + matched eval runner with hashed runs (#9); INT8 vs FP32 finding posted on issue #2 (E1).
- **Web**: landing + judge pages (#12), live adapter wired to contract v0.1 (#10), landing redesign in the console system (#18), committed 58-check verification suite — `web/demo-ui/dev/checks/README.md` has the two commands (#17).
- **Docs**: README accuracy pass + Kareem lane transfer (#16), pitch/claims ledger (#8); replay-v2 citation refresh across every surface is PR #19 (pending merge). Guttuu: note `agent/README.md` + `agent/CONTRACT.md` still cite the first replay — your lane, one-line updates.

## Critical path, by owner

**Vinh (tonight, in order)**
1. Human labels **A01–A15 then B01–B15** — exact category tokens from Niko's E1 comment (`unfinished_stutter_block`, `unfinished_fluent_pause`, `completed_stuttered_turn`, `completed_fluent_turn`); `time_origin` required. Everything evidential waits on this.
2. Record the gate decision with the team — a **DRAFT (undecided)** entry is prepared in the decision log; nothing is recorded as passed.
3. Three rehearsals + reset-under-60s before the 10 PM lock.
4. Tiger Data signup (mlh.link/tigerdata, ~5 min, like the Vultr one) — the integration is scaffolded and waits only on the connection string.

**Guttuu**
1. **Restart the backend on current main before recording anything else** — anything logged on pre-`bcf50d1` code is superseded on arrival.
2. Audio playback: engine receives PCM and discards it; the "judge hears it" beat needs playback + a cancellation/overlap retest.
3. Decide what to do with the 3 first-replay logs whose `run_ended.t` precedes their last event (clamp-on-read, footnote, or regenerate) — noted in PR #15.
4. If you can take it: the **independent cross-check of Vinh's labels** (was Kareem's). Needs a second human; flag rows marked `uncertainty` + 5 random rows.

**Niko**
1. **CRLF fix for the benchmark hash chain**: every SHA-256 in `benchmark/splits/v1/manifest.json` fails raw verification on Windows checkouts (CRLF), and `compare_runs.py` exits 2 across platforms because `items_sha256` differs. Repro'd on Vinh's machine; all four hashes pass after LF normalization. Smallest fix: `.gitattributes` with `*.csv`/`*.jsonl`/`*.json text eol=lf` for `benchmark/` + `git add --renormalize` (same pattern as `docs/proofs/model-mechanics/.gitattributes`).
2. Candidate: training harness is moving on `niko/model-benchmark`; the handoff needs the immutable `stutterturn-vN.onnx` + run records, compared against **stock FP32** per your own E1 rule.
3. Reviewed labels land tonight from Vinh — consume per your item builder.

**Decided (Vinh, Sat evening): Tiger Data stays.** Ownership moves to Vinh's side with the judges page. Scope: agent run logs as a time-series (events hypertable), with decision-vs-audio timing queries feeding an evidence chart on the judge view — real ingestion of real run logs, honestly labeled, no fabricated series. Build is credential-gated: Vinh signs up at mlh.link/tigerdata tonight and supplies the service connection string; the schema/ingest/chart scaffold is being prepared in parallel.

## Standing rules (unchanged)

Nobody imitates stuttering. Decisions ≠ interruptions. No rates from n=5. Nothing public without a committed artifact. 1 AM freeze.
