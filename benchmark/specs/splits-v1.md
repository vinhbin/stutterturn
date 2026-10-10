# Spec: show-separated split manifests v1

**Owner:** Niko · **Implementer:** Sonnet subagent · **Status:** spec revised after independent review and proof test (2026-10-10) · **PLAN:** E1, the first item under "Evaluation work required"

## Why

The exploratory 200 + 200 eval sets mix shows (block spans all 8, while fluent is **200/200 HeStutters**). They can't support a development decision or a final test, because the same podcast speaker and recording conditions can appear in training and evaluation. Every later step (training, threshold and checkpoint selection, the final report) reads its clip list from these frozen manifests.

## Scope

- **In scope:** one stdlib-only Python script that partitions the SEP-28k label rows by show into train, dev and test, and writes immutable, hashed manifests plus a verify mode. **Labels only**: the manifests never depend on whether audio exists.
- **Out of scope:** audio download, empty-clip filtering, energy-VAD gap detection, eval-set construction, training, and changes to existing scripts or `data/` files. A later spec rebuilds dev and test eval items *from* these manifests and filters unusable audio there.

## Decision: show assignment (fixed, not computed)

Counts are recomputed from `data/SEP-28k_labels.csv` after the quality gate, and independently verified.

| Split | Shows | Block | Fluent | Other disfluent |
|---|---|---|---|---|
| train | WomenWhoStutter, HeStutters, IStutterSoWhat, HVSA | 1,723 | 4,890 | 6,669 |
| dev | StutteringIsCool, MyStutteringLife | 549 | 3,056 | 2,277 |
| test | StrongVoices, StutterTalk | 844 | 3,394 | 2,813 |

Rationale:

- **HeStutters and WomenWhoStutter must share a split.** They are the only two shows whose audio comes from the same host (`stutterrockstar.files.wordpress.com`), and they share the series title "…Make Room For The Stuttering". That is evidence of a shared host voice. Both go to train.
- **Test is larger than dev**, as PLAN requires ("a larger, separate final test").
- Dev and test each have two shows.
- All 200 exploratory fluent clips (HeStutters) fall in train, and the exploratory block clips split 83 / 59 / 58. **The exploratory results can't serve as the dev or final-test comparator**; stock must be rerun on the rebuilt items.

The assignment is a constant in the script (`SHOW_SPLIT = {...}`). The script must fail if a show in the labels CSV is unassigned or an assigned show is missing.

