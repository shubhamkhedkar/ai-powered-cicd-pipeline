import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "ai"))
import ai_failure_analysis  # noqa: E402
import ai_release_notes  # noqa: E402
import ai_review  # noqa: E402
import ai_risk_score  # noqa: E402
import common  # noqa: E402


@pytest.fixture
def env(monkeypatch, tmp_path):
    for k in ("AI_API_KEY", "PR_NUMBER", "GITHUB_EVENT_PATH"):
        monkeypatch.delenv(k, raising=False)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    return summary


@pytest.fixture
def diff(tmp_path):
    f = tmp_path / "pr.diff"
    f.write_text("+print('hi')\n")
    return f


def test_skip_without_key(env, diff, capsys):
    with mock.patch.object(common, "_http") as http:
        assert ai_review.main(["--diff-file", str(diff)]) == 0
        assert ai_risk_score.main(["--diff-file", str(diff)]) == 0
        assert ai_failure_analysis.main([str(diff)]) == 0
        http.assert_not_called()
    assert "skipping" in env.read_text()


def test_chat_request(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    resp = {"choices": [{"message": {"content": " ok "}}]}
    with mock.patch.object(common, "_http", return_value=resp) as http:
        assert common.chat("s", "u") == "ok"
    url, payload, headers = http.call_args.args
    assert url == "https://api.openai.com/v1/chat/completions"
    assert payload["model"] == "gpt-4o-mini"
    assert headers["Authorization"] == "Bearer k"


def test_review_posts_comment(env, diff, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")
    monkeypatch.setenv("PR_NUMBER", "7")
    with (
        mock.patch.object(common, "chat", return_value="LGTM"),
        mock.patch.object(common, "github_request") as gh,
    ):
        assert ai_review.main(["--diff-file", str(diff)]) == 0
    path, data = gh.call_args.args
    assert path == "/repos/o/r/issues/7/comments"
    assert "LGTM" in data["body"]


def test_failure_analysis_summary(env, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")
    log = tmp_path / "pytest.log"
    log.write_text("AssertionError: 1 != 2")
    with mock.patch.object(common, "chat", return_value="Root cause: math") as c:
        assert ai_failure_analysis.main([str(log), str(tmp_path / "missing.log")]) == 0
    assert "AssertionError" in c.call_args.args[1]
    assert "Root cause: math" in env.read_text()


@pytest.mark.parametrize(
    "answer,level",
    [
        ('{"risk": "high", "reason": "auth"}', "high"),
        ('```json\n{"risk":"low"}\n```', "low"),
        ("medium-ish", "medium"),
        ("???", "medium"),
    ],
)
def test_risk_parse(answer, level):
    assert ai_risk_score.parse(answer)[0] == level


def test_risk_labels(env, diff, monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "k")
    monkeypatch.setenv("PR_NUMBER", "3")
    with (
        mock.patch.object(common, "chat", return_value='{"risk":"high","reason":"x"}'),
        mock.patch.object(common, "github_request") as gh,
    ):
        ai_risk_score.main(["--diff-file", str(diff)])
    assert gh.call_args.args[1] == {"labels": ["risk:high"]}


def test_release_notes(env, tmp_path, monkeypatch):
    out = tmp_path / "notes.md"
    monkeypatch.setattr(ai_release_notes, "commits_since_last_tag", lambda t: "- feat x (abc)")
    assert ai_release_notes.main(["--output", str(out)]) == 0
    assert "feat x" in out.read_text()
    monkeypatch.setenv("AI_API_KEY", "k")
    with mock.patch.object(common, "chat", return_value="### Features\n- X"):
        ai_release_notes.main(["--output", str(out)])
    assert "### Features" in out.read_text()
