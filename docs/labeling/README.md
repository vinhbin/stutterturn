# Start the human listening pass

Open [proposed-a.csv](proposed-a.csv), then [proposed-b.csv](proposed-b.csv). These are **proposed worksheets, not annotations or completed reviews**. Each batch has five candidates for each PLAN feasibility category. Every category is provisional; all timing, reviewer, uncertainty and acceptance fields are blank.

Start with **A01 / D012: `MyStutteringLife_7_92`**. The 3-second WAV already exists in the local kill-test audio archive. Open its [episode context at 1077.78 seconds](https://traffic.libsyn.com/secure/mystutteringlife/Final_Gal_Zussman_for_Libsyn.mp3?dest-id=1660175#t=1077.78), listen before and after that point, then inspect the excerpt. If the player ignores `#t=`, seek to **17:57.78** yourself. Availability of this episode was checked; the other episode links have not been checked.

For each row:

1. Open `context_ref` and listen to enough surrounding conversation to identify the speaker and whether their turn continues. A clip boundary, silence or an automatic label cannot establish a real turn end. If you have the excerpt locally, its filename is `<source_id>.wav`; these worksheets contain no audio.
2. For `unfinished_stutter_block`, confirm a block interrupts an unfinished turn and the **same speaker** resumes; enter `block_onset_s` and `resumption_s`. For `completed_stuttered_turn`, confirm stuttering in the turn and its actual end; enter `turn_end_s`. For `completed_fluent_turn`, confirm a fluent turn and its actual end; enter `turn_end_s`. Fluent here describes the recorded speech, not a diagnosis of the speaker. Leave inapplicable timing cells empty.
3. Keep `time_origin=clip_start`: seconds are relative to the excerpt's start, so an event 1.2 seconds into it is `1.2`. The episode time in `context_ref` identifies that start. Alternatively, set `episode_start` and enter episode-relative seconds consistently. Events must fall within the source excerpt; completed turns need at least 0.2 seconds of post-end audio for the runner (prefer 0.5 seconds).
4. Enter your name in `reviewer`, a dated timestamp in `reviewed_at`, and a speaker identifier only if known. Set `accepted=true` only after personally confirming the category and timing with no unresolved uncertainty. Agents cannot perform this human review for you.

If context is unavailable or you are unsure, leave `accepted` blank, explain why in `uncertainty`, and report the shortage. If listening disproves the proposed category (for example, a different speaker resumes), record `accepted=false` with your reviewer/date and explanation; Niko uses a reviewed rejection to remove the matching automatic item. Do not silently switch categories to fill a quota. Request a replacement from the next unused candidate in the same category, preserve the rejected row and record the replacement's D ID. Missing categories remain missing. Unfinished fluent pauses are additional regression coverage, not replacements for these three categories.

Vinh completes and hands off **A first, then B**. A second human still needs assignment: they must cross-check every B row marked uncertain plus five randomly selected B rows before Niko consumes B. Record their identity, sample IDs and outcomes in a separate handoff note; do not add columns to the CSV header. An accepted row with nonempty `uncertainty` is rejected by the builder.

After actual review, deliver the exact PLAN-header CSVs as:

- `benchmark/annotations/feasibility/vinh.csv` for A.
- `benchmark/annotations/feasibility/kareem.csv` for B (legacy filename; `reviewer` names the actual person).

Those output files have **not** been created by this packet. Niko validates them and, once his item builder and required source audio are available, uses:

```powershell
python benchmark/scripts/build_items.py --annotations benchmark/annotations/feasibility --out benchmark/items/v2
```

The explicit child directory matters: the builder does not search annotations recursively. Never overwrite items v1. These candidates are all development sources and must not enter training or the sealed final test. Thirty feasibility examples cannot establish population rates or release efficacy.

Provenance: [Niko's dev review queue](https://github.com/vinhbin/stutterturn/blob/33e4498e7f38732c7b18bf5cec34021a7053196a/benchmark/items/v1/review_queue_dev.csv), revision `33e4498e7f38732c7b18bf5cec34021a7053196a`; [source-map.csv](source-map.csv) preserves every D ID. Selection uses queue order: unfinished-stutter starts at D012, the first cached candidate, then wraps; completed categories start at their first rows. The first five per category go to A, the next five to B. This convenience selection uses no model outcomes; proposed sources are disjoint. [Full annotation rules](https://github.com/vinhbin/stutterturn/blob/33e4498e7f38732c7b18bf5cec34021a7053196a/benchmark/specs/eval-items-v1.md).
