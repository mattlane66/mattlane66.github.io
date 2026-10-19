#!/usr/bin/env python3
"""Check public-site files and new commits for accidental email/secret exposure.

Not a full secret scanner and cannot erase previously published Git history.
Never echo discovered email addresses or secret values into CI logs.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXT = {
    ".html", ".htm", ".js", ".mjs", ".css", ".json", ".xml", ".svg",
    ".md", ".txt", ".py", ".yml", ".yaml", ".toml", ".ini", ".sh",
    ".webmanifest", ".csv", ".ts", ".tsx", ".jsx",
}
EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
MAILTO = re.compile(r"""(?:href\s*=\s*["']\s*|(?:window\.)?location(?:\.href)?\s*=\s*["']\s*)mailto\s*:""", re.IGNORECASE)
EXAMPLE_DOMAINS = {"example.com", "example.net", "example.org", "example.test", "example.invalid"}
SAFE_COMMIT_DOMAINS = {"users.noreply.github.com", "noreply.github.com"}
SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", ".npmrc", ".pypirc",
    "id_rsa", "id_ed25519", "credentials.json",
}
SENSITIVE_SUFFIXES = (".pem", ".p12", ".pfx", ".key")


def safe_source_email(address: str) -> bool:
    domain = address.rsplit("@", 1)[-1].lower()
    return domain in EXAMPLE_DOMAINS or domain in SAFE_COMMIT_DOMAINS


def issues_in_source(path: str, content: str) -> list[str]:
    problems = []
    if any(not safe_source_email(m.group()) for m in EMAIL.finditer(content)):
        problems.append("non-example email address in tracked source")
    if Path(path).suffix.lower() in {".html", ".htm", ".js", ".mjs", ".json", ".css"} and MAILTO.search(content):
        problems.append("mailto reference in public web file")
    return problems


def check_tracked_files() -> list[str]:
    data = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    errors = []
    for raw in data.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", errors="replace")
        path = Path(relative)
        name = path.name.lower()
        if name in SENSITIVE_NAMES or name.endswith(SENSITIVE_SUFFIXES):
            errors.append(f"{relative}: prohibited private or credential filename")
        if path.suffix.lower() not in TEXT_EXT:
            continue
        try:
            source = (ROOT / relative).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            errors.append(f"{relative}: unable to scan tracked text file")
            continue
        errors += [f"{relative}: {issue}" for issue in issues_in_source(relative, source)]
    return errors


def safe_commit_email(address: str) -> bool:
    # GitHub itself uses this private committer identity for merge commits.
    return address.lower().split("@") == ["noreply", "github.com"] or address.rsplit("@", 1)[-1].lower() in SAFE_COMMIT_DOMAINS


def check_new_commit_metadata(base: str, head: str) -> list[str]:
    if not base or not head or set(base) == {"0"}:
        return []
    if not all(re.fullmatch(r"[0-9a-fA-F]{40}", rev) for rev in (base, head)):
        return ["invalid base or head SHA for commit metadata scan"]
    try:
        output = subprocess.check_output(
            ["git", "log", "--format=%H%x09%ae%x09%ce", f"{base}..{head}"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return ["unable to inspect new commit metadata"]
    errors = []
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            errors.append("unreadable commit metadata")
            continue
        sha, author, committer = fields
        for role, value in (("author", author), ("committer", committer)):
            if not safe_commit_email(value):
                errors.append(f"commit {sha[:12]}: {role} is not a GitHub noreply address")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="")
    args = parser.parse_args()
    errors = check_tracked_files() + check_new_commit_metadata(args.base, args.head)
    for issue in errors:
        print(f"PRIVACY: {issue}", file=sys.stderr)
    if errors:
        print(f"Privacy check failed ({len(errors)} findings); no addresses or values printed.", file=sys.stderr)
        return 1
    print("Privacy check passed: no disallowed emails, mailto links, or sensitive file names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
