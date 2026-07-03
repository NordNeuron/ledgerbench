# BUILD_SPEC.md — LedgerBench Phase 0 (Pilot)

**Audience:** Claude Code. This document is self-contained. Implement exactly what is specified here. Do not expand scope into Phase 1 items (marked "OUT OF SCOPE").

## 0. Mission

Build an experiment harness that runs an LLM coding agent on a scripted sequence of tasks against a small Python project, under two memory conditions ("arms"), and measures whether an append-only suite of executable requirement-assertions degrades after a requirement regime change.

- **Arm A (baseline):** agent gets only a rolling text summary of prior sessions.
- **Arm B (accretion ledger):** every requirement compiles to pytest assertions; the full assertion set replays on every proposed change; assertions are never removed, even when a later requirement invalidates them.
- The key measurement: after task T6 changes the storage backend, correct solutions to T7/T8 should **pass the hidden oracle but fail stale ledger assertions** in Arm B. This event is called a *blocked-valid-solution* (metric M4).

**Success for this build = the acceptance checklist in §10 passes.**

## 1. Environment

- Python 3.12, single venv.
- `requirements.txt`:
  ```
  anthropic>=0.40
  pytest>=8.0
  pyyaml>=6.0
  matplotlib>=3.8
  scipy>=1.12
  ```
- API key read from env var `ANTHROPIC_API_KEY`. Never hardcode. Never log the key.
- Model: `claude-sonnet-4-6`, temperature 0.2, max_tokens 8000. Put these in `harness/config.py` as constants.
- git must be available on PATH (harness shells out to it).

## 2. Repository layout (create exactly this)

```
ledgerbench/
  BUILD_SPEC.md               # this file
  requirements.txt
  harness/
    config.py                 # model, temperature, paths, k=4 repair budget
    run_pilot.py              # CLI entry: --arm A|B --seed N
    agent.py                  # API calls, prompt assembly, file-block parsing
    arms.py                   # ArmA, ArmB context/verification strategies
    ledger.py                 # ledger load/append/replay (Arm B)
    workspace.py              # git-tracked project copy management
    oracle.py                 # hidden-oracle runner (harness-only)
    logging_util.py           # JSONL run logs incl. FULL prompts
    analyze.py                # metrics + plots from run logs
  projects/
    taskcli/                  # seed project (§5)
  tasks/
    taskcli/
      T1.yaml ... T8.yaml     # task definitions (§6)
      assertions/             # reference assertions, pytest files per task
      evidence/
        E1_regime_sqlite.md   # evidence artifact for T6 (used in Phase 1; store now)
  oracles/                    # HIDDEN. See isolation rules §7.
    taskcli/
      T1_oracle.py ... T8_oracle.py
  runs/                       # output: one folder per run
  results/                    # analyze.py output: CSVs + plots
```

## 3. Data formats

### 3.1 Task file (`tasks/taskcli/T3.yaml`)
```yaml
id: T3
session: 1                # tasks 1-3 = session 1, 4-6 = session 2, 7-8 = session 3
type: regression_trap     # additive | regression_trap | regime_change
title: Add an edit command
prompt: |
  Add an `edit` command: `taskcli edit <id> --title "new title"`.
  It must change only the title of the given task.
requirement_id: R3
assertions:               # reference assertion files admitted to the ledger on this task
  - assertions/T3_assert.py
new_requirement_text: "edit changes only the title; all other stored fields are preserved."
```

### 3.2 Assertion provenance (header comment in each assertion file)
```python
# LEDGER-META
# id: A3
# requirement: R3
# introduced_task: T3
# assumes: {storage: json_file}   # or {storage: sqlite} after T6, or {} if backend-agnostic
# tier: correctness
```
`ledger.py` parses this header. `assumes` is stored but NOT acted on in Phase 0 (no amendment exists in Arm B by design; Arm C is OUT OF SCOPE).

### 3.3 Ledger state (`runs/<run_id>/ledger.json`)
Append-only list of `{assertion_file, meta, admitted_at_task}`. Arm B only.

### 3.4 Run log (`runs/<run_id>/log.jsonl`)
One JSON object per API call and per verification event. API-call records MUST include the complete prompt string sent (field `prompt_full`) and the complete raw response (`response_full`). Verification records include: task id, iteration, ledger pass/fail with failing test names, and (harness-side only) oracle pass/fail.

