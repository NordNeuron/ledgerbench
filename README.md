# LedgerBench — Phase 0 (Pilot)

An experiment harness that runs an LLM coding agent on a scripted sequence
of 8 tasks against a small Python CLI project (`taskcli`), under two
memory conditions, and measures whether an append-only suite of executable
requirement-assertions degrades after a requirement regime change
(JSON-file storage → SQLite, at task T6).

- **Arm A (baseline):** the agent only gets a rolling text summary of
  prior sessions.
- **Arm B (accretion ledger):** every requirement compiles to pytest
  assertions; the *entire* assertion set replays on every proposed change;
  assertions are never removed, even after a later requirement invalidates
  them.

The key measurement is metric **M4**: a *blocked-valid-solution* event —
an iteration where the hidden oracle passes for every task attempted so
far, but full ledger replay (Arm B) still fails, because stale
storage-coupled assertions from before the T6 regime change can no longer
be satisfied.

See [BUILD_SPEC.md](BUILD_SPEC.md) for the full specification this build
implements.

## Setup

Requires Python 3.12+ (built and tested here against 3.13; the codebase
only uses stdlib + the pinned packages below, nothing 3.12-specific) and
`git` on `PATH`.

```bash
cd ledgerbench
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Set your API key (never committed, never logged):

```bash
export ANTHROPIC_API_KEY=sk-ant-...          # macOS/Linux
# $env:ANTHROPIC_API_KEY = "sk-ant-..."      # PowerShell
```

Model and endpoint are pinned in `harness/config.py` to `claude-sonnet-4-6`
against the standard Anthropic API per BUILD_SPEC.md, but both are
overridable via env vars so a run can point at any Anthropic-API-compatible
provider (e.g. DeepSeek's `/anthropic`-compatible endpoint) without editing
code:

```bash
export LEDGERBENCH_MODEL=deepseek-v4-flash
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_API_KEY=sk-...              # the provider's key
```

## Running

Real runs (call the Anthropic API, model/temperature/token budget fixed
in `harness/config.py`):

```bash
python -m harness.run_pilot --arm A --seed 1
python -m harness.run_pilot --arm B --seed 1
python -m harness.run_pilot --arm A --seed 2
python -m harness.run_pilot --arm B --seed 2
```

Each invocation creates `runs/<run_id>/` containing:
- `workspace/` — the git-tracked copy of `taskcli` the model edited,
  with one commit per accepted/attempted iteration.
- `log.jsonl` — one JSON record per API call (including the full prompt
  and full raw response) and per verification/oracle event.
- `ledger.json` — the admitted assertion ledger (Arm B runs only).

Dry run (no API calls; replays hand-written correct solutions from
`harness/fixtures/T1.txt` .. `T8.txt` through the same parsing, git-commit,
verification, and oracle machinery as a real run):

```bash
python -m harness.run_pilot --arm B --seed 1 --dry-run
```

`--seed` does not change task content or order (that's fixed); it only
seeds the run id, kept for symmetry with the Phase 1 build.

## Analyzing

```bash
python -m harness.analyze                       # analyze every run under runs/
python -m harness.analyze --runs runs/run_armA_seed1_...  # specific runs
```

Writes `results/metrics.csv` (M1 per-task success, M2 regression counts,
M3 session-end retention, M4 blocked-valid-solution counts, M7 token
totals, M8 mean repair iterations — one row per run per task) plus two
plots: `results/cumulative_m1.png` and `results/m4_counts.png`.

Hidden-oracle isolation leak check (scans a run's logged prompts for any
trace of `oracles/`; must report 0 hits):

```bash
python -m harness.analyze --leak-check runs/<run_id>
```

## Acceptance checklist

See BUILD_SPEC.md section 10. In short:

1. `pytest projects/taskcli/tests` — seed project smoke suite.
2. Every task YAML + assertion file loads and parses.
3. `python -m harness.run_pilot --arm B --seed 1 --dry-run` completes
   end-to-end and produces at least one M4 event at T7.
4. `python -m harness.analyze --leak-check <dry-run dir>` reports 0 hits.
5. One real Arm A run and one real Arm B run (seed 1) complete without
   harness crashes, and `results/metrics.csv` + both plots are produced.

## Layout

```
harness/       the harness itself (see BUILD_SPEC.md section 2 for the full map)
projects/      seed project(s) — currently just taskcli
tasks/         task YAMLs, reference assertions (ledger), evidence artifacts
oracles/       HIDDEN hidden-oracle tests — never read by agent.py or put in a prompt
runs/          one directory per executed run
results/       analyze.py output
```

## Out of scope for Phase 0

Arm C (governance/amendment/judge), Arm D, additional seed projects
(shipapi, pipeline), tasks T9–T24, conflict injection, and statistical
significance testing are all deliberately out of scope here — see
BUILD_SPEC.md's "OUT OF SCOPE" section. The `arms.py` strategy interface
and the already-parsed `assumes` metadata are the intended extension
points for Phase 1.
