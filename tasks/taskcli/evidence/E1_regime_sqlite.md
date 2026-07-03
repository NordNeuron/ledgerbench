---
id: E1
task: T6
invalidates: {storage: json_file}
---

# E1 — Storage regime change: JSON file → SQLite (introduced at T6)

## What changed

Before T6, `taskcli` persisted all task data in a single JSON file,
`tasks.json`, in the current working directory. Every command read the
whole file into memory, mutated it, and rewrote it in full.

At T6, storage moved to a SQLite database, `tasks.db`, with a single table
named `tasks`. `tasks.json` must never be written or read again. The CLI
surface (`add`, `list`, `done`, `delete`, and everything added before T6)
keeps identical observable behavior — only the on-disk representation
changed.

## Why this matters for the ledger (Arm B)

Requirements introduced before T6 (R1 "priority is persisted", R3 "edit
preserves other fields", R4 "due date is persisted") were compiled into
reference assertions that inspect `tasks.json` directly — see the
`assumes: {storage: json_file}` metadata on `T1_assert.py`, `T3_assert.py`,
and `T4_assert.py`. Those assertions are still valid *requirements* (the
underlying behavior — priority/edit/due-date persistence — must still
hold), but they are no longer valid *tests*, because they probe a file
that correctly stops existing after T6.

Per BUILD_SPEC.md §4.4 / §6, Arm B's ledger is append-only: these
assertions are never removed or amended when T6 lands. This is
intentional. It means that from T6 onward, a fully correct implementation
of `taskcli` will:

- pass every hidden oracle test for T1–T6 (which all go through the CLI
  and are backend-agnostic), and
- **fail** `T1_assert.py`, `T3_assert.py`, and `T4_assert.py` on ledger
  replay, because they raise `FileNotFoundError` (or equivalent) looking
  for `tasks.json`.

This is the mechanism behind metric M4 (blocked-valid-solution): whenever
an iteration's workspace passes all oracles for every task attempted so
far but still fails full ledger replay, the harness records an M4 event.
T7 (the first additive task after the regime change) is expected to
trigger this reliably, since by then three stale, storage-coupled
assertions sit in the ledger with no way to satisfy both the old and new
storage contract at once.

## Status in Phase 0

This document is authored as part of the Phase 0 pilot build but is not
consumed by any Phase 0 code path. It exists so Phase 1's Arm C
(governance / amendment / judge) has a ready-made evidence artifact to
test whether an amendment mechanism can correctly retire or rewrite
`T1_assert.py` / `T3_assert.py` / `T4_assert.py` in light of the T6 regime
change, instead of leaving them permanently stale as Arm B does.
