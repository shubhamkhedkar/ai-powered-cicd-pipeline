"""Explain CI failures (lint/test logs): root cause + suggested fix."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

SYSTEM = (
    "You are a CI troubleshooting expert. Given failing lint/test logs, respond in markdown "
    "with sections: **Root cause**, **Suggested fix** (with code if useful), **Confidence**."
)


def read_logs(paths: list[str], tail_chars: int = 20_000) -> str:
    parts = []
    for p in paths:
        f = Path(p)
        if f.exists():
            text = f.read_text(encoding="utf-8", errors="replace")
            parts.append(f"### {f.name}\n{text[-tail_chars:]}")
    return "\n\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("logs", nargs="+")
    a = p.parse_args(argv)
    if not common.ai_enabled():
        common.skip_notice("AI failure analysis")
        return 0
    logs = read_logs(a.logs)
    if not logs.strip():
        print("No logs found - nothing to analyse.")
        return 0
    body = "## 🤖 AI Failure Analysis\n\n" + common.chat(SYSTEM, logs)
    common.write_summary(body)
    pr = common.pr_number_from_event()
    if pr:
        try:
            common.post_pr_comment(pr, body)
        except Exception as e:  # noqa: BLE001 - comment is best effort (e.g. fork PRs)
            print(f"::warning::Could not comment on PR: {e}")
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
