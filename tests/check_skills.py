#!/usr/bin/env python3
"""
Every skill and agent of the book plugin loads, and stays findable.

Adapted from the Book boilerplate's devtools/checks/check-skills.py (v1.2.9) to read the plugin's folders.

    python tests/check_skills.py [--root <plugin folder>]

The plugin folder defaults to plugins/book. For each `skills/<folder>/SKILL.md`:

1. It opens with a `---` frontmatter block that closes, and every key in it is one Claude Code reads.
2. `name` is present and equals the folder's name.
3. `description` is present, not empty, and at most 1,024 characters (the portable limit; the
   listing cuts at 1,536).
4. It ends with a `## What next` section: every skill says what comes after it.

For each `agents/<name>.md`: a frontmatter block whose keys are ones Claude Code reads for an agent,
`name` equal to the file's name, a description within the same limit, and a `tools` list - an agent with
no tools list inherits every tool, which a reviewer must not.

Then the sum of every skill description is held to LISTING_BUDGET. Over it is a failure here: the plugin's
skills share the session's listing with the project's own skills and the person's other plugins.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "plugins" / "book"
DESCRIPTION_LIMIT = 1024
# 7,500 until v0.5.0, which took in the four pack skills (check-guides, publish-guides, release-notes, deploy)
# from the project's own listing: the session's total is the same, so the budget grew by their 1,400 characters.
LISTING_BUDGET = 9_000
KEYS = {"name", "description", "when_to_use", "allowed-tools", "argument-hint", "disable-model-invocation",
        "user-invocable", "model", "license", "version", "metadata"}
AGENT_KEYS = {"name", "description", "tools", "model", "color"}
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TOP_KEY = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")


def frontmatter(text: str) -> dict[str, str] | None:
    """The top-level keys and their values, a folded or literal block joined into one line; None if absent."""
    match = FRONTMATTER.match(text.replace("\r\n", "\n"))
    if not match:
        return None
    fields: dict[str, str] = {}
    key = None
    for line in match.group(1).split("\n"):
        top = TOP_KEY.match(line)
        if top:
            key = top.group(1)
            value = top.group(2).strip()
            fields[key] = "" if value in (">", ">-", "|", "|-") else value.strip("\"'")
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def problems(root: Path = ROOT) -> tuple[list[str], int]:
    """(failures, total description length) for every skill and agent under root."""
    failures: list[str] = []
    total = 0
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    if not skills:
        failures.append(f"{root}: no skills/<folder>/SKILL.md found")
    for path in skills:
        rel = path.relative_to(root).as_posix()
        folder = path.parent.name
        text = path.read_text(encoding="utf-8")
        fields = frontmatter(text)
        if fields is None:
            failures.append(f"{rel}: no frontmatter — it must open with a `---` block that closes")
            continue
        unknown = sorted(set(fields) - KEYS)
        if unknown:
            failures.append(f"{rel}: frontmatter key(s) Claude Code does not read: {', '.join(unknown)}")
        if fields.get("name") != folder:
            failures.append(f"{rel}: name is {fields.get('name')!r}; it must be the folder's name, {folder!r}")
        description = fields.get("description", "")
        if not description:
            failures.append(f"{rel}: no description — the skill would never trigger")
        elif len(description) > DESCRIPTION_LIMIT:
            failures.append(f"{rel}: description is {len(description):,} characters; the limit is {DESCRIPTION_LIMIT:,}")
        total += len(description)
        if not re.search(r"^## What next\s*$", text.replace("\r\n", "\n"), re.M):
            failures.append(f"{rel}: no `## What next` section — every skill says what comes after it")
    for path in sorted((root / "agents").glob("*.md")):
        rel = path.relative_to(root).as_posix()
        fields = frontmatter(path.read_text(encoding="utf-8"))
        if fields is None:
            failures.append(f"{rel}: no frontmatter — it must open with a `---` block that closes")
            continue
        unknown = sorted(set(fields) - AGENT_KEYS)
        if unknown:
            failures.append(f"{rel}: frontmatter key(s) Claude Code does not read for an agent: {', '.join(unknown)}")
        if fields.get("name") != path.stem:
            failures.append(f"{rel}: name is {fields.get('name')!r}; it must be the file's name, {path.stem!r}")
        description = fields.get("description", "")
        if not description or len(description) > DESCRIPTION_LIMIT:
            failures.append(f"{rel}: description is {'missing' if not description else f'{len(description):,} characters'}"
                            f"; it must be present and at most {DESCRIPTION_LIMIT:,}")
        if not fields.get("tools"):
            failures.append(f"{rel}: no `tools` list — an agent without one inherits every tool")
    if total >= LISTING_BUDGET:
        failures.append(f"the {len(skills)} descriptions total {total:,} characters; keep them under "
                        f"{LISTING_BUDGET:,}. Shorten the longest.")
    return failures, total


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[args.index("--root") + 1]) if "--root" in args else ROOT
    failures, total = problems(root)
    if failures:
        print(f"Skills: {len(failures)} problem(s)")
        for line in failures:
            print(f"  {line}")
        return 1
    print(f"Every skill loads ({total:,} characters of description).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
