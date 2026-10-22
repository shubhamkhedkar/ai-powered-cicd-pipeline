"""AI code review of a PR diff; posts the review as a PR comment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

SYSTEM = (
    "You are a senior code reviewer. Review the unified diff. Report bugs, security issues, "
    "performance problems and readability concerns as a concise markdown list with file/line "
    "references. If the change looks good, say so briefly. Do not invent code not in the diff."
)


def review(diff: str) -> str:
    return common.chat(SYSTEM, f"Diff:\n```diff\n{diff}\n```")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--diff-file", required=True)
    p.add_argument("--no-comment", action="store_true")
    a = p.parse_args(argv)
    if not common.ai_enabled():
        common.skip_notice("AI code review")
        return 0
    diff = Path(a.diff_file).read_text(encoding="utf-8", errors="replace")
    if not diff.strip():
        print("Empty diff - nothing to review.")
        return 0
    body = "## 🤖 AI Code Review\n\n" + review(diff)
    common.write_summary(body)
    pr = common.pr_number_from_event()
    if pr and not a.no_comment:
        common.post_pr_comment(pr, body)
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
