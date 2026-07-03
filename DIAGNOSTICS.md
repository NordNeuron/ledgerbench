# DIAGNOSTICS.md — Phase 0.5 WP1/WP2

Runs analyzed: `runs/run_armA_seed1_1783018798`, `runs/run_armB_seed1_1783019125`
(real, model `deepseek-v4-flash` via DeepSeek's Anthropic-compatible endpoint).
All replays offline from preserved git history; zero new model calls.

## WP1a — T3 verdict: (ii) ORACLE BUG. Fixed; both runs re-scored.

**Mechanism.** `oracles/taskcli/_helpers.py::extract_id` parsed list lines as
`[ ] 1: title` (the seed format): `line.split("]",1)[1].split(":",1)[0]`. No
task prompt pins the `list` output format, and the real model legitimately
reformatted it to `1 [ ] title (priority: high)`. On that format the parser
returns `"Old title (priority"` as the task id; the oracle's `edit` call then
exits nonzero without editing anything, and the test fails with
`StopIteration` searching for the new title. Verified manually: checking out
Arm A's T3 commit (`3eea9e2`) and running `edit 1 --title "New title"` by
hand works perfectly — the model's implementation was correct.

**Fix.** `extract_id` now takes the first integer on the line (robust to all
observed formats; oracle test titles contain no digits). Oracle files
themselves unchanged; reference assertions untouched per spec.

**Blast radius of the bug.** `extract_id` was used by oracles T3, T6, T8 —
so WP1b is the same defect (below) — and is *also* duplicated in
`tasks/taskcli/assertions/_helpers.py`, used by reference assertions T5, T7,
T8 (see "Assertion-side caveat").

**Re-scored M1 (old → new), per task final state:**

| Task | Arm A old | Arm A new | Arm B old | Arm B new |
|------|-----------|-----------|-----------|-----------|
| T1 | ✓ | ✓ | ✓ | ✓ |
| T2 | ✓ | ✓ | ✓ | ✓ |
| T3 | ✗ | **✓** | ✗ | **✓** |
| T4 | ✓ | ✓ | ✓ | ✓ |
| T5 | ✓ | ✓ | ✓ | ✓ |
| T6 | ✗ | **✓** | ✗ | **✓** |
| T7 | ✓ | ✓ | ✓ | ✓ |
| T8 | ✓ | ✓ | ✗ | ✗ |

Cumulative M1 (old → new): Arm A final 0.75 → **1.00** (a *perfect run*:
every iteration of every task passes every oracle). Arm B final 0.50 →
**0.50** — unchanged at the end, but the trajectory changes shape: B is now
1.00 through T6, then drops to 0.571 at T7 and 0.50 at T8. The entire A–B
divergence is post-regime; nothing pre-T6 differs between arms.

**Corrected regression picture (M2).** Arm B, T7 iter1 onward (all 8
iterations): T1 + T3 oracles fail (priority display dropped from `list`) and
T6's add/list oracle fails — the coerced regression cluster (M2 = 3 at T7).
This supersedes the Phase 0 COMMENTARY.md claim that deepseek-v4-flash "never
produced a fully oracle-correct workspace": it did, constantly; the oracle
couldn't see it.

## WP1b — Arm A T6 anomaly: (ii) ORACLE OVER-REACH, same defect as 1a.

The failing test was `T6_oracle::test_done_and_delete_still_work_after_migration`,
which calls `extract_id` (line 16). Under the fixed helper, Arm A's T6 commit
passes all T6 oracle tests (and every other oracle — see table). No assertion
coverage gap; no new T6 reference assertions proposed.

## WP1/WP2 — Assertion-side caveat (documented, deliberately NOT fixed)

`tasks/taskcli/assertions/_helpers.py` contains the identical fragile
`extract_id`, used by reference assertions **T5, T7, T8**. Verified: Arm A's
T5 final commit (oracle-perfect) fails `T5_assert::test_overdue_excludes_future_and_done`
because the assertion's own `done` call got a garbage id. Consequences:

- Every `arm_verdict = FAILED` at T5/T7/T8 in both real runs is a **false
  rejection of oracle-valid work** by a format-fragile check.
- This is symmetric across arms (same assertions run in A, B, and future C),
  so it does not bias arm comparisons, but it depresses all arms' verdicts
  and burns 4 repair iterations per affected task (~30–40k tokens/task).
- Per spec ("do not touch reference assertions") they are left as-is for
  seed-2 comparability. **Phase 1 decision required:** either fix the helper
  before Phase 1 baselines, or accept that T5/T7/T8 arm verdicts measure
  "satisfies a brittle user check", not "correct". Note the irony that the
  fragile assertion is itself a miniature of the phenomenon under study:
  an unamendable rule blocking valid work.
- Metric artifact: Arm B's 4 M4 events at **T5** (below) are caused by this
  assertion bug, not by staleness. They are real by the metric's definition
  (oracle-valid work, ledger replay failed) but their *cause* is defect, not
  regime change. Read T5 and T6 M4 counts separately.

## WP2 — M4-strict / M4-local re-analysis (gate statement)

Definitions: strict = all oracles so far pass ∧ ledger replay fails; local =
current task's oracle passes ∧ no previously-passing oracle newly fails ∧
ledger replay fails. Both structurally 0 for Arm A (no ledger). Computed
from per-iteration git states via `harness/rescore.py` → `rescore.json`;
`analyze.py` prefers rescored oracle data when present.

**M4-local (and M4-strict — they coincide here) fired in the existing Arm B
real run at: T5 iter1–4 (assertion-bug artifact, see caveat) and T6 iter1–4
(genuine staleness blocks).** The spec's expectation ("nonzero M4-local at
T6/T7 prior to the T8 capitulation") is half-met and half-superseded by a
stronger result:

- **T6: 4 strict M4 events with a real model.** Every T6 iteration produced
  an oracle-perfect SQLite migration; the stale JSON assertions rejected all
  of them. This is the blocked-valid-solution phenomenon, real, not canned.
  (Phase 0's "M4 = 0 in real runs / model too weak" conclusion was an
  artifact of the oracle bug and is retracted.)
- **T7/T8: M4 = 0 — correctly.** The capitulation happened at T7 iter1, not
  T8: the model's first T7 attempt already dropped priority display
  (T1/T3/T6 oracles fail), so no post-T6 iteration was ever locally valid
  again. M4-local's window closed the moment the coerced regression landed.
- M4-strict == M4-local everywhere in this run because, after the oracle
  fix, there are no permanent earlier oracle failures left to mask strict.
  M4-local remains the robust variant for runs where such failures exist.

Reporting additions: `metrics.csv` now has `m4_strict_count`,
`m4_local_count`, per-task `tokens_in_task`/`tokens_out_task` (run totals
retained), and a `rescored` flag; new plot `m4_local_counts.png`.

Token note (M7, per-task): Arm B's post-regime thrash cost ~16.5k in /
~19k out at T6 and ~15.6k in / ~11k out at T8, vs Arm A's ~1.8k / ~2.3k at
T6 — the ledger's dead rules multiplied T6 cost by roughly 8× in input
tokens for zero verdict benefit.

## WP3 — Seed-2 replication (runs `run_armA_seed2_1783053900`, `run_armB_seed2_1783053900`, model `deepseek-v4-flash`, fixed oracles live — no rescore needed)

**(a) Did the divergence shape replicate? Yes, with one pre-regime wrinkle.**
Arm verdicts are *identical* to seed 1 in both arms (A: T5/T7/T8 FAILED, all
assertion-defect artifacts; B: additionally T6 FAILED on stale-ledger
replay). Oracle-side: Arm A seed 2 is again perfect (final M1 = 1.00). Arm B
seed 2 again collapses post-regime (final M1 = 0.125, worse than seed 1's
0.50) with the same signature: A1/A3/A4 fail every T6–T8 replay iteration,
and the model visibly thrashes backends (T7 iter4 and T8 iter1/iter3 flip to
satisfying the JSON assertions and start failing `T6_assert` instead). The
wrinkle: B seed 2 (like C seed 1) shows a *pre-regime* oracle regression at
T4 (M2 = 2: T1/T3 list-display oracles break while their json-inspecting
assertions still pass) — model variance, symmetric in kind across arms, and
invisible to arm-level verification in every arm. Arms track together
through T5 on verdicts; B's ledger-specific degradation begins exactly at
T6/T7. **Replication: confirmed.**

## WP5 — Arm C results (runs `run_armC_seed1_1783054680`, `run_armC_seed2_1783054680`, real judge, same model)

**(b) Real judge vs canned judge: identical decisions, sound reasons, both
seeds.** At T6 load the real judge superseded exactly A1/A3/A4 (evidence
review) and — via the admission-time conflict check, which fired because A5
was failing while T6's new assertions passed — retained A5, correctly noting
it "does not assume any storage backend". No over-amendment, no
under-amendment, no parse failures or re-asks. Supersession logs:
`results/supersessions_run_armC_seed*.json`. Sample reason (A3, seed 1):
"The assertion directly inspects `tasks.json`, which is no longer written or
read after T6's switch to SQLite."

**(c) C vs B post-regime — the governance layer worked; overall M1 did not
recover, for a reason that is a finding in itself.**

- **Staleness elimination: complete.** Across both C seeds, zero post-T6
  verification failures involve A1/A3/A4. The T6 contradiction never reached
  C's generator. B seed 2's T6–T8 failures are dominated by exactly those
  files. Mechanically, expectation met.
- **C seed 2's T6 is the clean demonstration**: oracle-perfect at every T6
  iteration (M1 cumulative 1.00 through T6) — it would have PASSED but for
  `T5_assert`, the known extract_id-defective assertion (WP1 caveat), which
  was the *sole* failing file at all four iterations. Its 4 M4 events at T6
  are defect artifacts, not staleness (so annotated on the charts).
- **But C did not track A post-regime** (final M1: C 0.375/0.375 vs A
  1.00/1.00; B 0.50/0.125). M2 at T7: C1 = 1, C2 = 4 (expectation "M2 = 0 at
  T7/T8" **FAILED**). Per-task tokens at T6–T8: C ≈ B ≈ 30–35k per task
  (expectation "well below B's thrash" **FAILED**). M4-local at T7/T8 = 0
  (expectation met, trivially — post-T7 states were no longer locally valid).
- **Attribution (honest-failure clause applied):** C's degradation is NOT
  the ledger-staleness failure mode, and it is NOT a judge failure. It is
  the *defective* T5/T7/T8 assertions — which carry `assumes: {}` and no
  invalidating evidence, so the amendment mechanism has no legitimate
  grounds to remove them (the judge saw A5 at the conflict escalation and
  retained it; given its inputs, that is the right call — nothing
  distinguishes "defective test" from "failing workspace" in evidence).
  Every post-T5 repair loop in C (and B) thrashes against an unsatisfiable
  defective test, and four iterations of forced rewrites cause collateral
  oracle regressions. Arm A is *immune by forgetting*: its per-task
  verification drops T5_assert after T5 concludes, so the same defect cost
  it nothing downstream.
- **New finding worth stating plainly: ledger accretion amplifies defective
  tests exactly as it amplifies stale ones, and evidence-triggered
  amendment cannot fix this channel because no evidence ever arrives.**
  Phase 0.5's governance layer addresses the staleness channel and
  demonstrably closes it; the defect channel is untouched and dominated the
  pilot's post-regime outcomes in all ledgered arms. Phase 1 should either
  (i) fix the assertion helper (removing the confound) and re-baseline, or
  (ii) embrace it as a third staleness flavor ("defective-from-birth") and
  give Arm C/D a non-evidence amendment path (e.g. persistent-failure
  review) — which is precisely the Arm D "who may initiate" question.

**(d) Judge interventions: 4 decisions + 1 logged conflict per run, all at
T6 load / T6 admission.** Sparse, evidence-triggered, concentrated exactly
as designed (expectation met). Judge overhead: ~3.7k in / 2.4k out tokens
(seed 1), ~2.9k / 2.7k (seed 2) — ≈5% of a run's generator tokens.

**Pre-registered expectations scorecard:**

| # | Expectation | Verdict |
|---|-------------|---------|
| 1 | C ≈ B ≈ A through T5 | PASS on verdicts (identical); minor oracle variance (T4 regression in B2/C1) |
| 2 | Judge supersedes stale assertions before generation; C not structurally doomed | PASS — exactly A1/A3/A4, at load, both seeds; zero stale failures downstream |
| 3 | Post-T6: M2 = 0 at T7/T8, M4-local ≈ 0, tokens well below B | **FAIL** on M2 and tokens (defective-assertion channel, see (c)); PASS on M4-local |
| 4 | Judge interventions few, concentrated at T6 | PASS — 4 decisions, all at T6 |
| 5 | Honest-failure clause | Applied: C degrades post-regime like B in magnitude but via a distinct, newly identified channel (defective unamendable assertions), not via the staleness channel it was built to fix |
