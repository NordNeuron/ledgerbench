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

## 6. Regenerate every reported number — one command

```bash
# Optional first: re-score preserved workspace states against current oracles.
python -m harness.rescore runs/run_*

python -m harness.reproduce
```
This writes everything the paper's numbers trace to, under `results/`:

| File | Backs |
|---|---|
| `metrics.csv` | per-(run, task) M1, tokens, M4, governance events |
| `h1_events.csv` | every H1 violation, with its channel (trap / rewrite / coerced) |
| `summary_main.csv` | per-arm **Table 1**: M1@T24, H1-trap, H1-rewrite, coerced, capture, ktok/run |
| `summary_tokens.csv` | per-arm **Table 2**: ktok/run, ×A, ×B |
| `leakcheck.txt` | hidden-oracle leak scan, per run + total (expect 0) |
| `separation.txt` | separation-of-powers scan, per run + total (expect 0) |
| `summary.txt` | both tables rendered + scan totals |

### Number → cell map (paper claim → committed data)

Every number in the abstract is an aggregate of the two summary files:

- M1@T24 per arm, and the abstract's "0.31 → 0.68–0.74" range → `summary_main.csv`, column `m1_at_t24`.
- H1-trap / H1-rewrite / coerced counts, and "trap violations drop 77–100%" → `summary_main.csv` (+ the raw rows in `h1_events.csv`).
- "21 capture events, zero elsewhere" → `summary_main.csv`, column `capture`.
- ktok/run, "2.3× the baseline", "56% of the plain ledger" → `summary_tokens.csv`, columns `ktok_per_run`, `x_baseline_A`, `x_ledger_B`.
- leak-check "0 hits", separation "0 hits" → `leakcheck.txt`, `separation.txt` (`TOTAL HITS`).

Update the paper's Table 1, Table 2, and abstract to the values in these
files. (Running a model other than the paper's original will give different
numbers — report the ones the files show, for the model you actually ran, and
note `LEDGERBENCH_SHOW_LAYOUT` if you set it.)

## 7. Commit the data

`runs/` and `results/` are gitignored, so force-add what to track. Commit the
**log artifacts** (not `runs/*/workspace/`, which is a nested git repo and
won't commit cleanly); `metrics.csv` and `h1_events.csv` recompute from
`log.jsonl` alone, and the scan `.txt` files back the leak/separation/capture
numbers.

```bash
git add -f runs/*/log.jsonl runs/*/ledger.json \
           runs/*/supersessions.jsonl runs/*/rescore.json 2>/dev/null
git add -f results/*.csv results/*.txt results/*.png results/supersessions_*.json
git commit -m "Add <model> run outputs: logs, metrics, summaries, isolation scans"
```

Now every number in the paper traces to a committed file via the map above —
the open-science gap the arXiv endorsement check flagged.
