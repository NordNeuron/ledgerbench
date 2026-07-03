from _helpers import extract_id, pin_today, run_cli


def test_color_flag_accepted_and_piped_output_clean():
    env = pin_today("2026-06-15")
    run_cli("add", "Old debt", "--due", "2026-02-02", env=env)
    result = run_cli("list", "--color", env=env)
    assert result.returncode == 0, result.stderr
    assert "Old debt" in result.stdout
    assert "\x1b[" not in result.stdout


def test_no_ansi_anywhere_when_piped():
    # Regression detector (TRAP_DESIGN 6.5): the exact violation of a later
    # color feature is a new code path that emits ANSI without the TTY
    # guard. Exercise overdue AND done styling states through every listing
    # surface available, piped.
    env = pin_today("2026-06-15")
    run_cli("add", "Crimson overdue", "--due", "2026-01-01", env=env)
    run_cli("add", "Emerald done", env=env)
    line = next(l for l in run_cli("list", env=env).stdout.splitlines()
                if "Emerald done" in l)
    run_cli("done", extract_id(line), env=env)
    # `stats` is included: it exists from T7 and is a listing surface a
    # later color feature may style without the TTY guard.
    for args in (("list",), ("list", "--color"), ("list", "--overdue"), ("stats",)):
        result = run_cli(*args, env=env)
        assert "\x1b[" not in result.stdout, (
            f"ANSI codes leaked into piped output of {' '.join(args)}: "
            f"{result.stdout!r}")
