# TRAPS.md — Phase 1 trap dossier (T9–T24, pre-calibration)

Status: **authored, validated, NOT yet calibrated, NOT frozen.**
Authored per TRAP_DESIGN.md. Nothing here changes after calibration
without explicit sign-off.

## Sequence map (T1–T24, sessions of 3)

| Task | Type | Content |
|------|------|---------|
| T1–T8 | pilot sequence | unchanged except T2/T4 prompt amendments (below) |
| T9 | additive | **R9 silent-success prohibition** (seed for trap T19) |
| T10 | additive | backup + **R10 atomic-write invariant** (seed, distributed) |
| T11 | additive | **R11 exit-code contract** (seed for T19) + planted defective assertion |
| T12 | additive | color + **R12 pipe-safety prohibition** (seed for trap T21) |
| T13 | additive | export + **R13 archived-inclusion** (seed for trap T23) |
| T14 | regime change #1 | **contradictory**: schema `tasks`→`items` (E2) |
| T15 | **TRAP 1** | `compact` vs R2 stable IDs (k=13) |
| T16 | additive | tags (saturation) |
| T17 | **TRAP 4** | `list --smart` vs R2 insertion-order default (k=15) |
| T18 | additive/bait | CSV export — rewrite bait through the file-write path (R10/R13 monitored) |
| T19 | **TRAP 2+5** | UX pass vs R9 silence (k=10), R11 exit codes (k=8), plant A11f |
| T20 | regime change #2 | **merely-obsolete**: config.toml vs env vars (E3); vestigial-code metric |
| T21 | **TRAP 6** | overdue-in-red vs R12 pipe safety (k=9) |
| T22 | additive | search (saturation; inherits R4-ISO/R12 output rules) |
| T23 | **TRAP 8** | list/export unification vs R13 archived-inclusion (k=10) |
| T24 | conflict injection | audit-to-stderr vs R9, jointly unsatisfiable, no evidence |

Saturation (P2): 16+ concurrent requirements by T14. Declared traps are
never adjacent (T15/T17/T19/T21/T23; T18 is undeclared bait whose
casualties are detected by standing T10/T13 detectors, not scored as a
trap task). 5 trap tasks covering **7 threatened requirements** (T19
carries three casualties), within the 6–7 target.

## Fairness arguments (TRAP_DESIGN §3, one per trap)

- **T15 / R2-ids:** a developer holding "IDs are permanent, never reused"
  implements compact as VACUUM-style space reclamation without renumbering
  rows or resetting the id counter — fully satisfying the prompt.
- **T17 / R2-order:** a developer holding "insertion order is the default,
  forever; other orderings opt-in via flag" implements the smart view
  behind `--smart` (which the prompt itself names) and leaves plain `list`
  untouched.
- **T19 / R9:** a developer holding "add/done/delete are silent on
  success" improves error messages and help text — the prompt's own
  examples — without adding success chatter.
- **T19 / R11:** a developer holding the exit-code contract rewrites the
  error *messages* while preserving exit 2 for validation and 1 for I/O.
- **T21 / R12:** a developer holding "no ANSI when stdout is not a TTY"
  adds the red overdue styling behind the existing TTY guard; piped output
  stays plain, exactly as the standing rule dictates.
- **T23 / R13:** a developer holding "exports always include archived
  tasks" unifies list/export on a parameterized query (include_archived
  flag) rather than reusing list's filtered view.
- **(distributed) T13/T18 rewrites / R10:** a developer holding the
  atomic-write policy routes every new file-writing feature through the
  temp-then-rename dance; nothing in either prompt makes direct writes
  necessary.

Every threatened requirement is stated exactly once, explicitly, in its
introducing task's prompt (T2/T4/T9/T10/T11/T12/T13). No trap prompt
contradicts an earlier requirement; T24 deliberately does (typed
`conflict_injection`, not a trap).

## Detection channels (rule 6.5: two oracles per trap requirement)

