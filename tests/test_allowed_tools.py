"""
Every command a skill tells Claude to run is one its `allowed-tools` pre-approves, so a skill never stops to
ask for its own steps (Book D60). The commands are read from the skill's SKILL.md and its references/: each
inline code span that starts with a program the skills run, and each line of a fenced `sh` block.

`${CLAUDE_SKILL_DIR}` is left as written on both sides: Claude Code substitutes it in the body and in the
Bash rules of `allowed-tools` alike (the Skills docs), so the two still match after it is resolved.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "book" / "skills"
PROGRAMS = ("python", "python3", "git", "sh", "pdftotext", "dotnet", "gh", "curl", "rclone", "pwsh")
INLINE = re.compile(r"(?<!`)`([^`\n]+(?:\n[^`\n]+)?)`(?!`)")
FENCE = re.compile(r"^```(?:sh|bash|shell)\n(.*?)^```", re.M | re.S)
# Commands a skill names but does not run itself, each with why.
NOT_RUN = {
    ("*", "python devtools/book.py <command>"): "the line naming the Book's command, not a step",
}


def frontmatter(text: str) -> str:
    match = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    return match.group(1) if match else ""


def bash_patterns(text: str) -> list[str] | None:
    """The Bash rules of `allowed-tools`, or None when the skill sets none (every tool then asks or is allowed)."""
    match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter(text), re.M)
    return re.findall(r"Bash\(([^)]*)\)", match.group(1)) if match else None


def commands(text: str) -> set[str]:
    """The commands a skill's text gives to run: inline spans that start with a program, and sh block lines."""
    body = text[len(frontmatter(text)):]
    found = set()
    for block in FENCE.findall(body):
        found |= {line.strip() for line in block.splitlines() if line.strip() and not line.lstrip().startswith("#")}
    for span in INLINE.findall(FENCE.sub("", body)):
        span = " ".join(span.split())
        words = span.split()
        if len(words) > 1 and words[0] in PROGRAMS:
            found.add(span)
    return found


def allowed(command: str, patterns: list[str]) -> bool:
    """Claude Code's rule: the whole command matches, `*` standing for any text (a trailing ` *` also the bare one)."""
    for pattern in patterns:
        rx = "^" + re.escape(pattern).replace(r"\ \*", r"(?: .*)?").replace(r"\*", ".*") + "$"
        if re.match(rx, command, re.S):
            return True
    return False


def skill_text(folder: Path) -> str:
    parts = [(folder / "SKILL.md").read_text(encoding="utf-8")]
    parts += [path.read_text(encoding="utf-8") for path in sorted((folder / "references").rglob("*.md"))]
    return "\n".join(parts)


class AllowedToolsTests(unittest.TestCase):
    def test_every_command_a_skill_gives_is_pre_approved(self):
        skills = sorted(path.parent for path in SKILLS.glob("*/SKILL.md"))
        self.assertGreater(len(skills), 20)
        gaps = []
        for folder in skills:
            main = (folder / "SKILL.md").read_text(encoding="utf-8")
            patterns = bash_patterns(main)
            if patterns is None:
                continue
            for command in sorted(commands(skill_text(folder))):
                if (folder.name, command) in NOT_RUN or ("*", command) in NOT_RUN:
                    continue
                if not allowed(command, patterns):
                    gaps.append(f"{folder.name}: `{command}`")
        self.assertEqual(gaps, [], "add a Bash(...) rule to the skill's allowed-tools, or name it in NOT_RUN")

    def test_the_matcher_follows_claude_codes_rules(self):
        self.assertTrue(allowed("git diff --stat", ["git diff*"]))
        self.assertTrue(allowed("git fetch", ["git fetch *"]), "a trailing ` *` matches the bare command")
        self.assertFalse(allowed("git fetchall", ["git fetch *"]))
        self.assertTrue(allowed('python "${CLAUDE_SKILL_DIR}/scripts/x.py" a', ['python "${CLAUDE_SKILL_DIR}/scripts/x.py"*']))
        self.assertFalse(allowed("python devtools/book.py upgrade --target x", ["python devtools/book.py verify*"]))

    def test_the_reader_finds_inline_and_fenced_commands_and_skips_prose(self):
        text = ("---\nname: x\n---\n\nRun `git branch --show-current`, then `/book:plan`, and `pdftotext` alone.\n\n"
                "```sh\npython devtools/book.py upgrade --target <project>\n# a comment\n```\n\n"
                "Then `python3 devtools/book.py impact\n  --block \"x\"`.\n")
        self.assertEqual(commands(text), {"git branch --show-current", "python devtools/book.py upgrade --target <project>",
                                          'python3 devtools/book.py impact --block "x"'})
