# Spec: dev/test eval items v1

**Owner:** Niko · **Implementer:** Sonnet subagent · **Status:** revised after independent review and proof test (2026-10-10) · **PLAN:** E1 · **Consumes:** `splits/v1` (`dev.csv` sha256 `3030592364bc…80b340`, `test.csv` `fd558b91fb40…32c2`) · **Produces:** item JSONL for `eval_runner.py`

## Why

The eval runner needs items with ground-truth timing, drawn only from frozen dev and test shows, with each item's evidence level explicit. The spec also gives humans a review path to confirm, correct or reject items.

## What 3-second clips can and cannot establish (read first)

SEP-28k clips are 3 s windows cut from longer episodes; the mirror has only the windows. All speakers on these shows are podcast participants, and many stutter, so the "fluent" group means **fluent-labelled clips**, not fluent speakers.

- **Unfinished stuttered (usable):** a `Block ≥ 2` clip with an energy gap, then an energy resume inside the clip. The resume may be **another speaker**, so these items are `energy_vad` until a human confirms them.
- **Unfinished fluent (weaker):** a mid-clip pause in a fluent-labelled clip. It may follow a finished sentence, and the resume may be another speaker. Energy only, until reviewed.
- **Completed turns: not provable from clips.** End-of-window silence isn't a turn end. Energy "completed" items are `end_of_window` proxies in separate files, never reported as turn-end delay. Real completed items come only from human labels made with episode context.
- **The fallback is censored:** with ≤ 3 s of audio and a 3.0 s fallback, it essentially never becomes observable.
- **The PLAN +50 ms delay criterion is degenerate under the `single` schedule.** Every completed item the model decides gets `delay_s = vad_stop_s` (0.2 s) exactly, because the only check is at `silence_start + 0.2` and `silence_start = turn_end`. The median difference between any two models is always 0. **The measurable completed-turn signal under `single` is the rate decided at the first check vs censored or fallback**, compared paired between models. Under `interval`, delay varies but is censored at the trailing silence. Gate reports must state this; delay medians must not be presented as evidence.
- **Making completed-turn delay measurable needs human labels:** about 50 (preferably 100) confirmed completed turns per group in dev, each with ≥ 0.5 s of post-end audio in the clip. "Stuttered" completed turns may come from **any** dev clip with stuttering labels, not only Block clips. Turn ends are confirmed in episode context (`SEP-28k_episodes.csv` URL + the split CSV's `start`/`stop`).

## Inputs

- `benchmark/splits/v1/dev.csv` and `test.csv`. Run `build_splits.py --check` first and refuse if it fails. **`train.csv` is read for its `clip_key` column only**, for leakage assertions.
- Audio at `benchmark/audio/<clip_key>.wav` (gitignored), fetched by `fetch_split_audio.py`.
- Energy VAD: **import** `analyze`, `find_first_gap` and `fluent_features` from `build_eval_sets.py` (verified free of side effects). Don't copy or alter them. Record the module's sha256. **Use each function's own `reason == "ok"` / returned pauses; never re-check `gap ≥ 0.30` with float comparisons** (the smallest valid gap computes as 0.2999999999999996).
- Optional human annotations: `--annotations DIR` (default `benchmark/annotations/`), all `*.csv` files with PLAN's header `sample_id,source_id,context_ref,speaker_id,category,time_origin,block_onset_s,resumption_s,turn_end_s,reviewer,reviewed_at,uncertainty,accepted`.

## Audio fetch: `benchmark/scripts/fetch_split_audio.py`

- Reads dev and test `clip_key`s and maps each to its mirror path by basename in `data/hf_miosipof_files.txt`. All 26,215 keys map uniquely (verified). Downloads with `hf_hub_download("miosipof/sep28k_full", path, repo_type="dataset")` into `benchmark/audio/`, with 16 threads.
- Skips files already present and over 1000 bytes. **Records empty mirror files in `benchmark/audio/empty_on_mirror.txt` and skips them on later runs**, rather than re-fetching every time.
- Default: block + fluent for dev and test (about 7.8k clips, ~750 MB, roughly double during download because of the HF cache). `--splits` and `--categories` narrow it. Writes `benchmark/audio/fetch_log.json`.

## Item construction (dev and test independently)

Item fields are exactly the runner's: `item_id, clip_key, audio, split, group, kind, silence_start_s, resume_s, turn_end_s, observe_until_s, label_source`. **`audio = "audio/<clip_key>.wav"`**, relative to `benchmark/`, which is how the runner resolves it. Extra provenance goes in `provenance.jsonl` (the runner would pass extra fields through, but keep items minimal).

**Audio gate, applied before calling `analyze` (which asserts 16 kHz):** exclude the clip if the file is missing, listed as empty on the mirror, not 16 kHz, shorter than 2.9 s, or has peak |x| < 1e-4. Tally each reason. `observe_until_s` = the actual duration.

1. **`stuttered/unfinished`**, from block clips: `find_first_gap(analyze(path))` with `reason == "ok"` → `silence_start_s = gap_start`, `resume_s = resume`, `label_source = "energy_vad"`. One item per clip. Tally the rejection reasons. Items whose gap is ≤ `vad_stop_s` (0.2 s) have no model check before the resume, so they always count as not-premature. Exclude them as `gap_not_checkable`. Expect none, since gaps are ≥ 0.30 s.
2. **`fluent/unfinished`**, from fluent clips with `fluent_features(...)["total_speech"] ≥ 0.5` (the exploratory filter): take the first returned pause → `silence_start_s = pause_start`, `resume_s = pause_end`, `energy_vad`. One item per clip.
3. **`fluent/completed` proxy**, from fluent clips with total speech ≥ 0.5 and trailing silence ≥ 0.50 s: `turn_end_s = silence_start_s = speech_end`, `resume_s = null`. These go to `<split>_end_of_window.jsonl` only.
4. **Completed items in general:** `silence_start_s = turn_end_s`. Drop the item as `post_end_too_short` if `observe_until_s − turn_end_s < vad_stop_s`, because its grid would be empty and it would always be censored.

Item ID: `f"{split}-{stu|flu}-{unf|cmp}-{clip_key}"`.

## Human labels (confirm, correct, reject)

**Category vocabulary (exact tokens; tell Vinh and Kareem before labelling):** `unfinished_stutter_block`, `unfinished_fluent_pause`, `completed_stuttered_turn`, `completed_fluent_turn`. Any other string → reject the row with its reason; never fuzzy-match.

**`time_origin`:**
- `clip_start` or `source_audio_start` (the agent contract's origin): times are clip-relative.
- `episode_start`: subtract `start / 16000` from the split CSV row.
- Empty or anything else: reject.
- A converted time outside [0, duration]: reject.

**Row handling**, for rows whose `source_id` (stripping `.wav`) is a dev or test `clip_key`:
- **`accepted` true and `uncertainty` empty:**
  - An unfinished category creates or replaces that clip's item of that kind, with `label_source = "human"` and `resume_s = resumption_s`.
  - `silence_start_s` **keeps the energy value**, because the deployed VAD triggers on energy silence. If `|block_onset_s − energy gap_start| > 0.10 s`, flag it in provenance as `onset_disagreement`. With no energy item, use `block_onset_s`.
  - A completed category creates a `completed` item in the **main** file, with `turn_end_s` and `silence_start_s = turn_end_s`, subject to the `post_end_too_short` rule.
- **`accepted` true but `uncertainty` non-empty:** reject the row as `uncertain`, and keep the energy item.
- **`accepted` false with a non-empty `reviewer`:** **remove** that clip's energy item of the matching kind and count it as `human_rejected`. This is how a reviewer removes, say, an item whose resume is the interviewer.
- **Rows whose clip is in train or unknown:** count as `annotations_not_in_dev_test` and ignore.

**Leakage rule:** human-labelled dev and test clips must never feed training. PLAN allows feasibility labels to feed training, so the manifest lists every annotated dev/test `clip_key` in `annotated_dev_test_keys`, and training must exclude them. If F3/F4 drew blocks from `block_eval.csv`, about 58% of them are dev/test, which is fine for evaluation and forbidden for training.

**Annotations arriving after a build mean a new version** (`items/v2`). v1 is never edited.

## Outputs: immutable `benchmark/items/v1/`

- `dev.jsonl` and `test.jsonl` (main items), `dev_end_of_window.jsonl` and `test_end_of_window.jsonl` (proxies). Sorted by `item_id`.
- `provenance.jsonl`: `{item_id, source, annotation_file, sample_id, reviewer, vad_params, gap_or_pause_dur_s, trailing_sil_s, total_speech_s, show, block_votes, interjection_votes, natural_pause_votes, replaced_energy_item, onset_disagreement}`. Show and vote fields allow per-show and NaturalPause/Interjection-stratified reporting by joining on `item_id`.
- **`review_queue_dev.csv`**, using the PLAN header. Rows are chosen by the lowest `sha256(item_id)` within each bucket: **20 stuttered/unfinished, 20 fluent/unfinished, and 25 completed-turn candidates per group**. The stuttered candidates come from dev clips with trailing silence ≥ 0.5 s in any non-fluent category; the fluent candidates are end-of-window proxies.
  - `sample_id`s are `D001…` (no collision with A01–B15). `source_id = clip_key`. `context_ref = "<episode URL>#t=<start/16000 s>"`. `time_origin = clip_start`. `category` is pre-filled with the candidate's category token.
  - **All time columns and `accepted` are left blank**, so reviewers aren't anchored on the energy times. The energy times go in a separate `review_queue_dev_energy.csv`, keyed by `sample_id`, for the merge.
  - Never sample the review queue from test.
  - Purpose: estimate label accuracy and seed completed-turn items. **n = 20 can't detect a fluent regression** (the 95% CI is about ±20 points). State this in the manifest.
- `manifest.json`: version, created_utc, script and `build_eval_sets.py` sha256s, verified split sha256s, VAD params, annotation files and their sha256s, the category vocabulary and its `time_origin` handling, all tallies (per split × source category × reason, including `human_rejected` and `uncertain`), item counts per split × group × kind × label_source, output sha256s, `annotated_dev_test_keys`, `test_sealed: true`, and `limits`. The limits restate this spec's "can and cannot establish" section, plus:
  - per-show VAD threshold differences (MSL's quietest frames ≈ −84 dB vs SV ≈ −59 dB) shift item yield by show;
  - 8 of 117 overlap block items also carry Interjection ≥ 2;
  - NaturalPause ≥ 2 on 10 of 117 block and 16 of 52 fluent overlap items.

The build prints the test sha256 with the instruction to record it in the decision log. No model or threshold selection uses test.

Refuse if `benchmark/items/v1/` exists. `--out DIR` is for tests. `--check` re-verifies output and split hashes.

## Compute (estimates from the reviewer's prototype; per model, at ~25 ms/call)

- Dev main items: about 87k grid calls, roughly 36 min.
- Dev proxies: about 82k calls, roughly 34 min.
- Test is similar.
- The cache makes reruns of the same model free.
- For the 3 PM dev decision, run stock FP32, stock INT8 and candidates on **dev main items first**; proxies are optional.

## Acceptance checks (paste commands and output)

1. `fetch_split_audio.py` (default) completes, with ok / cached / failed / empty-on-mirror counts. A second run makes no network calls for files known to be empty.
2. The build produces all outputs and prints the item counts, tallies and sha256s. A second build refuses, and `--check` passes.
3. **Leakage:**
   - no item's clip_key is in `train.csv`;
   - dev items come only from StutteringIsCool/MyStutteringLife;
   - test items come only from StrongVoices/StutterTalk.
4. **Exploratory consistency:** for the 117 overlap clips (59 dev, 58 test), `silence_start_s` and `resume_s` equal `block_eval.csv` `gap_start` and `gap_start + gap_dur` within 0.011 s. The reviewer measured a max difference of 0.000.
5. **Runner compatibility:**
   - `eval_runner.load_items()` validates every line of all four JSONL files (import it; it has no side effects).
   - A `--scratch` run of a 3-line subset of `dev.jsonl` with stock INT8 succeeds.
   - A 3-line subset of `dev_end_of_window.jsonl` under `agent-v0.1-single` reports either `delay_s = 0.2` or `censored`, which confirms the degenerate-delay statement.
6. **Human path:** use `--annotations <scratch dir>` and `--out <scratch dir>` with a hand-made CSV. It must yield exactly:
   - one replacement from an accepted dev `unfinished_stutter_block`;
   - one human completed item from an accepted dev `completed_fluent_turn` with ≥ 0.2 s of post-end audio;
   - one `human_rejected`, which removes the energy item;
   - one `uncertain` rejection;
   - one train row → `annotations_not_in_dev_test`;
   - one `episode_start` row converted correctly;
   - one bad-category rejection.

   Report each outcome.
7. The review queue has 90 rows with the exact PLAN header, dev keys only, blank time and `accepted` columns, `D`-prefixed IDs and a matching energy sidecar.

## Files the implementer writes

- `benchmark/scripts/fetch_split_audio.py`, `benchmark/scripts/build_items.py`
- The generated `benchmark/items/v1/*`

Don't modify `build_eval_sets.py`, the runner, the splits, existing data, or anything outside `benchmark/`. Don't create `benchmark/annotations/`. Don't commit or push. If the data contradicts the spec, stop and report.

## Acceptance results (2026-10-10, macOS)

All 7 checks passed (Sonnet implementer, re-verified by Opus: `build_items.py --check`, `build_splits.py --check`, split membership, ID uniqueness, audio paths, ordering of `silence_start_s < resume_s <= observe_until_s`).

| split | group | kind | file | n |
|---|---|---|---|---|
| dev | stuttered | unfinished | main | 352 |
| dev | fluent | unfinished | main | 1,518 |
| dev | fluent | completed | end_of_window | 680 |
| test | stuttered | unfinished | main | 415 |
| test | fluent | unfinished | main | 1,311 |
| test | fluent | completed | end_of_window | 833 |

All items are `energy_vad`; no human items exist yet, so the main files contain no completed turns. 27 dev/test clips are empty on the mirror (`benchmark/audio/empty_on_mirror.txt`, local). Check 5 confirmed the degenerate delay: end-of-window items decided by the model all show `delay_s` = 0.2.

- `dev.jsonl` sha256 `742b645ba7213fecc0753d6c10376e330673b70c0d21d59881f0ca442e962ee3`
- `test.jsonl` sha256 `6bddc5b6b59ad2b929b0542828199d13c0130cd450b57394f7ac2488b6c26d32` (sealed: final evaluation only)

Implementation choices where the spec was silent:
1. Stuttered completed review candidates are drawn from dev block and `other_disfluent` clips with ≥ 0.5 s trailing silence (dev `other_disfluent` audio is fetched for this).
2. `accepted=false` with no reviewer is rejected as `ann_declined_without_reviewer`; nothing changes.
3. A human completed item and an end-of-window proxy for the same clip share an `item_id`; `provenance.jsonl` carries `file` (`main` / `end_of_window`) to disambiguate.
4. Malformed annotation rows (bad `time_origin`, out-of-range time, missing required time, duplicate) are rejected under `ann_<reason>` tallies.
