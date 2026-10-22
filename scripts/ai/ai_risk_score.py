"""Score PR risk (low/medium/high) and apply a `risk:<level>` label."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

LEVELS = ("low", "medium", "high")
SYSTEM = (
    "Assess the risk of merging this diff (size, critical files, security, missing tests). "
    'Reply ONLY with JSON: {"risk": "low|medium|high", "reason": "<one sentence>"}'
)


def parse(answer: str) -> tuple[str, str]:
    m = re.search(r"\{.*\}", answer, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            lvl = str(d.get("risk", "")).lower()
            if lvl in LEVELS:
                return lvl, str(d.get("reason", ""))
        except json.JSONDecodeError:
            pass
    for lvl in ("high", "medium", "low"):
        if lvl in answer.lower():
            return lvl, answer.strip()[:200]
    return "medium", "Could not parse model output."


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--diff-file", required=True)
    p.add_argument("--no-label", action="store_true")
    a = p.parse_args(argv)
    if not common.ai_enabled():
        common.skip_notice("AI risk score")
        return 0
    diff = Path(a.diff_file).read_text(encoding="utf-8", errors="replace")
    level, reason = parse(common.chat(SYSTEM, diff))
    common.write_summary(f"### 🤖 AI Risk: **{level}**\n\n{reason}")
    pr = common.pr_number_from_event()
    if pr and not a.no_label:
        repo = common.os.environ["GITHUB_REPOSITORY"]
        common.github_request(f"/repos/{repo}/issues/{pr}/labels", {"labels": [f"risk:{level}"]})
    print(f"risk={level} reason={reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
