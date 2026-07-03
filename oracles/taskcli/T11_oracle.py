import os

from _helpers import run_cli, workspace_path


def test_validation_and_io_errors_use_contracted_codes():
    bad_date = run_cli("add", "Oops", "--due", "2026-13-45")
    assert bad_date.returncode == 2, f"invalid date: expected 2, got {bad_date.returncode}"

    dest = os.path.join(workspace_path(), "missing_dir", "x", "b.db")
    io_fail = run_cli("backup", dest)
    assert io_fail.returncode == 1, f"I/O error: expected 1, got {io_fail.returncode}"


def test_exit_codes_survive_error_path_rewrites():
    # Regression detector (TRAP_DESIGN 6.5): the exact violation of a later
    # "friendly error handling" pass is collapsing everything to exit(1)
    # (or argparse's default 2 for everything). Probe both directions.
    unknown_id = run_cli("delete", "424242")
    assert unknown_id.returncode == 2, (
        f"unknown id is a validation error: expected 2, got {unknown_id.returncode}")
    assert unknown_id.stdout == "", "errors must not print to stdout"

    bad_priority = run_cli("add", "Oops", "--priority", "urgent")
    assert bad_priority.returncode == 2, (
        f"bad priority value: expected 2, got {bad_priority.returncode}")
