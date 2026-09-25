# Reproducing LedgerBench with a local model (Qwen, etc.)

This runs the full benchmark end-to-end and regenerates **every reported
number from committed data** (`results/metrics.csv`, `results/h1_events.csv`,
and the plots). It works against any model exposed through an
OpenAI-compatible `/v1/chat/completions` endpoint — the way Ollama, vLLM, and
LM Studio serve local models — so you can drive it with a **local Qwen**
instead of the Anthropic or DeepSeek APIs.

Only the transport changes: prompts, `<file>`-block parsing, the hidden
oracles, the governance logic, and the logging are identical to the Anthropic
backend. See `harness/agent.py:OpenAICompatibleSolver`.

> **Note on comparability.** The tables in the paper / `TRAPS.md` / `README.md`
> were reported for `claude-sonnet-4-6`. Running here with Qwen produces a
> *new, real* dataset that documents **Qwen's** behavior — it is not a
> reproduction of the Sonnet numbers. Commit the generated `results/` as the
> traceable backing for whatever model you actually ran, and label the model
> in any numbers you publish. Do not paste these outputs under the existing
> Sonnet tables.

---

## 1. Prerequisites

```bash
git clone <this-repo> ledgerbench && cd ledgerbench
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt                      # includes the `openai` client
```

## 2. Serve Qwen locally (OpenAI-compatible)

### Option A — Ollama
```bash
ollama pull qwen2.5-coder:32b     # or :7b / :14b, whatever you run locally
```
The default Ollama context window (4096 tokens) is **too small** — the ledger
prompts grow long and will be silently truncated, corrupting the results.
Raise it with a Modelfile:
```bash
printf 'FROM qwen2.5-coder:32b\nPARAMETER num_ctx 32768\n' > Modelfile
ollama create qwen2.5-coder-32k -f Modelfile
ollama serve   # if not already running; endpoint: http://localhost:11434/v1
```
Use `qwen2.5-coder-32k` as the model tag below.

### Option B — vLLM
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --max-model-len 32768            # endpoint: http://localhost:8000/v1
```

## 3. Point the harness at it

```bash
export LEDGERBENCH_BACKEND=openai
export OPENAI_BASE_URL=http://localhost:11434/v1   # Ollama; vLLM: :8000/v1
export OPENAI_API_KEY=not-needed                    # local servers ignore it
export LEDGERBENCH_MODEL=qwen2.5-coder-32k          # the served model tag
# Reasoning variants (e.g. QwQ) spend output budget on thinking; raise if so:
# export LEDGERBENCH_MAX_TOKENS=16000
```

### Optional: show the project file layout (`LEDGERBENCH_SHOW_LAYOUT=1`)

The published README lists the CLI commands and storage format but **not the
source files**, while the generator is asked to return complete files without
seeing the workspace. A model that doesn't know the layout may write a new
top-level `taskcli.py` — which `python -m taskcli` never runs, because the
seeded `taskcli/` package shadows it — so tasks fail for a reason unrelated to
the memory condition. This shows up as near-zero pass rates across all arms.

```bash
export LEDGERBENCH_SHOW_LAYOUT=1
```

appends a short layout block (the source file **names** only, not their
contents) to the README shown to **every** arm, so the arms stay a fair
comparison and only the path-guessing confound is removed. Default (unset)
reproduces the published protocol exactly. **If you enable it, report it as a
protocol change alongside your numbers.**

> Do not confuse this with showing the file *contents*: that would let the
> model read earlier requirements straight from the code and would weaken the
> memory comparison the benchmark is built on. This flag exposes names only.

## 4. Smoke test (a couple of tasks, one arm)

```bash
LEDGERBENCH_TASKS=2 python -m harness.run_pilot --arm A --seed 1
```
Confirm `runs/run_armA_seed1_*/log.jsonl` was written and its `run_start`
record shows `"backend": "openai"` and your model tag.

## 5. Full campaign (5 arms × 12 seeds = 60 runs)

```bash
for arm in A B C C+ D; do
  for seed in $(seq 1 12); do
    python -m harness.run_pilot --arm "$arm" --seed "$seed"
  done
done
```
(Unset `LEDGERBENCH_TASKS` first so all 24 tasks run.) This is the expensive
step — it is many model calls per run. It is resumable in the sense that each
run writes its own `runs/<id>/` directory; re-running only adds directories.

## 6. Score and check isolation

```bash
# Optional: re-score preserved workspace states against the current oracles.
python -m harness.rescore runs/run_*

# Metrics + H1 events + plots -> results/
python -m harness.analyze

# Hidden-oracle leak and separation-of-powers scans (expect 0 hits each).
for r in runs/run_*; do python -m harness.analyze --leak-check "$r"; done
for r in runs/run_*; do python -m harness.analyze --separation-check "$r"; done
```
`results/metrics.csv` and `results/h1_events.csv` now contain every empirical
number (M1 retention, H1 trap/rewrite/coercion counts, per-arm token costs,
governance events), each traceable to a run directory.

## 7. Commit the data

`runs/` and `results/` are in `.gitignore`, so force-add what you want tracked:

```bash
git add -f results/metrics.csv results/h1_events.csv results/*.png \
           results/supersessions_*.json
git add -f runs/            # optional: the raw per-seed logs (large)
git commit -m "Add <model> run outputs: metrics, H1 events, isolation scans"
```

Committing at least `results/metrics.csv` (plus the command in §6 that
produced it) is what makes the numbers verifiable — the open-science gap the
arXiv endorsement check flagged.
