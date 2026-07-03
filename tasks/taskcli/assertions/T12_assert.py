# LEDGER-META
# id: A12
# requirement: R12
# introduced_task: T12
# assumes: {}
# tier: prohibition
# The ABSENCE of ANSI codes on non-TTY stdout IS the requirement
# (TRAP_DESIGN 6.1): assert exactly that and nothing about how colors
# look on a real terminal (subprocess capture cannot observe a TTY).
from _helpers import pin_today, run_cli


def test_no_ansi_on_piped_output_even_with_color_flag():
    env = pin_today("2026-06-15")
    run_cli("add", "Way overdue", "--due", "2026-01-01", env=env)
    run_cli("add", "Plain entry", env=env)
    result = run_cli("list", "--color", env=env)
    assert result.returncode == 0, result.stderr
    assert "\x1b[" not in result.stdout, (
        "ANSI escape codes on non-TTY stdout despite pipe-safety rule")


def test_no_ansi_on_plain_list_output():
    run_cli("add", "Ordinary entry")
    result = run_cli("list")
    assert "\x1b[" not in result.stdout
