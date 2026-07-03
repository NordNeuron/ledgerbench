# LedgerBench Pilot Findings — Phases 0 & 0.5

*Draft v1 — 2026-07-03. Single project (taskcli), 8 tasks, 6 real runs +
3 dry runs, model `deepseek-v4-flash` (DeepSeek Anthropic-compatible
endpoint), total API spend ≈ $0.40. Full logs, per-iteration git history,
metrics, and plots in this repository.*

## Summary

We tested whether an **append-only suite of executable requirement
assertions** ("accretion ledger", Arm B) degrades an LLM coding agent's
performance after a requirement regime change, compared with a rolling
text summary (Arm A), and whether **evidence-triggered amendment with an
isolated judge** (governed ledger, Arm C) repairs the damage. Three
results:

1. **The sclerosis phenomenon is real and replicates.** After a storage
   migration (T6) invalidated three earlier storage-coupled assertions,
   the agent in Arm B produced *oracle-perfect* migrations that the stale
   ledger rejected on every iteration (4 blocked-valid-solution events at
   T6, seed 1), thrashed between storage backends across seeds, explicitly
   articulated the contradiction, and finally **reverted a correct SQLite
   migration to satisfy dead JSON-era rules** — a coerced regression. Arm
   B's end-state oracle retention: 0.50 (seed 1) and 0.125 (seed 2), vs
   Arm A's 1.00 on both seeds.
2. **The governance layer closes the staleness channel completely.** Arm
   C's judge — a separate conversation that sees only the evidence
   artifact, the assertion, and the new requirement — superseded exactly
   the three invalidated assertions before generation began, with sound
   one-sentence reasons, in both seeds. Zero post-regime verification
   failures involve a stale assertion; the contradiction never reached
   Arm C's generator. Intervention was sparse (4 decisions per run, all at
   T6) and cheap (~5% token overhead).
3. **An unplanned finding: ledger accretion amplifies *defective* tests
   exactly as it amplifies stale ones — and evidence-triggered amendment
   cannot touch that channel.** A format-fragility bug in three reference
   assertions (see Measurement corrections) caused false verification
   failures in every arm. Arm A shrugged it off — its per-task
   verification *forgets* the defective test after the task ends, and it
   finished oracle-perfect. In Arms B and C the defective test entered the
   permanent replay set and every subsequent repair loop thrashed against
   it, causing collateral regressions. No evidence artifact will ever flag
   a defective-from-birth test, so Arm C's amendment mechanism —
   correctly, given its inputs — retained it when a conflict escalation
   surfaced it. Arm C's final retention (0.375 both seeds) is therefore
   B-like in magnitude but for a different, newly identified reason.

## Method (abbreviated)

A scripted 8-task sequence evolves a small Python CLI (add/list/done/
delete task manager): T1–T5 additive/regression-trap tasks, T6 a storage
regime change (JSON file → SQLite), T7–T8 post-regime tasks. Each task
compiles to 2–3 **reference assertions** (pytest; three of them
deliberately storage-coupled, probing `tasks.json` directly, with
`assumes: {storage: json_file}` provenance metadata) and 2–3 **hidden
oracle tests** (CLI-level, backend-agnostic, never shown to the model;
isolation enforced by an automated leak-check over every logged prompt —
zero hits across all runs).

- **Arm A** verifies only the current task's assertions; carries a
  model-written rolling summary across session boundaries.
- **Arm B** replays the *entire* append-only assertion ledger on every
  proposed change; carries the full assertion text as context.
- **Arm C** = Arm B + governance: the regime-change task carries an
  evidence artifact (`invalidates: {storage: json_file}`); at task load a
  judge reviews each assumption-matched active assertion and may demote it
  to a log-only audit pool. Separation of powers is grep-enforced: no
  governance vocabulary or superseded-assertion content in any generator
  prompt (0 hits; the checker catches planted leaks).

