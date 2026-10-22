"""Shared helpers: OpenAI-compatible chat client + GitHub API helpers (stdlib only)."""

from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
MAX_INPUT_CHARS = 60_000


def ai_enabled() -> bool:
    return bool(os.environ.get("AI_API_KEY", "").strip())


def skip_notice(stage: str) -> None:
    msg = f"AI_API_KEY secret not set - skipping {stage}."
    print(f"::notice title=AI stage skipped::{msg}")
    write_summary(f"> ℹ️ {msg}\n")


def truncate(text: str, limit: int = MAX_INPUT_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def _http(url: str, data: dict | None, headers: dict, method: str = "POST") -> dict:
    body = json.dumps(data).encode() if data is not None else None
    if not url.startswith("https://"):
        raise ValueError("Only https URLs are allowed")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)  # noqa: S310
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        raw = resp.read().decode() or "{}"
        return json.loads(raw)


def chat(system: str, user: str) -> str:
    base = os.environ.get("AI_BASE_URL") or DEFAULT_BASE_URL
    model = os.environ.get("AI_MODEL") or DEFAULT_MODEL
    resp = _http(
        base.rstrip("/") + "/chat/completions",
        {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": truncate(user)},
            ],
        },
        {"Authorization": f"Bearer {os.environ['AI_API_KEY']}", "Content-Type": "application/json"},
    )
    return resp["choices"][0]["message"]["content"].strip()


def write_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def github_request(path: str, data: dict | None = None, method: str = "POST") -> dict:
    token = os.environ["GITHUB_TOKEN"]
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    return _http(
        f"{api}{path}",
        data,
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method,
    )


def post_pr_comment(pr_number: int | str, body: str) -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    github_request(f"/repos/{repo}/issues/{pr_number}/comments", {"body": body})


def pr_number_from_event() -> str | None:
    if os.environ.get("PR_NUMBER"):
        return os.environ["PR_NUMBER"]
    path = os.environ.get("GITHUB_EVENT_PATH")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            ev = json.load(f)
        num = (ev.get("pull_request") or {}).get("number")
        return str(num) if num else None
    return None
