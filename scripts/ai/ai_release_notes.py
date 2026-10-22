"""Generate release notes from commits since the previous tag."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

SYSTEM = (
    "You write release notes. Group the commits into Features, Fixes, Maintenance "
    "(omit empty groups), as concise markdown bullets. No preamble."
)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout.strip()


def commits_since_last_tag(current: str) -> str:
    prev = _git("describe", "--tags", "--abbrev=0", f"{current}^")
    rng = f"{prev}..{current}" if prev else current
    return _git("log", rng, "--pretty=format:- %s (%h)")


def fallback_notes(commits: str) -> str:
    return "## What's changed\n\n" + (commits or "- No changes")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", default="HEAD")
    p.add_argument("--output", default="release_notes.md")
    a = p.parse_args(argv)
    commits = commits_since_last_tag(a.tag)
    if common.ai_enabled():
        notes = "## What's changed\n\n" + common.chat(SYSTEM, commits or "(no commits)")
    else:
        common.skip_notice("AI release notes (using plain commit list)")
        notes = fallback_notes(commits)
    Path(a.output).write_text(notes + "\n", encoding="utf-8")
    common.write_summary(notes)
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