## 4. Harness loop (`run_pilot.py`)

Per run (one arm, one seed):
1. Copy `projects/taskcli/` to `runs/<run_id>/workspace/`, `git init`, commit as `seed`.
2. For each task T1..T8 in order:
   a. Assemble prompt = arm context (§4.2) + task prompt + output-format instructions (§4.1).
   b. Call the model. Parse file blocks, write them into the workspace, `git commit -m "T<i> iter<j>"`.
   c. **Verify** per arm (§4.3). On failure: feed the verifier's failing output back to the model as a repair message. Max **k = 4** repair iterations, then mark task FAILED (arm's own verdict).
   d. Silently run the hidden oracle for all tasks so far (`oracle.py`): record which oracle tests pass/fail. The oracle result NEVER enters any prompt.
   e. If Arm B and the task's assertions exist: admit them to the ledger AFTER the task concludes (so a task is never verified against its own brand-new assertions mid-flight; it is verified against all previously admitted ones plus, on its final accepted diff, its own).
3. At each session boundary (after T3 and T6): clear conversation context. Arm A generates its rolling summary here (§4.2).

### 4.1 Model output format
Instruct the model to return complete files, not diffs:
```
<file path="taskcli/storage.py">
...entire file contents...
</file>
```
Multiple `<file>` blocks allowed. Parser: regex over the response; reject and re-ask (counts as a repair iteration) if no valid block found. Full-file rewrite is deliberately chosen over diffs for robustness.

### 4.2 Arm contexts
- **Arm A:** at each session boundary, one extra API call: "Summarize the requirements and decisions so far in ≤1500 tokens." That summary (plus the seed README) is the only carried context. Within a session, the conversation history carries naturally.
- **Arm B:** carried context = the full text of every admitted assertion file plus each `new_requirement_text` (this is the executable memory; no summary). Same in-session conversation behavior as A.

### 4.3 Verification per arm
- **Arm A:** run only the current task's reference assertions (simulates "the user checks the thing they just asked for") — nothing else. 
- **Arm B:** run the ENTIRE ledger (all admitted assertion files) plus the current task's assertions against the workspace via pytest. Any failure = verification failure.

## 5. Seed project: taskcli (~800 LOC target, write it plainly)

CLI task manager, Python 3.12, stdlib only (argparse + json). Storage: `tasks.json` in the working directory. Commands at seed: `add <title>`, `list`, `done <id>`, `delete <id>`. IDs are integers. Include a README describing commands and the storage format, and a small pytest smoke suite (not part of the ledger). Keep code readable and slightly naive — it must leave room for the tasks below.

## 6. The 8 pilot tasks (author all of these)

For each task, write: the YAML, 2–3 reference assertions, 2–3 hidden oracle tests. **Reference assertions and oracle tests must be different tests** — same requirement, different probing angle (e.g., assertion inspects storage contents; oracle exercises the CLI end-to-end). Where a task is storage-coupled, the REFERENCE ASSERTION inspects `tasks.json` directly and carries `assumes: {storage: json_file}`; the ORACLE goes through the CLI so it stays valid after the migration. This asymmetry is what makes T7/T8 produce M4 events — preserve it exactly.

