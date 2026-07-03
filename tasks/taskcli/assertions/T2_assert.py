# LEDGER-META
# id: A2
# requirement: R2
# introduced_task: T2
# assumes: {}
# tier: correctness
from _helpers import run_cli


def test_list_sort_priority_orders_high_med_low():
    run_cli("add", "Low task", "--priority", "low")
    run_cli("add", "High task", "--priority", "high")
    run_cli("add", "Med task", "--priority", "med")
    result = run_cli("list", "--sort", "priority")
    assert result.returncode == 0, result.stderr
    titles_in_order = [t for t in ("High task", "Med task", "Low task")]
    lines = result.stdout.splitlines()
    positions = [next(i for i, l in enumerate(lines) if t in l) for t in titles_in_order]
    assert positions == sorted(positions)


def test_list_without_sort_keeps_insertion_order():
    run_cli("add", "First", "--priority", "low")
    run_cli("add", "Second", "--priority", "high")
    result = run_cli("list")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    pos_first = next(i for i, l in enumerate(lines) if "First" in l)
    pos_second = next(i for i, l in enumerate(lines) if "Second" in l)
    assert pos_first < pos_second