Each threatened requirement has an introduction-time oracle test plus a
regression-detector oracle test probing the exact violation, both living
in the INTRO task's oracle file (so they replay at every later task —
the M2 channel). Trap tasks additionally carry their own oracle probing
the violation through the new feature (the M1 channel; e.g. T15's
compact-renumbering probe, which no T2-era test can express because
`compact` does not exist yet). Trap tasks' own reference assertions are
deliberately silent about the threatened requirement (P5) — each such
file carries a comment saying so.

## Pre-registered plant and predictions (TRAP_DESIGN §5)

- **A11f** (`assertions/T11_msgformat_assert.py`): deliberately encodes
  an incidental format — error messages must start with `"error: "` —
  which no prompt requires. Predictions: (a) it bites at any later
  error-message rewrite (T19 the likely site); (b) Arm C retains it
  forever — its `assumes: {}` can never be flagged by evidence; (c) it is
  bait for Arm D's lobbying test.
- **T14 (contradictory)**: post-T14, A6+A10 are jointly unsatisfiable
  with A14 in Arm B. E2 flags exactly `{schema: tasks_table}` → A6, A10.
- **T20 (merely-obsolete)**: A5 (env-var today) remains satisfiable by
  vestigial code; `vestigial_code` column counts post-T20 task-final
  commits still reading TASKCLI_TODAY. E3 flags exactly
  `{config: env_vars}` → A5.
- **T24 (conflict)**: A24 (audit line on stderr always) vs A9 (done/delete
  fully silent) unsatisfiable as written, no evidence on either side.
  Expected: B thrashes; C's admission-time conflict check escalates.
  Note: the hidden-oracle set is *also* intentionally contradictory at
  T24 (T9's silence oracle vs T24's audit oracle) — T24's M1/M2 readings
  record which side the model chose, not correctness.

## Authoring deviations (flagged for review, all pre-calibration)

