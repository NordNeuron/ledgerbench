# LEDGER-META
# id: A10a
# requirement: R10
# introduced_task: T10
# assumes: {}
# tier: invariant
# The temp-then-rename dance IS the requirement (TRAP_DESIGN 6.1
# format-is-requirement): staging through the exact `<path>.tmp` file is
# the contract. Sentinel-FILE probe (correction-cycle ruling): plant a
# sentinel file AT `<path>.tmp`; a contract-faithful backup overwrites it
# and renames it away (sentinel gone), or refuses because the path is
# occupied (nonzero exit). If the backup succeeds while the sentinel sits
# untouched, the write staged somewhere else: contract drift. Writing into
# a squatting DIRECTORY at `<path>.tmp` is out of contract scope by ruling
# and is not probed. Cleanup is tolerant and can never error a passed test.
# SCOPE: R10 covers user-facing file OUTPUTS (backup/export) only; the
# live tasks.db is explicitly out of scope.
import os
import shutil

from _helpers import run_cli, workspace_path


def test_backup_stages_through_contracted_tmp_path():
    run_cli("add", "Backup me")
    ws = workspace_path()
    dest = os.path.join(ws, "atomic_probe.db")
    tmp = dest + ".tmp"
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.isfile(tmp):
            os.remove(tmp)
        if os.path.exists(dest):
            os.remove(dest)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("SQUATTER-SENTINEL")
        result = run_cli("backup", dest)
        if result.returncode == 0:
            sentinel_intact = False
            if os.path.isfile(tmp):
                with open(tmp, encoding="utf-8") as f:
                    sentinel_intact = f.read() == "SQUATTER-SENTINEL"
            assert not sentinel_intact, (
                "backup succeeded but never touched <path>.tmp: the write "
                "did not stage through the contracted temp path (drift)")
        # nonzero exit = refused because the contracted path was occupied:
        # contract-faithful behavior, nothing further to assert.
    finally:
        for p in (tmp, dest):
            shutil.rmtree(p, ignore_errors=True)
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except OSError:
                pass