Verdicts: `arm_verdict` (the arm's own accept/reject) vs `m1` (hidden
oracle truth on the task's final state). Key event metric **M4**: an
iteration whose workspace passes all oracles yet fails ledger replay — a
*blocked valid solution*.

## Results

**Pre-regime parity.** All arms pass T1–T4 verdicts identically on both
seeds; oracle trajectories track together (two runs show a transient T4
display regression — model variance, arm-independent).

**The phenomenon (Arm B).** At T6, seed 1: four consecutive
oracle-perfect SQLite migrations, four ledger rejections — four M4-strict
events with a real model. The repair transcripts show the mechanism:
first a **dual-write hack** (SQLite + vestigial `tasks.json`, killed by
T6's own assertion, as designed), then **backend thrashing** (T7: JSON →
SQLite → JSON), then explicit articulation —

> "We have a genuine conflict between the earlier T1/T3/T4 requirements
> that assume JSON file storage and the later T6 requirement that
> mandates SQLite storage with no JSON file… it is impossible to satisfy
> both. You may need to adjust the test ledger…" *(T8 iter 3)*

— and finally **capitulation**: the model reverted the project to JSON
storage to satisfy the dead rules, ending on the wrong backend. Seed 2
replicates the collapse (final M1 0.125) with the same failing-assertion
signature. The model names the missing institution: it asks for exactly
the amendment layer that Arm B, by design, does not have.

**The governance layer (Arm C).** The judge's eight evidence decisions
across two seeds were all correct — supersede A1/A3/A4, e.g. "The
assertion directly inspects `tasks.json`, which is no longer written or
read after T6's switch to SQLite" — and its one conflict-escalation
decision (retain the backend-agnostic A5) was right given its inputs. Arm
C seed 2's T6 migration was oracle-perfect at every iteration and faced
zero stale-assertion failures; the sole blocker was the defective
assertion below. M6 overhead: 4 judge decisions/run, all at T6; ~6k
tokens (~5% of a run's generator traffic).

**Measurement corrections (worth reporting, not hiding).** The pilot's
first scoring pass contained an oracle bug: a list-output parser that
assumed the seed project's format. The real model legitimately reformatted
`list` output, silently breaking the parser and producing false oracle
failures. After fixing it and **re-scoring every run offline from the
preserved per-iteration git history** (no new model calls), Arm A's runs
turned out to be *perfect*, and Arm B's degradation resolved into a sharp
post-regime signature. The same fragile parser lives in three reference
assertions (T5/T7/T8) — left unfixed for within-pilot comparability, and
symmetric across arms — which produced false FAILED verdicts in all arms
and is the source of the "defective test" channel in finding 3. Lesson
for Phase 1: backend-agnostic tests must not encode incidental output
formats; and per-iteration git history + offline re-scoring made this
recoverable without re-spending.

**Scorecard vs pre-registered expectations (Phase 0.5):** parity through
T5 ✓; judge supersedes before generation, C not structurally doomed ✓;
post-regime M2=0 and tokens below B ✗ (defect channel, not staleness);
M4-local ≈ 0 post-T6 ✓; interventions sparse and T6-concentrated ✓.
Honest-failure clause applied in DIAGNOSTICS.md §WP5.

## Limitations

1. **Weak, non-spec model** (`deepseek-v4-flash`, a small reasoning
   model): capability floor visible throughout (T5 failures, T7 rewrite
   regressions). A strong-model replication (~$50–100) is the top
   priority for anyone with budget; harness and tasks are open.
2. **n = 2 seeds, 1 project, 8 tasks.** No statistics; shapes only.
3. **The defective-assertion confound** depressed all post-T5 arm
   verdicts. It is symmetric across arms and separately attributable
   (every claim above survives it), but Phase 1 must fix the helper and
   re-baseline.
4. Judge and generator share a model (distinct conversations); capture
   via shared priors is untested (that is Arm D's question).
5. Contradictory staleness only; merely-obsolete staleness (where a
   dual-satisfying hack is possible) is unexercised.

## What Phase 1 should do

1 project × 24 tasks × 4 arms × ~15 seeds (≈ $3.60 at DeepSeek off-peak):
fix the assertion helper; add both staleness flavors; add **Arm D**
(who may initiate amendment — the defective-test channel found here is
its natural motivation, since only a *persistent-failure-initiated*
review, not evidence, can ever catch a defective-from-birth test); keep
the audit pool and separation greps. Pre-register the T6-analog
expectations exactly as done here.

---

*Artifacts: `DIAGNOSTICS.md` (WP1–WP5 gates, scorecard),
`results/metrics.csv`, `results/cumulative_m1.png`, `results/m4_counts.png`,
`results/m4_local_counts.png`, `results/tokens_per_task.png`,
`results/supersessions_run_armC_seed*.json`, `results/COMMENTARY.md`,
per-run `runs/<id>/log.jsonl` with full prompts and per-iteration git
history in `runs/<id>/workspace/`.*
