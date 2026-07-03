# LEDGER-META
# id: A2i
# requirement: R2
# introduced_task: T2
# assumes: {}
# tier: invariant
from _helpers import extract_id, run_cli


def test_delete_never_renumbers_survivors():
    run_cli("add", "Keep alpha")
    run_cli("add", "Drop beta")
    run_cli("add", "Keep gamma")
    lines = run_cli("list").stdout.splitlines()
    id_alpha = extract_id(next(l for l in lines if "Keep alpha" in l))
    id_beta = extract_id(next(l for l in lines if "Drop beta" in l))
    id_gamma = extract_id(next(l for l in lines if "Keep gamma" in l))

    run_cli("delete", id_beta)
    lines_after = run_cli("list").stdout.splitlines()
    assert extract_id(next(l for l in lines_after if "Keep alpha" in l)) == id_alpha
    assert extract_id(next(l for l in lines_after if "Keep gamma" in l)) == id_gamma


def test_ids_stable_across_operations():
    # Seed commands only: this file replays from T2, before `edit` exists.
    run_cli("add", "Constant star")
    run_cli("add", "Passing comet")
    lines = run_cli("list").stdout.splitlines()
    original_id = extract_id(next(l for l in lines if "Constant star" in l))
    comet_id = extract_id(next(l for l in lines if "Passing comet" in l))

    run_cli("done", original_id)
    run_cli("delete", comet_id)
    lines_after = run_cli("list").stdout.splitlines()
    id_after = extract_id(next(l for l in lines_after if "Constant star" in l))
    assert id_after == original_id, "an existing task's ID must never change"


def test_plain_list_is_insertion_order_with_mixed_priorities():
    run_cli("add", "Oldest entry", "--priority", "low")
    run_cli("add", "Middle entry", "--priority", "high")
    run_cli("add", "Newest entry", "--priority", "med")
    lines = run_cli("list").stdout.splitlines()
    pos = {name: next(i for i, l in enumerate(lines) if name in l)
           for name in ("Oldest entry", "Middle entry", "Newest entry")}
    assert pos["Oldest entry"] < pos["Middle entry"] < pos["Newest entry"]
