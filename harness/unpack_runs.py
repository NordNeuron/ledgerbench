"""Committed run archives: unpack them for analysis, or (maintainers) re-pack.

    python -m harness.unpack_runs              # data/runs/*.tar.xz -> runs/
    python -m harness.unpack_runs --excluded   # also data/excluded/*.tar.xz -> runs_*/, logs_*/
    python -m harness.unpack_runs --pack       # rebuild the archives + data/SHA256SUMS

Each archive's members are repo-relative paths (runs/run_armA_seed1_.../...),
so extraction recreates exactly the layout the harness wrote. Checksums in
data/SHA256SUMS are verified before extracting.
"""
import argparse
import hashlib
import sys
import tarfile
from pathlib import Path

from harness import config

ROOT = config.ROOT_DIR
DATA = ROOT / "data"
SUMS = DATA / "SHA256SUMS"
MAIN_ARMS = ["A", "B", "C", "Cplus", "D"]
EXCLUDED = ["runs_smoke", "runs_published_protocol", "runs_truncated_32k", "runs_64k",
            "logs_published_protocol", "logs_truncated_32k", "logs_64k"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pack() -> None:
    (DATA / "runs").mkdir(parents=True, exist_ok=True)
    (DATA / "excluded").mkdir(parents=True, exist_ok=True)
    targets = []
    for arm in MAIN_ARMS:
        members = sorted((ROOT / "runs").glob(f"run_arm{arm}_seed*"))
        if not members:
            sys.exit(f"no runs for arm {arm} under runs/")
        targets.append((DATA / "runs" / f"arm{arm}.tar.xz", members))
    for name in EXCLUDED:
        if (ROOT / name).exists():
            targets.append((DATA / "excluded" / f"{name}.tar.xz", [ROOT / name]))
    for out, members in targets:
        with tarfile.open(out, "w:xz", preset=9) as tar:
            for m in members:
                tar.add(m, arcname=m.relative_to(ROOT).as_posix())
        print(f"packed {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB)")
    lines = [f"{_sha256(p)}  {p.relative_to(DATA).as_posix()}" for p, _ in targets]
    SUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {SUMS.relative_to(ROOT)}")


def unpack(include_excluded: bool) -> None:
    sums = dict(reversed(line.split("  ", 1)) for line in SUMS.read_text(encoding="utf-8").splitlines() if line)
    archives = sorted((DATA / "runs").glob("*.tar.xz"))
    if len(archives) != len(MAIN_ARMS):
        sys.exit(f"expected {len(MAIN_ARMS)} archives in data/runs/, found {len(archives)}")
    if include_excluded:
        archives += sorted((DATA / "excluded").glob("*.tar.xz"))
    for a in archives:
        rel = a.relative_to(DATA).as_posix()
        if sums.get(rel) != _sha256(a):
            sys.exit(f"checksum mismatch for data/{rel}")
        with tarfile.open(a, "r:xz") as tar:
            tar.extractall(ROOT, filter="data")
        print(f"unpacked data/{rel}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pack", action="store_true", help="rebuild archives from runs/ (maintainers)")
    p.add_argument("--excluded", action="store_true", help="also unpack the excluded attempts")
    args = p.parse_args()
    pack() if args.pack else unpack(args.excluded)


if __name__ == "__main__":
    main()
