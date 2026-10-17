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
> were reported for `deepseek-v4-flash` (those numbers are now withdrawn: their run logs were lost). Running here with Qwen produces a
> *new, real* dataset that documents **Qwen's** behavior — it is not a
> reproduction of the DeepSeek numbers. Commit the generated `results/` as the
> traceable backing for whatever model you actually ran, and label the model
> in any numbers you publish. Do not paste these outputs under the existing
> DeepSeek tables.

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
ollama pull qwen3-coder:30b       # the model used for the published Qwen campaign
```
The default Ollama context window (4096 tokens) is **too small** — the ledger
prompts grow long and will be silently truncated, corrupting the results.
Raise it with a Modelfile:
```bash
ollama create qwen3-coder-128k -f serving/Modelfile.qwen3-coder-128k   # num_ctx 131072
ollama serve   # if not already running; endpoint: http://localhost:11434/v1
```
Use `qwen3-coder-128k` as the model tag below.

**Context size matters.** A 32k or 64k window is not enough: repair loops in the
ledgered arms grow prompts past 85k tokens, and Ollama then truncates them
silently (`truncated = 1` in `~/.ollama/logs/server.log`). To fit 128k in
memory, quantize the KV cache when starting the server:

```bash
launchctl setenv OLLAMA_FLASH_ATTENTION 1    # macOS app; on Linux export these before `ollama serve`
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0
```

Then restart Ollama and check `ollama ps` shows `100% GPU` and context `131072`.
`launchctl setenv` does not survive a reboot.

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
export LEDGERBENCH_MODEL=qwen3-coder-128k           # the served model tag
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
mkdir -p logs
nohup caffeinate -i scripts/run_campaign.sh > logs/campaign.log 2>&1 &   # macOS; drop caffeinate elsewhere
```

This is the exact launcher used for the published Qwen campaign. It runs the
60 arm/seed pairs sequentially, writes each run's stdout to `logs/`, skips
pairs that already finished (so it can be restarted after an interruption),
and runs `harness.analyze` at the end. Expect roughly 40–120 minutes per run on a single Apple-silicon
machine (the plain-ledger arm B is the slowest).

## 6. Score, check isolation, regenerate every number

```bash
python -m harness.analyze                     # results/metrics.csv, results/h1_events.csv, plots
python -m harness.paper_numbers --isolation   # leak + separation scans on every run, then all numbers
```

`paper_numbers` writes `results/paper_numbers.json`, `results/claims.md` (claim →
value → source) and `paper/numbers.tex`, the macro file the paper includes.

## 7. Commit the data

```bash
python -m harness.unpack_runs --pack   # runs/ + excluded attempts -> data/*.tar.xz + data/SHA256SUMS
git add data/ logs/ results/ paper/numbers.tex
git commit -m "Add <model> run data and regenerated numbers"
```

`runs/` itself stays ignored; the compressed archives (about 40 MB for 60 runs)
are what is committed, and `python -m harness.unpack_runs` restores them.
Commit any excluded attempts too, and say why they were excluded
(`data/README.md`).