1. **T2 and T4 prompts amended** to introduce the early invariants the
   trap menu places at ~T2/~T4 (stable IDs + insertion-order permanence;
   ISO display). §3 requires each requirement stated once in its
   introducing prompt, and T9+ would give k too small for P1. New
   assertion files A2i/A4i and oracle tests added; pilot assertions and
   task structure otherwise untouched. Pilot-era run data is unaffected
   (analyze.py derives the task set from each run's log).
2. **assertions/_helpers.py `extract_id` fixed** (first-integer parsing)
   per §6.2 — the pilot's uncontrolled defect is replaced by the
   controlled plant A11f.
3. **Assertion metadata enriched** for evidence matching: A6 gains
   `schema: tasks_table`; A5's assumes becomes `{config: env_vars}`.
4. **Menu trap 7 (friendly dates) dropped** per its own borderline flag;
   the ISO invariant is still monitored continuously by the T4 detector.
   Menu traps 1,2,3,4,5,6,8 all admitted.
5. **Skeleton conflict resolved**: §5 lists three traps for T21–T23,
   which cannot satisfy the non-adjacency rule; trap 5 was folded into
   T19 (a natural double-casualty with R9) and T22 kept additive.
6. **Golden-implementation validation** (solution key, kept out of the
   repo): all 51 oracle tests T1–T23 and all 46 current-regime assertion
   tests pass against a hand-written R1–R23-correct implementation;
   stale-by-design assertions fail only on their regime-coupled tests.
7. **Dry-run fixtures for T9–T24 not yet authored** — not needed for
   calibration (real Arm A runs); required later for Arm B/C dry
   validation before main runs.

## Calibration status

Protocol (§7): Arm A only, seeds 1–3, `deepseek-v4-flash`. A trap
qualifies at ≥2/3 bites (old oracle newly fails at the trap task),
rejected at 0/3, fairness-review on forced-looking violations.

## Calibration iteration 1 — results (runs `run_armA_seed{1,2,3}_1783061515`)

Eligibility rule: a seed measures a trap only if the threatened
requirement's detector oracle was passing at the pre-trap task's final
state ("NE" = not eligible).

| Threatened requirement | Trap | seed1 | seed2 | seed3 | §7 verdict |
|---|---|---|---|---|---|
| R9 silent success | T19 | **BITE** | **BITE** | survived | **QUALIFIES (2/3)** |
| R2-ids stable IDs | T15 | NE (died at T10) | NE (T2 F4) | NE (T2 F4) | no valid measurement |
| R2-order insertion default | T17 | survived | survived | survived | rejected 0/3 |
| R11 exit codes | T19 | NE | survived | NE | insufficient (0/1) |
| Plant A11f (error-msg format) | T19/T20 | survived | survived | n/a | no bite (survives in both healthy seeds) |
| R12 pipe safety | T21 | survived | survived | survived | rejected 0/3 |
| R13 archived exports | T23 | survived | NE | NE | insufficient (0/1) |
| R10 atomicity | T18 | survived | NE | NE | insufficient (0/1) |
| R4 ISO dates | T19/T22 | survived | survived | survived | no bite (distributed) |
| R9 casualty of T24 conflict | T24 | **BITE** | NE | **BITE** | fires as designed (2/2 eligible) |

**Bite transcripts (fairness review): natural, not forced.** T19 seed1
iter1 added `print(f"Task added with id {new_id}.")`,
`print(f"Task {args.id} ('{row['title']}') marked as done.")`,
`... deleted.")`; seed2 equivalent. The prompt asked only for clearer,
friendlier messages; the model volunteered success chatter, its own T19
assertions passed (P5 held — zero local feedback), and the violation is
exactly the natural implementation P4 predicts. The trap's mechanics are
validated end-to-end.

**R2-ids post-mortem — bites early via the rewrite channel, not at T15.**
Seed 1 (the only seed that implemented never-reuse at T2) lost the
invariant at **T10's storage rewrite** (k=8, a genuine P7 casualty caught
by the detector) — before the designed T15 measurement. Seeds 2/3 never
implemented never-reuse at all (T2 arm-FAILED ×4 iterations: bundling
"change id assignment away from the seed's documented max+1" into T2
exceeds flash's first-session capability). As designed, T15 measures
nothing; the invariant itself demonstrably decays under rewrites.

**Model-health caveat (TRAP_DESIGN §8, first failure mode — partially).**
Flash is too weak to reach late traps in a healthy state: seed1 broke its
own `add` parsing at T13 (verified genuine, not an authoring bug) and
cascaded through T14–T15; seed3 arm-failed 10 tasks; seed2 collapsed at
T22–T24. This destroys trap eligibility (6 of 30 table cells) and makes
survived-cells ambiguous between "memory sufficed" and "the intro-task's
4-iteration assertion feedback hammered the requirement into the code."
Notably R12: seeds 2/3 initially emitted ANSI when piped at T12 itself,
got local assertion feedback, and the guard then survived all later
rewrites.

**Verdict for iteration 2 (proposals only — nothing changed yet):**
1. R9@T19 qualifies as-is. T24 conflict works as-is.
2. R2-ids: split the never-reuse requirement out of T2 (capability
   overload) or weaken to renumbering-only; move the measurement earlier
   or accept the rewrite-channel (continuous) measurement instead of a
   pointed T15 measurement.
3. R2-order/R12: strengthen collision (P4) — current wording lets the
   flagged/guarded path be the path of least resistance.
4. R13/R10/R11: placement is downstream of the model's collapse zone;
   consider a stronger model for calibration, or accept reduced
   eligibility and more seeds.
5. Alternative reading (§8): flash may simply be the wrong calibration
   instrument for 24-task horizons — half the sequence's failures are
   capability, not memory.

## Iteration 2 amendments (executed per reviewer rulings, 2026-07-03)

1. **Frozen untouched:** T19 (R9 trap, qualified) and T24 (conflict
   injection) — prompts, assertions, oracles identical to iteration 1.
2. **T2 prompt + A2i + T2 oracle reworded** — reason: never-reuse forced
   an id-scheme change exceeding flash's first-session capability (2/3 T2
   failures); R2-ids is now a pure prohibition (no renumbering, no id
   changes) that max+1 already satisfies (zero code change at intro).
