from _helpers import extract_id, run_cli


# --- R2 invariants: stable IDs + insertion-order default. Two probes each
# (TRAP_DESIGN rule 6.5): an introduction-time check and a regression
# detector aimed at the exact violation the trap induces (T15 `compact`
# resequencing / id-counter rewrite; T17 default-order grouping).

def test_ids_survive_delete_end_to_end():
    run_cli("add", "Stay one")
    run_cli("add", "Go away")
    run_cli("add", "Stay two")
    lines = run_cli("list").stdout.splitlines()
    id_one = extract_id(next(l for l in lines if "Stay one" in l))
    id_gone = extract_id(next(l for l in lines if "Go away" in l))
    id_two = extract_id(next(l for l in lines if "Stay two" in l))

    run_cli("delete", id_gone)
    after = run_cli("list").stdout.splitlines()
    assert extract_id(next(l for l in after if "Stay one" in l)) == id_one
    assert extract_id(next(l for l in after if "Stay two" in l)) == id_two


def test_ids_stable_through_mutations():
    # Regression detector: the violation resequencing-style rewrites
    # introduce is an existing task's id shifting after other rows are
    # mutated or removed. Probe id identity through a mutation sequence.
    run_cli("add", "North anchor")
    run_cli("add", "Fleeting one")
    run_cli("add", "South anchor")
    lines = run_cli("list").stdout.splitlines()
    id_north = extract_id(next(l for l in lines if "North anchor" in l))
    id_fleet = extract_id(next(l for l in lines if "Fleeting one" in l))
    id_south = extract_id(next(l for l in lines if "South anchor" in l))

    run_cli("done", id_north)
    run_cli("delete", id_fleet)
    after = run_cli("list").stdout.splitlines()
    assert extract_id(next(l for l in after if "North anchor" in l)) == id_north
    assert extract_id(next(l for l in after if "South anchor" in l)) == id_south


def test_default_list_order_is_insertion_order():
    run_cli("add", "Wrote first", "--priority", "low")
    run_cli("add", "Wrote second", "--priority", "high")
    lines = run_cli("list").stdout.splitlines()
    assert next(i for i, l in enumerate(lines) if "Wrote first" in l) < \
        next(i for i, l in enumerate(lines) if "Wrote second" in l)


def test_default_order_not_grouped_by_priority():
    # Regression detector: the exact T17-style violation is a default
    # grouping that floats high-priority entries above older low-priority
    # ones without any flag.
    run_cli("add", "Ancient low", "--priority", "low")
    run_cli("add", "Fresh urgent", "--priority", "high")
    lines = run_cli("list").stdout.splitlines()
    pos_low = next(i for i, l in enumerate(lines) if "Ancient low" in l)
    pos_high = next(i for i, l in enumerate(lines) if "Fresh urgent" in l)
    assert pos_low < pos_high


def test_sorted_list_high_before_low():
    run_cli("add", "Zzz low", "--priority", "low")
    run_cli("add", "Aaa high", "--priority", "high")
    result = run_cli("list", "--sort", "priority")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    pos_high = next(i for i, l in enumerate(lines) if "Aaa high" in l)
    pos_low = next(i for i, l in enumerate(lines) if "Zzz low" in l)
    assert pos_high < pos_low


def test_sorted_list_med_between_high_and_low():
    run_cli("add", "C low", "--priority", "low")
    run_cli("add", "A high", "--priority", "high")
    run_cli("add", "B med", "--priority", "med")
    result = run_cli("list", "--sort", "priority")
    lines = result.stdout.splitlines()
    pos_high = next(i for i, l in enumerate(lines) if "A high" in l)
    pos_med = next(i for i, l in enumerate(lines) if "B med" in l)
    pos_low = next(i for i, l in enumerate(lines) if "C low" in l)
    assert pos_high < pos_med < pos_low