**Expected usable sizes** (reviewer's estimate from gap/resume survival in RESULTS.md, not a promise): about 400 dev and 470 test block items. At p = 10%, n = 400 gives a 95% Wilson interval of about [7.4%, 13.3%]. With only two shows per split, the effective n is smaller. The 30-example feasibility set can't establish a 10% bound.

## Inputs

- `benchmark/data/SEP-28k_labels.csv`, read-only. Header: `Show,EpId,ClipId,Start,Stop,Unsure,PoorAudioQuality,Prolongation,Block,SoundRep,WordRep,DifficultToUnderstand,Interjection,NoStutteredWords,NaturalPause,Music,NoSpeech`. **Header names and values have leading spaces**, so strip every key and field.

## Row rules (applied in this order)

1. `clip_key = f"{Show}_{EpId}_{ClipId}"`, which matches the mirror filename stem (`HeStutters_1_133.wav`).
2. **Quality gate (identical to `select_clips.py:8,36-44`, verified):** exclude a row if any of `Unsure, PoorAudioQuality, DifficultToUnderstand, Music, NoSpeech` ≥ 2. Count the excluded rows in total and per reason. A row excluded for several reasons counts under each reason, but once in the total.
3. `category` (same order as `select_clips.py`):
   - `block` if `Block ≥ 2`
   - `fluent` if `NoStutteredWords ≥ 2` and each of `Prolongation, Block, SoundRep, WordRep, Interjection` < 2
   - `other_disfluent` otherwise. Keep these rows: training may use them later.
4. `split = SHOW_SPLIT[Show]`. Every row of a show goes to that show's split; no row-level sampling.

No episode is excluded. The earlier "exclude HeStutters episode 0" rule was dropped: review showed the empty mirror clips follow a truncation-by-time pattern across episodes, not one bad episode. Empty audio is handled when eval items are built.

## Outputs

Write to `benchmark/splits/v1/`:

- `train.csv`, `dev.csv`, `test.csv`. Columns, in order: `clip_key,show,ep_id,clip_id,start,stop,category,block,prolongation,sound_rep,word_rep,interjection,no_stuttered_words,natural_pause`. Integer vote columns. Rows sorted by `(show, ep_id as int, clip_id as int)`. LF line endings, UTF-8, no index column.
- `manifest.json`:
  ```json
  {
    "version": "v1",
    "created_utc": "...",
    "code_commit": "<git rev-parse HEAD or null>",
    "script": "benchmark/scripts/build_splits.py",
    "script_sha256": "...",
    "labels_csv": "benchmark/data/SEP-28k_labels.csv",
    "labels_sha256": "...",
    "show_split": {"WomenWhoStutter": "train", "...": "..."},
    "rules": {"quality_gate_votes": 2, "block_votes": 2, "fluent_votes": 2},
    "exclusions": {"quality_total": 0, "quality_by_reason": {"Unsure": 0}},
    "files": {"train.csv": {"sha256": "...", "rows": 0, "by_category": {"block": 0, "fluent": 0, "other_disfluent": 0}, "by_show": {}}},
    "limits": [
      "speaker identity unknown; separation by show only",
      "HeStutters and WomenWhoStutter share a host (same audio host domain and series title); kept together in train",
      "weak cross-show guest first-name matches only (geoff: HeStutters/StrongVoices; alex: StrongVoices/WomenWhoStutter); not verified",
      "gender skew: WomenWhoStutter mostly female, HeStutters mostly male, both in train",
      "two shows per dev/test split: show clustering reduces effective sample size",
      "at least 26 mirror clips are empty, consistent with truncated episode audio (e.g. HeStutters_0 after ~700 s, HeStutters_1 after ~1772 s); filtered when eval items are built, not here",
      "3 s clips: blocks longer than ~2.5 s cannot appear",
      "labels are SEP-28k annotator votes, not human-validated turn ends",
      "audio not included; rights remain with podcast owners"
    ]
  }
  ```

**Provenance and hashes.** `code_commit` is informational: the script is uncommitted at first build, so it may be null or stale. **`script_sha256` is the provenance of record.** The "split hash" consumed elsewhere (e.g. `model/CONTRACT.md` §5 `train_manifest_sha256`, `dev_manifest_sha256`) means **the sha256 of `train.csv` / `dev.csv` / `test.csv`**, not `manifest.json`, which contains a timestamp.

## CLI

```
python benchmark/scripts/build_splits.py            # build v1; refuse if benchmark/splits/v1/ exists
python benchmark/scripts/build_splits.py --check    # verify; exit 1 on any mismatch
python benchmark/scripts/build_splits.py --out DIR  # build into DIR instead (for tests); same refusal rule
```

`--check` (optionally with `--out DIR`) must:

1. Verify each CSV's sha256 and row count against `manifest.json`.
2. Verify that `labels_sha256` matches the current labels file.
3. Rebuild in memory from the labels and confirm the CSV bytes are identical.

A changed `script_sha256` produces a **warning only**, so later harmless edits don't break v1 verification. A rule change means a new `v2`.

- **Immutability:** if the output directory exists, exit non-zero. There is no `--force`.
- Paths resolve relative to the script file via `BASE`, as the existing scripts do. Stdlib only (`csv`, `json`, `hashlib`, `subprocess`, `argparse`, `pathlib`). No pandas. Python ≥ 3.10.
- Print a summary table (split × category counts, exclusions) to stdout.

## Acceptance checks (the implementer runs these and pastes the output)

1. A fresh build exits 0. A second run exits non-zero and leaves the files untouched (compare hashes before and after).
2. `--check` exits 0 on the fresh build. Build a second copy with `--out <scratch>/v1copy`, append one byte to its `dev.csv`, and `--check --out <scratch>/v1copy` exits 1. The committed files are never touched.
3. **Disjointness:** no `clip_key` appears in two files, no show appears in two files, and every `clip_key` is unique. The script asserts all three.
4. **Conservation:** 28,177 input rows = quality exclusions (expected 1,962) + rows across the 3 files.
5. **Counts equal the decision table exactly:** block 1,723 / 549 / 844; fluent 4,890 / 3,056 / 3,394; other 6,669 / 2,277 / 2,813. Any difference is a bug, or the data changed, so stop and report.
6. Every `clip_key` from `data/block_eval.csv` and `data/fluent_eval.csv` (strip `.wav`) is found in exactly one split. Expected: block 83 train / 59 dev / 58 test; fluent 200 train.
7. **Determinism:** build twice with `--out` into two different scratch directories. The CSVs are byte-identical, and `manifest.json` differs only in `created_utc`.

## Constraints for the implementer

- Write only `benchmark/scripts/build_splits.py` and the generated `benchmark/splits/v1/*`. Don't modify any other file.
- Don't commit or push. Niko reviews and commits, pulling latest first.
- If the data contradicts this spec (an unexpected show, a header mismatch, counts that differ from check 5), stop and report it. Don't adapt silently.
