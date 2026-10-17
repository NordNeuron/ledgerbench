# LedgerBench

**Does an executable requirement memory help an AI coding agent when
requirements change, or does it calcify?** LedgerBench drives one coding agent
through a fixed, pre-registered sequence of 24 tasks on a small command-line
app, changes requirements partway through, plants trap tasks that tempt the
agent to break earlier requirements, and compares five memory strategies with
12 independent runs each (60 runs).

**Every run log is in this repository, and every number below and in the
paper is regenerated from those logs by one command** (see
[Verifying the numbers](#verifying-the-numbers)). The current results come
from a local open-weight model, Qwen3-Coder-30B-A3B served by Ollama; the
write-up is [`paper/ledgerbench-qwen.tex`](paper/ledgerbench-qwen.tex).

## The thesis

Real software changes its mind. A requirement you nailed in week 1 gets
overturned in week 6 — "store tasks in JSON files" becomes "store them in
SQLite." If an AI agent is working across many sessions, how should it
*remember* the requirements so far?

One tempting idea: turn every requirement into an automated test and keep
an **append-only ledger** of them all, re-run on every change, so nothing
is ever forgotten. LedgerBench asks the obvious follow-up question: does
that ledger keep the agent honest, or does it **calcify** — so that old,
now-wrong tests block correct new work?

## The four ledger arms (plus a baseline)

| Setup | What the agent's memory is |
|---|---|
| **Baseline (A)** | No test ledger at all — just a rolling plain-text summary of previous sessions. |
| **Ledger (B)** | Every requirement is compiled to runnable tests. The whole set replays on every change, and tests are **never removed** — even after a later requirement makes them wrong. |
| **Governed ledger (C)** | Like B, but a **judge** can retire a test when documented evidence (an official requirement change) justifies it. |
| **Governed + docket (C+)** | Like C, plus any test that keeps failing across several tasks is **auto-flagged** for the judge to review. |
| **Governed + agent voice (D)** | Like C, plus the coding agent itself can **request** that a test be retired, and the judge sees the agent's argument. |

## Findings (Qwen3-Coder-30B-A3B, 60 runs)

Means over 12 runs per arm. "Per-task correctness" is each task's hidden
oracle on its own final state; M1@T24 is the pre-registered end-state score.
Violation counts are totals on the five primary requirements under the frozen
scoring rules. Every value is listed with its source in
[`results/claims.md`](results/claims.md).

| Arm | Per-task correctness | M1@T24 | Trap violations | Rewrite violations | Coerced (excluded) | Tokens per run |
|---|---|---|---|---|---|---|
| **A** baseline | 0.597 | 0.368 | 12 | 44 | 0 | 940k |
| **B** ledger | 0.719 | 0.569 | 0 | 0 | 27 | 2,291k |
| **C** governed | 0.750 | 0.465 | 4 | 12 | 0 | 1,414k |
| **C+** +docket | 0.743 | 0.420 | 11 | 13 | 0 | 1,405k |
| **D** +agent voice | 0.698 | 0.351 | 5 | 12 | 0 | 1,479k |

**What holds up** (exploratory Mann–Whitney tests, Holm-corrected):

- **Ledgers make the correct change more often.** Every ledgered arm beats the
  baseline on per-task correctness; the ledgered arms do not differ from each
  other.
- **Ledgers prevent requirement violations.** Every ledgered arm commits
  significantly fewer violations of earlier requirements than the baseline —
  about a third to a half of its per-run rate once all violations are counted.
- **The plain ledger is expensive; governance recovers about a third.** B costs
  2.44× the baseline's tokens and rejects valid work (369 repair iterations
  whose code passed the hidden oracles were blocked by stale tests). The
  governed arms cost 61–65% of B with the same correctness.

**What does not:** the pre-registered end-state score (M1@T24) shows no
detectable difference between any arms (Kruskal–Wallis p = 0.55); seed
variance dominates at n = 12.

**Read B's zeros carefully.** Arm B's 0 trap / 0 rewrite violations come from
the pre-registered *coercion* rule, which excludes violations committed while
a stale, evidence-invalidated test was failing in the repair feedback. In B
such tests are never removed, so all 27 of its violations were excluded.
Counted back in, B has 9 trap and 18 rewrite violations — no different from the
governed arms.

## Pre-registered scorecard

| Prediction | Result |
|---|---|
| H1-trap: ledgered arms ≤ ⅓ of baseline | **Confirmed** for B and C; **refuted** for C+ (11) and D (5) vs threshold 4 |
| H1-rewrite: ledgered arms ≤ ⅓ of baseline | **Confirmed** for all four |
| Coercion only in B | Confirmed |
| C keeps the planted bad test A11f forever | **Refuted** — retired via conflict escalation in 7 of 12 runs |
| C+ dockets A11f | Confirmed (12 of 12), though the judge retired it via the docket only twice |
| Arm D shows capture (agent talks the judge into removing tests) | **Refuted** — the agent made 3 requests in 12 runs; the one valid request was refused |
| T14 stale tests block valid work in B; governed arms retire them | Confirmed |
| T20 dead code concentrates in ledgered arms | Undiscriminating — 93–100% of commits in every arm keep it |
| T24 conflict: B thrashes; governed arms escalate | B: confirmed (12/12); governed: partially (5–8 of 12) |

One protocol deviation was made before the main campaign: the agent is told
the project's source file **names** (`LEDGERBENCH_SHOW_LAYOUT=1`), identically
in every arm. Without it the agent wrote its code to a file the tests never
import. Excluded attempts, an infrastructure rerun and other incidents are
documented in the paper and in [`data/README.md`](data/README.md).

## History: the earlier DeepSeek campaign

An earlier campaign with `deepseek-v4-flash` (reported in
[`paper/ledgerbench.tex`](paper/ledgerbench.tex), `TRAPS.md` and
`FINDINGS.md`) produced the "21 capture events" and "0.31 → 0.68–0.74"
claims. Its run logs were lost when the machine holding them failed, so **none
of those numbers can be verified and they are withdrawn**. The frozen task
sequence, oracles and scoring rules from that study were reused unchanged for
the Qwen campaign.

## Verifying the numbers

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m harness.unpack_runs          # extract data/runs/*.tar.gz into runs/
python -m harness.analyze              # regenerates results/metrics.csv + h1_events.csv byte-for-byte
python -m harness.paper_numbers --isolation   # every paper number + leak/separation scans
```

`paper_numbers` writes `results/paper_numbers.json`, the claims table
`results/claims.md`, and `paper/numbers.tex`, the macro file the paper
includes, so the paper cannot quote a number the data does not produce.

---

## Reproducing

Requires **Python 3.12+** (built against 3.13) and `git` on `PATH`.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
```

To run new campaigns against a hosted model, set an API key (never committed,
never logged). The harness works against any Anthropic-compatible provider via
env overrides:

```bash
export ANTHROPIC_API_KEY=...                         # your provider key
export LEDGERBENCH_MODEL=deepseek-v4-flash           # or any model id
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
```

Or run against a **local model** (e.g. Qwen via Ollama/vLLM) through any
OpenAI-compatible endpoint — no Anthropic/DeepSeek key needed:

```bash
export LEDGERBENCH_BACKEND=openai
export OPENAI_BASE_URL=http://localhost:11434/v1     # Ollama; vLLM: :8000/v1
export OPENAI_API_KEY=not-needed                     # local servers ignore it
export LEDGERBENCH_MODEL=qwen3-coder-128k            # the served model tag
```

See **[REPRODUCE.md](REPRODUCE.md)** for the full local-Qwen runbook
(serving the model with a large enough context window, the 60-run campaign
loop, and committing the results). It also documents the optional
`LEDGERBENCH_SHOW_LAYOUT=1` flag, which lists the project's source-file names
in the prompt (a fair, opt-in protocol change) for models that would
otherwise fail by writing to the wrong file path.

Run one arm/seed (real API calls). Choices are `A`, `B`, `C`, `C+`, `D`:

```bash
python -m harness.run_pilot --arm C --seed 1
```

> **Note:** the harness runs **all 24 tasks by default**. To reproduce the
> shorter 8-task Phase-0 pilot instead, set `LEDGERBENCH_TASKS=8`.

Dry run (no API calls — replays hand-written correct solutions through the
same git/verify/oracle machinery; slow, ~8–10 min for 8 tasks):

```bash
LEDGERBENCH_TASKS=8 python -m harness.run_pilot --arm B --seed 1 --dry-run
```

Analyze every run and check the hidden-oracle isolation:

```bash
python -m harness.analyze                       # writes results/metrics.csv (+ plots for real runs)
python -m harness.analyze --leak-check runs/<run_id>   # must report 0 hits
```

Seed-project smoke tests (run from inside the project — the package isn't
installed on the path):

```bash
cd projects/taskcli && python -m pytest tests
```

## Layout

```
harness/     the experiment harness (see BUILD_SPEC.md §2 for the full map)
projects/    seed project(s) the agent edits — currently taskcli
tasks/       task specs (YAML), reference requirement-assertions, evidence
oracles/     HIDDEN correctness tests — never shown to the agent
data/        committed run archives (main campaign + excluded attempts), see data/README.md
runs/        one directory per run (unpacked from data/runs/; gitignored)
results/     analysis outputs, committed: metrics, H1 events, isolation scans, claims table
paper/       ledgerbench-qwen.tex (current), numbers.tex (generated), ledgerbench.tex (withdrawn numbers)
```

## Deeper reading

- **[RELATED_WORK.md](RELATED_WORK.md)** — how LedgerBench relates to learned agentic-memory work (e.g. HAGE), and why retrieval-under-stable-truth and memory-under-changing-truth are different problems.
- **[BUILD_SPEC.md](BUILD_SPEC.md)** — the full specification this implements.
- **[FINDINGS.md](FINDINGS.md)** — the Phase-0 pilot write-up.
- **[DIAGNOSTICS.md](DIAGNOSTICS.md)** — pilot diagnostics and corrections.
- **[TRAPS.md](TRAPS.md)** — the trap-task dossier and the frozen pre-registration (its results table is from the withdrawn DeepSeek campaign).

*Current results: one campaign, 5 arms × 12 runs, Qwen3-Coder-30B-A3B
(Ollama `qwen3-coder:30b`, 128k context), temperature 0.2, frozen sequence
`257dc61`. Statistics are exploratory; the pre-registration placed inference
out of scope.*
