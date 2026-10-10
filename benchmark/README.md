# StutterTurn benchmark (kill test, Oct 10)

Measured results are in [RESULTS.md](RESULTS.md). Scripts in `scripts/`, metrics and eval CSVs in `data/`.

**Audio is not in this repo.** The clips are SEP-28k podcast audio; copyright stays with the podcast owners, so we don't redistribute them. To reproduce: `scripts/download_clips.py` fetches the clips from the Hugging Face mirror (`miosipof/sep28k_full`) using the official label CSVs in `data/` (SEP-28k annotations, CC BY-NC 4.0, Lea et al., ICASSP 2021 — non-commercial use with attribution).

The model under test is pipecat-ai Smart Turn v3.2 (BSD-2); clone github.com/pipecat-ai/smart-turn next to this folder (gitignored here).