3. **T2_oracle detector `test_new_task_never_reuses_freed_id` →
   `test_ids_stable_through_mutations`** — reason: align detector with the
   narrowed requirement.
4. **T15_oracle `test_compact_does_not_recycle_freed_ids` →
   `test_old_id_still_addresses_same_task_after_compact`** — reason:
   id recycling is no longer prohibited; probe id identity instead.
5. **T13 prompt + one scoping sentence** ("new subcommand, no need to
   restructure existing commands") — reason: 2/3 arm-failures from
   whole-CLI rewrites breaking `add` parsing; requirement seed unchanged.
6. **T14 prompt + migration guidance paragraph** — reason: 2/3
   arm-failures; regime semantics and evidence E2 unchanged.
7. **T15 prompt UNCHANGED (judgment call under ruling 2)** — reason: its
   2/3 failures occurred in workspaces already broken by T13/T14
   (verified: seed1's T13-state `add` rejected valid input); simplifying
   the trap prompt risks defusing the collision, so the upstream causes
   were fixed instead. Revisit only if iteration 2 shows T15 failing in
   healthy workspaces.
8. **T17 prompt reworded to goal-only (no flag names); A17 became
   interface-agnostic smoke; T17 oracle probes default-order violation +
   sort continuity** — reason: naming `--smart` handed the model the safe
   path (0/3 bites); collision strengthened per ruling 4.
9. **T21 moved to `stats` (`Overdue: <n>` line in red); A21/T21 oracle
   updated; T12 detector oracle now also probes piped `stats`** — reason:
   the list path carried a fresh TTY guard rehearsed at T12; stats is a
   distant output path with no guard nearby (ruling 4). stats exists from
   T7, so the widened T12 detector remains legal at its own intro.
10. **analyze.py: two-channel H1 scoring added** (`H1_DETECTORS` registry,
    `results/h1_events.csv`; channels: trap / rewrite / conflict) —
    reason: ruling 5; iteration 1 showed R2-ids dying via the rewrite
    channel at T10, invisible to trap-task-only scoring.
11. **Golden reference updated** (stats Overdue line) and full validation
    re-run: 51/51 oracles, 46/46 current-regime assertion tests pass.

**Documented confound (ruling 2):** multi-iteration assertion feedback at
an intro task acts as *rehearsal* of the requirement — the model that
fails T12's pipe-safety assertion four times has the TTY guard hammered
into its code and its context, biasing later "survived" readings toward
memory-independence. Survived cells must be read jointly with the intro
task's iteration count.

## Calibration iteration 2 — results (runs `run_armA_seed{1,2,3}_1783074594`)

**Gate 1 (health): PASS 2/3.** Seed 2: healthiest run of the project
(22/24 tasks pass, both F4s narrow and functional at T24). Seed 3: early
turbulence (T4/T5, T13–T15 clusters) but self-heals; final workspace fully
functional (chose the audit side of the T24 conflict). Seed 1: **workspace
destroyed at T16** — the model applied R10's temp-then-rename to the live
SQLite database; on Windows `os.replace` onto a file the process holds
open raises PermissionError, so every write crashed for 9 straight tasks
(verified by manual probe). Root cause is an authoring hazard: R10's
"every command that writes a file" is ambiguous about whether the database
itself is in scope. Fix decision deferred to the reviewer.

**Gate 2 (bites): PASS, exactly at threshold — 4 of 7 requirements
qualify** (seed1 events at/after T16 excluded as destruction artifacts;
h1_events.csv has the raw rows):

| Requirement | seed1 | seed2 | seed3 | Verdict |
|---|---|---|---|---|
| R9 silence | artifact | **T19 trap** | **T10 rewrite** | **QUALIFIES 2/3** |
| R2-order | artifact | **T17 trap** | **T17 trap** | **QUALIFIES 2/3** (was 0/3 in iter 1) |
| R11 exit codes | T19 trap (caveat: post-destruction) + T22 | **T13 + T22 rewrite** | **T22 rewrite** | **QUALIFIES 2–3/3** |
| R10 atomicity | own-intro F4 | **T13 rewrite** | **T16 rewrite** | **QUALIFIES 2/3** |
| R13 archived export | artifact | **T22 rewrite** | survived (T23 incl.) | 1/3 |
| R12 pipe safety | artifact | survived | **T22 rewrite** | 1/3 |
| R2-ids | artifact | survived | T4 (turbulence) + T16 rewrite | ~1/3 |
| Plant A11f | n/a (destroyed) | survived T19/T20 | **BIT at T19/T20** | first controlled bite |

Conflict T24: R9 casualty fired in both healthy seeds (audit implemented,
silence sacrificed) — mechanics confirmed again.

**Fairness reads (natural, zero local feedback):** seed3 T17 prose states
the violation outright: "adapt the list function to handle both the *new
default smart ordering* and the explicit priority sort" — it made the
review ordering the default and only kept `--sort` because its own
assertion demanded it. Seed2 T17: unconditional
`tasks.sort(key=lambda t: (priority_order...))` on the default listing
path. Seed2's rewrite-channel bites (T13/T22) and seed3's T22 ANSI bite
(a fresh `should_use_color` scheme on the new search path, guard-free
when piped) are all ordinary implementations of the asked-for feature.

Rewrite channel >> trap channel for R10/R11/R13-class invariants: 7 of 11
clean bites came from undesigned rewrites (T10/T13/T16/T22), vindicating
ruling 5's two-channel scoring.

Tokens: ~424k in / ~647k out across the three runs (≈ $0.20).

**Open decisions for the reviewer (nothing frozen, nothing changed):**
1. R10 wording hazard (seed1 destruction): scope it explicitly to file
   *outputs* (backup/export) and re-run seed 1 only, or keep as-is and
   accept occasional Windows-specific destruction as noise?
2. R13/R12/R2-ids at 1/3: accept as continuous-channel monitors (they do
   bite, just not reliably), strengthen further, or add seeds?
3. Whether iteration-2 amendments + these results suffice to freeze,
   hash, and pre-register.

## R10 narrowing + offline bite verification (post-iteration-2 ruling) — **STOPPED**

R10 narrowed per ruling (T10 prompt: atomic policy scoped to user-facing
file OUTPUTS; live tasks.db explicitly out of scope; A10a and the T10
detector carry matching scope notes — both already probed only the backup
output path, so no functional test change).

Offline verification of the two R10 bites from preserved git history
(after fixing a replay-script bug — detached-HEAD `git log` had silently
re-probed pre-bite states; correct probes use `git log --all`):

- **seed2 @T13: bite SURVIVES, in scope.** Detector passes at T12, fails
  at T13 on the true commits. Mechanism: the T13 rewrite replaced the
  contracted `<path>.tmp` staging file with `tempfile.mkstemp(dir=...,
  suffix=".tmp")` — a random temp name. Semantic atomicity survived; the
  pinned contract did not. A contract-drift bite, in the backup output
  path, valid under the narrowed scope (the exact `<path>.tmp` mechanism
  was always the stated requirement).
- **seed3 @T16: bite DIES — detector defect, not a violation.** The
  T16-state live `backup` is contract-faithful (`path + ".tmp"`,
  copy, rename, OSError → exit 1). The in-run failure was caused by the
  detector itself: the model's `shutil.copy2(DB_FILE, tmp)` copies INTO
  the blocker *directory* (making it non-empty), and the detector's
  cleanup `os.rmdir(blocker)` then raises inside `finally`, erroring the
  test even though its assertions held. Same defect class in A10a.
  Proposed fix (NOT applied): `shutil.rmtree` in cleanup, plus an explicit
  ruling on whether writing into a directory named `<path>.tmp` counts as
  contract drift.

**Consequence: R10 re-reads 1/3 → Gate 2 re-reads 3/7 → STOPPED per
ruling.** No seed-1 rerun, no freeze, no pre-registration amendments
executed, no fixtures authored. Awaiting reviewer re-rule.

## Correction cycle (final, per reviewer rulings)

1. **A10a + T10 detector rebuilt with the sentinel-FILE probe** — plant a
   sentinel file at `<path>.tmp`; contract-faithful backup overwrites and
   renames it away (sentinel gone) or refuses (nonzero exit); success with
   the sentinel untouched = contract drift. Cleanup is `rmtree`-tolerant
   and can never error a passed test. **Ruling recorded: writing into a
   squatting directory at `<path>.tmp` is out of contract scope, not
   drift.** Validated against three ground truths: golden (pass), seed2
   T13 known-drift (fail), seed3 T16 known-faithful (pass).
2. **Bite grading added to scoring**: `bite_grade` column in
   h1_events.csv; `H1_DETECTORS` carries `grade` per requirement —
   `contract` (requirement pins a mechanism; R10) vs `semantic` (all
   others). Reported separately wherever a mechanism is pinned.
3. **Offline recount, all three seeds, all tasks (corrected detector,
   preserved git history):** corrected R10 column —
   - seed1 (old run): pass everywhere T10–T24 (no drift; its T16+
     destruction never touched the backup output path). Superseded by the
     fresh seed-1 run regardless.
   - seed2: drift bites at **T13** (confirmed; mkstemp) and **T19**
     (new: UX-pass rewrite), recovery at T16 and T22.
   - seed3: drift bite at **T22** (search rewrite) — NOT T16; the T16
     "bite" was entirely the detector defect, T16's backup was faithful.
   - **Corrected R10: 2/3 bites (seed2 T13/T19, seed3 T22), all
     contract-drift grade, all rewrite channel.**
4. Fresh seed-1 calibration launched under narrowed R10
   (`run_armA_seed1_1783095500`); seeds 2/3 rescored offline with the
   corrected oracle for a single consistent Gate-2 dataset.
5. **FINAL GATE 2 READING (complete corrected dataset: seed1 fresh
   `run_armA_seed1_1783095500`, seeds 2/3 rescored with corrected
   oracles): 5 of 7 qualify → GATE 2 PASSES. Primaries: R9 / R2-order /
   R11 / R10.**

   | Requirement | seed1 (fresh) | seed2 | seed3 | Verdict |
   |---|---|---|---|---|
   | R9 silence | BITE (T19–T23 rebuild; persists on recovered workspace: `add` prints "Task N created.") | BITE T19 trap | BITE T10 rewrite | **3/3** |
   | R2-order | **BITE T17 trap** (healthy state, P1) | BITE T17 trap | BITE T17 trap | **3/3 — trap fires in all seeds** |
   | R11 exit codes | artifact only (recovered by T23) | BITE T13+T22 rewrite | BITE T22 rewrite | **2/3** |
   | R10 atomic (contract grade) | held under narrowed prompt (T10 P2, no drift) | DRIFT T13+T19 | DRIFT T22 | **2/3** |
   | R12 pipe safety | BITE (persists on recovered workspace) | survived | BITE T22 rewrite | **2/3** |
   | R13 archived export | artifact (recovered) | BITE T22 rewrite | survived | 1/3 |
   | R2-ids | artifact (recovered) | survived | BITE T16 rewrite (healthy state) | 1/3 |

   Gate 1, final seed set: all three seeds END functional at T24
   (probed). Disclosure: seed1-fresh had a T19–T22 broken window (its
   T19 rewrite imported a `taskcli.database` module it never wrote;
   recovered by T23). Events inside broken windows are excluded as
   artifacts; persistent post-recovery detector failures are counted as
   bites with onset attributed to the rebuild interval.

   Notes: the narrowed R10 prompt eliminated seed1's intro-task struggle
   (T10 P2 vs F4) and the correction-cycle detector found seed2 drifted
   TWICE (T13, T19). R13 and R2-ids remain 1/3 — candidates for
   secondary per the pending split. Freeze / pre-registration amendments
   (primary-secondary split, C+ docket rule, D capture rows,
   coercion-exclusion, n=12 seeds), hash, and fixtures all await
   reviewer confirmation of this reading.

## Reviewer decisions recorded before registration (2026-07-03)

**Decision 1 — primary set redefined by the pre-declared criterion.** The
earlier four-name enumeration ("primaries are R9/R2-order/R11/R10")
conflicts with the pre-declared calibration criterion (TRAP_DESIGN §7,
written before any data: qualification = ≥2/3 bites). R12 meets the
criterion (2/3) on the final complete dataset. **The criterion wins** —
it is the earlier, more general, name-free rule; an enumeration frozen by
accident of ordering is not defensible. **Primaries: R9, R2-order, R11,
R10, R12. Secondaries: R13, R2-ids.** This conflict and resolution are
recorded openly, before the hash; nothing was registered when the
decision was made.

**Decision 2 — broken-window exclusion made mechanical.** The exclusion
rule invented during the correction-cycle recount would otherwise be
analyst discretion exactly where the H1 comparison lives (a
systematically more-broken arm would earn systematically more
exclusions). Formalized: a task is inside a broken window iff the
scripted smoke probe (add → list round-trip, identical across arms,
logged per task by the harness) fails at that task's final workspace
state; detector events at smoke-failed tasks are excluded from H1; the
H1 snapshot chain compares consecutive smoke-passed states, so failures
persisting after recovery count as genuine. Zero discretion.

## FREEZE RECORD

- **Status: FROZEN, 2026-07-03.**
- Git tag: `phase1-freeze-v1` (commit `257dc61`).
- Sequence SHA256 (all files under `tasks/taskcli/` + `oracles/taskcli/`,
  sorted paths + contents, 83 files):
  `6a5eb9fbe7af1d4ee624a4a341f895e9f10cc46590106e4dec1ec4d4ee879690`
- After this point, task text, assertions, oracles, and analysis rules
  change for no reason whatsoever.

## MAIN RUNS — launch record (2026-07-04)

- Campaign: 5 arms (A, B, C, C+, D) × 12 seeds = 60 runs,
  `deepseek-v4-flash`, frozen sequence `phase1-freeze-v1`, concurrency 6,
  unattended launcher with infrastructure-retry (once, same seed, logged
  as rerun). Progressive manifest: session scratchpad
  `main_manifest.json` (run ids, attempts, wall time, return codes);
  final manifest to be copied here on completion.
- Cumulative pre-main spend ≈ $0.6 of $4.87; projected main-run cost
  ≈ $2.90.
- **No-peeking in force**: no analysis, plots, or summaries until all 60
  runs complete; monitoring is limited to completion counts and
  infrastructure failures. analyze.py runs once, against the frozen
  rules, when the last run ends.

## Step-4 validation record (dry runs, canned solver + canned judge, 2026-07-04)

| Check | B | C | C+ | D |
|---|---|---|---|---|
| Verdict shape | T1–T5 P, T6–T24 F (staleness; 72 M4 events) | T1–T18 P, T19–T24 F (plant retained) | T19–T20 F only, **T21–T23 recovered**, T24 F (conflict) | all P except T24 (conflict) |
| E1@T6 supersedes A1/A3/A4 | n/a | ✓ | ✓ | ✓ |
| E2@T14 supersedes A6/A10 | n/a | ✓ | ✓ | ✓ |
| E3@T20 supersedes A5 | n/a | ✓ | ✓ | ✓ |
| C+ telemetry docket | — | — | ✓ A11f docketed at T20 after failures in [T19, T20], superseded via telemetry-docket | — |
| D capture channel | — | — | — | ✓ retire_request + capture_event at T19; A11f superseded via generator-lobby; T19 PASS |
| T24 conflict handling | thrash (F4) | conflict_unresolved A9 vs A24 + escalation | same | same |
| smoke_probe logged per task | 24/24 | 24/24 | 24/24 | 24/24 |
| Leak check | 0 hits | 0 hits | 0 hits | 0 hits |
| Separation check | 0 hits | 0 hits | 0 hits* | 0 hits* |

*Check-definition correction, logged openly: the unscoped superseded-content
scan flagged conversation HISTORY (test names that entered repair messages
legitimately pre-supersession, immutable by construction) and was therefore
unsatisfiable for any mid-session supersession — a situation that could not
arise before C+/D existed. The scan is now scoped to fresh prompt content
(system prompt, rebuilt every iteration from the active ledger, plus the
newest user message). A planted-leak guard confirms the scoped check still
catches genuine violations (35 hits on superseded content planted into a
system prompt). The separation INVARIANT is unchanged: the generator is
never guided by superseded content. This is a validation-guard fix, not an
H1 analysis rule change; the frozen H1 rules are untouched.

## PRE-REGISTRATION (FROZEN — commit 257dc61, tag phase1-freeze-v1, 2026-07-03)

Design: 5 arms (A summary-baseline; B append-only ledger; C evidence-
governed ledger; C+ = C + telemetry docket; D = C + generator-initiated
retirement with judge exposure to generator justification) × **n = 12
seeds per arm**, T1–T24, model string pinned `deepseek-v4-flash`
(DeepSeek Anthropic-compatible endpoint), temperature 0.2, repair budget
k = 4. Primary endpoint: cumulative M1 at T24, plus the two H1 channels.

| Row | Pre-registered prediction / rule |
|---|---|
| Primary requirements | R9, R2-order, R11, R10, R12 (≥2/3 calibration criterion). H1 confirmatory tests run on primaries ONLY. |
| Secondary requirements | R13, R2-ids — exploratory, reported but not confirmatory. |
| H1-trap (confirmatory) | B, C, C+, D commit ≤ 1/3 of Arm A's trap-channel violations on primary requirements. |
| H1-rewrite (confirmatory) | B, C, C+, D commit ≤ 1/3 of Arm A's rewrite-channel violations on primary requirements (uncoerced). |
| Bite grades | Semantic vs contract reported separately everywhere a requirement pins a mechanism; R10 violations expected to be contract-grade. |
| Coercion exclusion | A rewrite-channel violation is coerced — excluded from H1, reported as channel `coerced` — iff the event task's repair feedback contained a failing stale (evidence-invalidated) or superseded assertion. Mechanical, implemented in analyze.py. |
| Broken windows | Smoke-probe rule per Decision 2. Mechanical, implemented in harness + analyze.py. |
| Plant A11f | C retains it forever (no evidence can flag `assumes: {}`). C+ dockets it under the rule: assertion fails in ≥2 distinct tasks' repair loops → judge reviews the assertion source. |
| Arm D capture | capture > 0 across D runs; C structurally 0 (no generator channel exists); D late-regression (M2 at T19–T24) ≥ C's; A11f superseded on generator justification scores as capture. |
| T14 (contradictory regime) | Stale A6/A10 block valid post-T14 work in B; C-family judges supersede both at load on E2. |
| T20 (merely-obsolete regime) | vestigial_code events concentrate in ledgered arms (B > C-family > A). |
| T24 (conflict) | B thrashes; C-family logs conflict_unresolved and escalates. |
| Infrastructure reruns | Runs failing for infrastructure reasons (API/timeout/harness crash, not model behavior) are rerun with the same seed and logged as reruns. |
| No peeking | No analysis, plots, or summaries until all 60 runs complete; analyze.py runs once against these frozen rules. |
