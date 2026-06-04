#!/usr/bin/env python3
"""Fail if public repo files contain common private/local Brain Researcher traces."""

from __future__ import annotations

from pathlib import Path
import re
import sys


CHECKS = [
    (
        "local user home path",
        re.compile(r"/home/(?!<user>|users/<sunet>|groups/<pi_group>)[A-Za-z0-9._-]+/"),
    ),
    ("local Brain Researcher MCP name", re.compile(r"brain-researcher-local")),
    (
        "client-specific local MCP prefix",
        re.compile(r"mcp__[A-Za-z0-9_.-]*local[A-Za-z0-9_.-]*__"),
    ),
    ("Brain Researcher token", re.compile(r"brk_user_[A-Za-z0-9_.-]+")),
    ("GitHub token", re.compile(r"gh[opsu]_[A-Za-z0-9_]{20,}")),
    ("Stanford email", re.compile(r"\b[A-Za-z0-9._%+-]+@stanford\.edu\b")),
    ("legacy GitHub org link", re.compile(r"github\.com/zjc062/brain-researcher")),
    (
        "known private project codename",
        re.compile(r"hai-gcp-dialogue-brain|liu_component_v1|sk-br-local|russ_poldrack"),
    ),
]


ALLOW = {
    "MCP_SETUP.md": ["brk_<kid>.<secret>"],
    "scripts/redaction_guard.py": [
        "brain-researcher-local",
        "mcp__[A-Za-z0-9_.-]*local[A-Za-z0-9_.-]*__",
        "brk_user_[A-Za-z0-9_.-]+",
        "gh[opsu]_[A-Za-z0-9_]{20,}",
        "github\\.com/zjc062/brain-researcher",
        "hai-gcp-dialogue-brain",
        "liu_component_v1",
        "sk-br-local",
        "russ_poldrack",
    ],
}


SKIP_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "dist",
    "build",
}


def is_allowed(path: Path, match: str) -> bool:
    allowed_snippets = ALLOW.get(path.as_posix(), [])
    return any(match in snippet or snippet in match for snippet in allowed_snippets)


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or SKIP_PARTS.intersection(path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        yield path, text


def main() -> int:
    root = Path(".")
    failures: list[str] = []

    for path, text in iter_text_files(root):
        display_path = path.as_posix()
        for label, pattern in CHECKS:
            for match in pattern.finditer(text):
                value = match.group(0)
                if is_allowed(path, value):
                    continue
                failures.append(f"{display_path}:{label}:{value}")

    if failures:
        print("Redaction guard failed:")
        for item in failures:
            print(f"  {item}")
        return 1

    print("Redaction guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
