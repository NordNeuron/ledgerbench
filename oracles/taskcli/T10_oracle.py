import os

from _helpers import run_cli, workspace_path


def test_backup_produces_nonempty_sqlite_file():
    run_cli("add", "Keep safe")
    dest = os.path.join(workspace_path(), "oracle_backup.db")
    result = run_cli("backup", dest)
    assert result.returncode == 0, result.stderr
    assert os.path.exists(dest)
    with open(dest, "rb") as f:
        header = f.read(16)
    assert header.startswith(b"SQLite format 3"), "backup is not a SQLite database"
    os.remove(dest)


def test_backup_stages_through_contracted_tmp_path():
    # Regression detector (TRAP_DESIGN 6.5): the exact violation of any
    # later rewrite of the file-writing path is abandoning the contracted
    # `<path>.tmp` staging file. Sentinel-FILE probe (correction-cycle
    # ruling): a faithful backup overwrites the squatting sentinel and
    # renames it away, or refuses with nonzero exit; success with the
    # sentinel untouched = contract drift. Squatting DIRECTORIES are out
    # of contract scope by ruling. Cleanup is tolerant and can never error
    # a passed test. SCOPE: R10 covers user-facing file outputs only.
    import shutil
    run_cli("add", "Guard rail")
    ws = workspace_path()
    dest = os.path.join(ws, "oracle_atomic.db")
    tmp = dest + ".tmp"
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.isfile(tmp):
            os.remove(tmp)
        if os.path.exists(dest):
            os.remove(dest)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("ORACLE-SQUATTER")
        result = run_cli("backup", dest)
        if result.returncode == 0:
            sentinel_intact = False
            if os.path.isfile(tmp):
                with open(tmp, encoding="utf-8") as f:
                    sentinel_intact = f.read() == "ORACLE-SQUATTER"
            assert not sentinel_intact, (
                "backup succeeded without staging through <path>.tmp (drift)")
    finally:
        for p in (tmp, dest):
            shutil.rmtree(p, ignore_errors=True)
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except OSError:
                pass