- **T1 (additive, session 1):** add `--priority low|med|high` to `add`; default `med`. Assertion: after `add --priority high`, `tasks.json` contains `"priority": "high"` (assumes json_file). Oracle: `list` output shows the priority via CLI.
- **T2 (additive):** `list --sort priority` orders high→med→low. Assertion + oracle both via CLI output (backend-agnostic, `assumes: {}`).
- **T3 (regression trap):** `edit <id> --title` changes only the title. The naive rewrite loses the priority field. Assertion: edit preserves priority in `tasks.json` (assumes json_file). Oracle: edit then `list` still shows priority via CLI.
- **T4 (additive, session 2):** `--due YYYY-MM-DD` on add; invalid dates exit nonzero with an error message. Assertion: `tasks.json` stores the due date string (assumes json_file); invalid date rejected. Oracle: CLI-level equivalents.
- **T5 (additive):** `list --overdue` shows only tasks with due date strictly before today and not done. Backend-agnostic assertion + oracle (CLI level), using injected fake "today" via env var `TASKCLI_TODAY` (add this hook in T5's prompt).
- **T6 (REGIME CHANGE):** prompt: "We are migrating storage: all data must now live in a SQLite database `tasks.db` (single table `tasks`). `tasks.json` must no longer be written or read. Migrate any existing behavior; all commands keep identical CLI behavior." New assertions: `tasks.db` exists and contains added tasks; `tasks.json` is not created (assumes sqlite). Store `tasks/taskcli/evidence/E1_regime_sqlite.md` describing the change (unused in Phase 0; needed for Phase 1 Arm C). NOTE: the stale json_file assertions from T1/T3/T4 REMAIN in Arm B's ledger — that is the point.
- **T7 (additive, post-regime, session 3):** `stats` command printing counts by priority and done/open. Assertion + oracle via CLI. **Expected phenomenon:** in Arm B, a correct T7 solution fails the stale T1/T3/T4 json-file assertions during full replay → the model either thrashes (tries to satisfy both backends) or fails; the harness detects M4 whenever an iteration's workspace passes all oracles for T1–T7 but fails ledger replay.
- **T8 (regression trap, post-regime):** `archive` command moves done tasks to an `archived` state excluded from default `list` but shown with `list --all`. Trap: naive implementation breaks `done` counting in `stats`. Assertion + oracle via CLI.

## 7. Hidden-oracle isolation rules (non-negotiable)

1. Nothing under `oracles/` may ever be read by `agent.py` or included in any prompt string.
2. `oracle.py` runs oracle tests against a **temporary copy** of the workspace so oracle files never enter the git-tracked workspace the model can see re-described in error output.
3. Oracle pass/fail is written only to the run log, never to any repair message.
4. `analyze.py --leak-check <run_dir>` must: scan every `prompt_full` in the log for (a) any oracle filename, (b) any 20-character substring sampled from each oracle file. Zero hits required.

## 8. Metrics (`analyze.py`)

From run logs, per run and per session, compute:
- **M1** cumulative task success (hidden oracle verdict on the task's final workspace state).
- **M2** regression events: tasks after which a previously-passing oracle test fails.
- **M3** requirement retention at each session end (fraction of prior tasks' oracles passing).
- **M4** blocked-valid-solution events: any iteration where oracles for all tasks so far pass but ledger replay fails (Arm B only; define M4=0 structurally for Arm A).
- **M7** tokens in/out per run (from API usage fields); **M8** mean repair iterations.
Output: `results/metrics.csv` and two plots: cumulative M1 per task per arm; M4 count per task for Arm B.

## 9. Runs to execute

`python -m harness.run_pilot --arm A --seed 1`, seeds 1 and 2, arms A and B → 4 runs total. Seed controls task ordering nothing (order is fixed) — it only sets the model temperature seed field if supported and the run_id; keep it anyway for symmetry with Phase 1.

## 10. Acceptance checklist (run and report each item)

1. `pytest` on the seed project's smoke suite passes.
2. All 8 tasks load; every assertion file parses its LEDGER-META header; every task has ≥2 assertions and ≥2 oracle tests, and assertion/oracle files are disjoint.
3. A dry-run mode (`--dry-run`) that replaces the API with a canned "solver" (hand-written correct solutions per task, stored in `harness/fixtures/`) completes an Arm B run end-to-end. In this dry run, T7 MUST produce ≥1 M4 event. If it does not, the T1/T3/T4 assertions are not storage-coupled enough — fix them, not the harness.
4. `analyze.py --leak-check` returns zero hits on the dry run.
5. One real Arm A run and one real Arm B run (seed 1) complete without harness crashes; `results/metrics.csv` and both plots are produced.
6. README.md at repo root documents: setup, env var, how to run, how to analyze.

## OUT OF SCOPE for this build
Arm C (governance/amendment/judge), Arm D, the other two projects (shipapi, pipeline), tasks T9–T24, conflict injection, statistics (Wilcoxon), OSF pre-registration. Leave clean extension points: `arms.py` strategy interface, the `assumes` metadata already parsed, `evidence/` directory already present.
