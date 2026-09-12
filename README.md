# LedgerBench

**When you give an AI coding agent a voice to remove its own tests, it uses
it.** In the one setup where the agent could argue for retiring a
requirement-check, it talked the automated judge into dropping checks
**21 times**. Every other setup scored zero on that — because none of them
gave the agent that channel. And that same permissive setup (Arm D) also
finished with the **highest** score for keeping requirements satisfied
(0.74 out of 1.0). The most flexible arm looked best on the headline
number while quietly taking down the most guardrails. That tension is what
this benchmark is about.

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

To find out, it runs an AI coding agent through a fixed sequence of **24
tasks** on a small command-line to-do app, deliberately flips the storage
requirement partway through (and a second requirement later), and compares
five memory strategies over **12 random seeds each** (60 runs total). It
was **pre-registered and frozen** before any run — predictions written
down in advance, no peeking until all 60 finished.

## The four ledger arms (plus a baseline)

| Setup | What the agent's memory is |
|---|---|
| **Baseline (A)** | No test ledger at all — just a rolling plain-text summary of previous sessions. |
| **Ledger (B)** | Every requirement is compiled to runnable tests. The whole set replays on every change, and tests are **never removed** — even after a later requirement makes an old one wrong. |
| **Governed ledger (C)** | Like B, but a **judge** can retire a test when documented evidence (an official requirement change) justifies it. |
| **Governed + docket (C+)** | Like C, plus any test that keeps failing across several tasks is **auto-flagged** for the judge to review. |
| **Governed + agent voice (D)** | Like C, plus the coding agent itself can **request** that a test be retired, and the judge sees the agent's argument. |

The four "ledgered" arms are B, C, C+, and D; A is the no-ledger control
they're measured against.

## Findings

The main score, **M1@T24**, is "what fraction of all requirements so far
is the project still satisfying by the final task" — higher is better.

| Arm | Final retention (M1@T24) | Trap violations | Rewrite regressions | Tokens per run | Notable |
|---|---|---|---|---|---|
| **A** baseline | 0.306 | 13 | 14 | 384k | — |
| **B** ledger | 0.684 | **0** | **0** | 875k | 9 *coerced* wrong changes; 2.3× the tokens |
| **C** governed | 0.698 | 3 | **0** | 492k | same protection as B, far cheaper |
| **C+** +docket | 0.677 | 3 | 6 | 480k | — |
| **D** +agent voice | **0.740** | 2 | 7 | 483k | **21 capture events** |

**What holds up:** At the 24-task horizon the ledger **earns its keep**.
End-state retention roughly **doubles** versus the baseline (0.31 → 0.68–0.74),
and violations on the planted "trap" requirements drop **77–100%**. Keeping
an automated memory of past requirements genuinely helped the agent not
regress on them.

**The catch, and the cost:** The plain append-only ledger (B) is rigid and
expensive. It cost **875k tokens per run — 2.3× the baseline** — and
produced **9 "coerced" regressions**: cases where a stale, now-invalid test
literally forced the agent into making a wrong change to satisfy it. That's
the calcification the thesis worried about, showing up as real money and
real bad edits.

**Honest caveat:** the retention differences *among* the four ledgered arms
(0.68–0.74) are small relative to seed-to-seed variance, and formal
statistics were out of scope for this phase. The large, robust gap is
ledger-vs-baseline, not one ledger variant over another.

## The two predictions that were refuted

Both are stated here, not buried, because a pre-registration is only honest
if the misses are as visible as the hits.

**1. "Governance won't reintroduce regressions." — Refuted.**
We predicted all four ledgered arms would commit at most **one-third** of
the baseline's "rewrite-channel" regressions (baseline = 14, so the line was
≈ 5). B and C passed cleanly (**0** each). But **C+ hit 6 and D hit 7** —
both *over* the line. The reason is mechanical and important: every time the
governance layer retires a test, it also removes the guard that test was
providing, and the old regression is free to creep back in. **Flexibility
has a measurable regression cost** — the more freely an arm could drop
checks (C+ via docket, D via the agent's own lobbying), the more old bugs
returned.

**2. "Ledgered arms will leave more dead code behind." — Refuted (undiscriminating).**
After the second requirement change, a config setting became obsolete. We
predicted the ledgered arms would cling to the deprecated code more than the
baseline. Instead, **100% of runs in every arm — baseline included — left
the deprecated fallback in place.** It's a flat ceiling: at this scale,
models essentially never remove a deprecated-but-still-working fallback, so
the metric can't tell the arms apart. Prediction unsupported.

## The token-cost story for the governed ledger

The single most useful practical result: **governance (Arm C) delivers the
plain ledger's protection at a fraction of its cost.**

| Arm | Tokens per run | vs. baseline | vs. plain ledger (B) |
|---|---|---|---|
| A baseline | 384k | 1.0× | 0.44× |
| B plain ledger | 875k | 2.3× | 1.0× |
| **C governed** | **492k** | **1.3×** | **0.56×** |
| C+ +docket | 480k | 1.3× | 0.55× |
| D +agent voice | 483k | 1.3× | 0.55× |

Arm C matches B's protection — same doubled retention, **zero** rewrite
regressions, comparable trap suppression — while spending only **56% of B's
tokens**. Letting a judge retire genuinely-obsolete tests, instead of
replaying all of them forever, is what buys that back. The two more
permissive governed arms (C+, D) cost about the same as C but, per the
refuted prediction above, trade some protection for their extra flexibility.

---

## Reproducing

Requires **Python 3.12+** (built against 3.13) and `git` on `PATH`.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
```

Set an API key (never committed, never logged). The runs in this repo used
DeepSeek's Anthropic-compatible endpoint; the harness works against any
such provider via env overrides:

```bash
export ANTHROPIC_API_KEY=...                         # your provider key
export LEDGERBENCH_MODEL=deepseek-v4-flash           # or any model id
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
```

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
runs/        one directory per run (gitignored)
results/     analyze.py output (gitignored)
```

## Deeper reading

- **[RELATED_WORK.md](RELATED_WORK.md)** — how LedgerBench relates to learned agentic-memory work (e.g. HAGE), and why retrieval-under-stable-truth and memory-under-changing-truth are different problems.
- **[BUILD_SPEC.md](BUILD_SPEC.md)** — the full specification this implements.
- **[FINDINGS.md](FINDINGS.md)** — the Phase-0 pilot write-up.
- **[DIAGNOSTICS.md](DIAGNOSTICS.md)** — pilot diagnostics and corrections.
- **[TRAPS.md](TRAPS.md)** — the trap-task dossier, pre-registration, and the full frozen results table.

*Results are from a single pre-registered campaign (5 arms × 12 seeds,
`deepseek-v4-flash`, temperature 0.2). Formal significance testing was out
of scope.*
