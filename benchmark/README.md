# StutterTurn benchmark (kill test, Oct 10)

Measured results are in [RESULTS.md](RESULTS.md). Scripts in `scripts/`, metrics and eval CSVs in `data/`.

**Audio is not in this repo.** The clips are SEP-28k podcast audio; copyright stays with the podcast owners, so we don't redistribute them. To reproduce: `scripts/download_clips.py` fetches the clips from the Hugging Face mirror (`miosipof/sep28k_full`) using the official label CSVs in `data/` (SEP-28k annotations, CC BY-NC 4.0, Lea et al., ICASSP 2021 — non-commercial use with attribution).

The model under test is pipecat-ai Smart Turn v3.2 (BSD-2); clone github.com/pipecat-ai/smart-turn next to this folder (gitignored here).

## Reproducing byte hashes

The scoped `.gitattributes` keeps benchmark CSV, JSON, JSONL and Python files at
LF on every checkout, including Windows. Manifests hash the actual file bytes;
do not change their expected hashes to accommodate CRLF conversion.

Verify a fresh checkout with `python benchmark/scripts/build_splits.py --check`
from the repository root. An existing working copy may still have CRLF files
until Git checks them out again; preserve local changes before refreshing it.
Previously generated runs with mismatched input hashes remain incompatible:
reproduce them under new run IDs instead of rewriting historical provenance.
