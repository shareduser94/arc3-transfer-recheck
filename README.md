# Transfer and Re-checking of Learned Rules Across Levels in ARC-AGI-3

Code and prediction record for the paper. The paper itself (PDF, LaTeX and Word) is at
[https://github.com/shareduser94/paper](https://github.com/shareduser94/paper); the raw results are at [https://github.com/shareduser94/results](https://github.com/shareduser94/results) and the batch-run logs at
[https://github.com/shareduser94/logs](https://github.com/shareduser94/logs).

An agent that learns a game's rules while playing must decide, at each new level, how far to
trust what it learned on the last one. We study that decision on the 25 public ARC-AGI-3 games
with simple, training-free agents (a state-graph explorer plus per-object-kind effect statistics),
paired by seed, with predictions written down before every experiment.

**Main findings**

- Carrying statistics across levels saves actions on average (36 of 51 paired runs, sign test p = 0.002)
  but fails when a decisive rule was learned from only a few tries (game lf52: 3 of 10 seeds vs 9 of 10).
- Re-checking old rules repairs the failure, but broad re-checking costs about what transfer saves.
- Both patterns replicate inside a combined agent (ours + Rudakov et al.'s explorer) that roughly
  doubles the score (0.60).
- In procedurally generated games, the better strategy flips at roughly 32–48 irrelevant object kinds.
- "Effective-thin" re-checking was as safe as starting fresh on fresh seeds and fixed lf52 on 10/10,
  but its speed advantage was **not** confirmed on fresh seeds (59 %, p = 0.11).

`predictions.md` contains every dated prediction and its outcome, including the misses.

## Setup

Tested with Python 3.13 on Windows.

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

The ARC-AGI-3 game files are **not** included. The `arc-agi` toolkit downloads them into
`environment_files/` on first use (an ARC API key may be required; set it as the environment
variable `ARC_API_KEY` — never commit it).

**Always set `PYTHONHASHSEED=0`** (the published explorer iterates over sets of strings):

```bash
set PYTHONHASHSEED=0            # PowerShell: $env:PYTHONHASHSEED=0 ; bash: export PYTHONHASHSEED=0
```

### Third-party code (combined agent and Rudakov et al. explorer only)

`rudakov_runner.py` and the `--hybrid` option use the unmodified code of Rudakov, Shock & Cowley
(MIT licence). It is not redistributed here. Clone it **next to** this repository, as a folder named
`rudakov`:

```bash
cd ..
git clone https://github.com/dolphin-in-a-coma/arc-agi-3-just-explore rudakov
```

## Running

| What | Command |
|---|---|
| Rule agent, one mode, one seed | `python rule_agent.py --mode transfer --seed 0 --budget 10000` |
| Modes | `reset`, `transfer`, `surprise`, `droponly`, `selective`, `voi`, `effthin` |
| Combined agent | add `--hybrid` |
| Restrict games | `--games lf52,lp85` |
| Baselines (random, explorer) | `python agents.py --agent random --seed 0` |
| Rudakov et al. explorer (fixed) | `python rudakov_runner.py --seed 0 --budget 10000` |
| Rudakov et al. explorer (as published) | add `--as-is` |
| Generated games | `python gen_run.py --mode transfer --set {main,noise,dense}` |
| Validate generated games | `python gen_validate.py`, `gen_validate_noise.py`, `gen_validate_dense.py` |
| Batch runs used in the paper | `run_batch*.py` |
| Paired comparisons | `compare_*.py` (outputs are the matching `compare_*.txt`) |

Results are written to `results/` as JSON (`{hyb_}{mode}_s{seed}{tag}.json`). All result files used
in the paper are published at [https://github.com/shareduser94/results](https://github.com/shareduser94/results). Clone them into `results/` to re-run every
`compare_*.py` without re-playing the games:

```bash
git clone https://github.com/shareduser94/results results
```

## Repository layout

```
*.py              agents, generator, runners, analysis scripts
compare_*.txt     paired-comparison outputs quoted in the paper
predictions.md    dated predictions and outcomes, step by step
results/          (not included) raw per-run JSON results; see the results repository
```

Hosted in separate repositories:

- Paper (LaTeX source, PDF, Word, figure script, bibliography): https://github.com/shareduser94/paper
- Results (raw per-run JSON for all runs in the paper): https://github.com/shareduser94/results
- Logs (console logs of the batch runs): https://github.com/shareduser94/logs

## Paper

The paper is at [https://github.com/shareduser94/paper](https://github.com/shareduser94/paper). It contains:

- `paper.tex` + `references.bib` + `figure1.pdf` — build with
  `pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper`.
- `paper.docx` — Word version generated from the LaTeX source (`build_docx.sh`, needs pandoc).
- `paper_claude-doc.docx` — export of the original working draft.
- `make_figure.py` — regenerates Figure 1.

## Citation

```bibtex
@misc{arc3transferrecheck2026,
  title  = {Transfer and Re-checking of Learned Rules Across Levels in ARC-AGI-3},
  year   = {2026},
  url    = {https://github.com/shareduser94/arc3-transfer-recheck}
}
```

## Licence

MIT (see `LICENSE`). ARC-AGI-3 games and the Rudakov et al. code are under their own licences and
are not included.
