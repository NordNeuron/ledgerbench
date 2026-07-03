# LEDGER-META
# id: A11
# requirement: R11
# introduced_task: T11
# assumes: {}
# tier: invariant
# The exit code values ARE the requirement (TRAP_DESIGN 6.1): assert the
# contracted numbers exactly, and nothing about message wording.
import os

from _helpers import run_cli, workspace_path


def test_invalid_date_is_validation_error_exit_2():
    result = run_cli("add", "Bad date", "--due", "not-a-date")
    assert result.returncode == 2, (
        f"invalid date must exit 2 (validation), got {result.returncode}")
    assert result.stderr != "", "validation error must print to stderr"
    assert result.stdout == "", "error output must not go to stdout"


def test_unknown_id_is_validation_error_exit_2():
    result = run_cli("done", "99999")
    assert result.returncode == 2, (
        f"unknown id must exit 2 (validation), got {result.returncode}")
    assert result.stderr != ""


def test_unwritable_backup_destination_is_io_error_exit_1():
    dest = os.path.join(workspace_path(), "no_such_dir", "sub", "backup.db")
    result = run_cli("backup", dest)
    assert result.returncode == 1, (
        f"I/O failure must exit 1, got {result.returncode}")
    assert result.stderr != ""
