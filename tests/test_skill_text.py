"""
Promises a skill's own words make, held where the skills live: the boilerplate tested these against its
copies until v1.3.0 moved them here.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "book" / "skills"
REVIEW_CHECKLIST = ("review-method.md", "review-pass-a.md", "review-b-core.md")


class ReviewAndShipTests(unittest.TestCase):
    def test_peer_review_never_resolves_and_ship_resolves_only_with_the_flag(self):
        review = "\n".join(path.read_text(encoding="utf-8") for path in (SKILLS / "peer-review").rglob("*.md"))
        self.assertNotIn("--confirm-author-settled", review, "/book:peer-review never resolves a thread")
        self.assertIn("--expect-head", review, "/book:peer-review posts only onto the head it reviewed")
        posts = [line for line in review.splitlines() if "pr post " in line and "--plan" in line]
        self.assertTrue(posts, "/book:peer-review posts its findings with pr post")
        self.assertTrue(all("--expect-head" in line for line in posts), posts)
        ship = (SKILLS / "ship" / "SKILL.md").read_text(encoding="utf-8")
        resolves = [line for line in ship.splitlines() if "pr resolve" in line]
        self.assertTrue(resolves)
        self.assertTrue(all("--confirm-author-settled" in line for line in resolves), resolves)

    def test_the_core_review_checklist_is_where_review_scope_names_it(self):
        # A project's `book review-scope` prints `book:peer-review/references/<file>` for these.
        for name in REVIEW_CHECKLIST:
            self.assertTrue((SKILLS / "peer-review" / "references" / name).is_file(), name)
        method = (SKILLS / "peer-review" / "references" / "review-method.md").read_text(encoding="utf-8")
        self.assertIn("This is the one READY rule", method)


# The triage table's rows, in order. A project's factory.toml [[review_scope.rows]] carries the same names
# (the boilerplate pins this list too), so a row added or renamed here must be added there in step.
TRIAGE_ROWS = [
    "Product code under `src/`", "An endpoint, request/response DTO or permission", "A migration", "Tests only",
    "Docs only (`docs/`, other `*.md`)", "Tooling (`devtools/`, `.claude/`, `.githooks/`, CI)",
    "A `CLAUDE.md` (root or nested)", "`requirements/**`", "`database-scripts/`, `scripts/`",
    "Root build and deploy config \u2014 `Directory.Packages.props`, `compose*.yaml`, `Dockerfile`, "
    "`appsettings*.json`, `bitbucket-pipelines.yml`",
    "Generated files \u2014 `docs/api/api-contracts.md`, `docs/database-erd.md`, a migration's `.Designer.cs`, "
    "the model snapshot",
]
ROW = re.compile(r"^\| (\d+) \|", re.M)


class ReviewChecklistTests(unittest.TestCase):
    """The core checklist's safeguards the boilerplate held until v1.3.0 (C1, C6, the one READY rule)."""

    def files(self) -> dict[str, str]:
        folder = SKILLS / "peer-review" / "references"
        return {name: (folder / name).read_text(encoding="utf-8") for name in REVIEW_CHECKLIST}

    def test_the_triage_table_has_the_pinned_rows(self):
        method = self.files()["review-method.md"]
        table = method.split("| The diff touches |", 1)[1].split("\n\n", 1)[0]
        cells = [line.split("|")[1].strip() for line in table.splitlines()[2:] if line.startswith("|")]
        self.assertEqual(cells, TRIAGE_ROWS)

    def test_every_core_check_appears_exactly_once(self):
        files = self.files()
        rows = [int(n) for text in files.values() for n in ROW.findall(text)]
        self.assertEqual(sorted({n for n in rows if rows.count(n) > 1}), [], "a check in two places")
        headed = {int(n) for heading in re.findall(r"^### A\d · .*$", files["review-pass-a.md"], re.M)
                  if "\u2014" in heading for n in re.findall(r"\b(\d+)\b", heading.split("\u2014", 1)[1])}
        prose = headed - set(rows)
        self.assertEqual(prose, {1, 3, 4, 15}, "the Pass A checks with no table row")
        self.assertEqual(sorted(set(rows) | prose)[:15], list(range(1, 16)), "checks 1-15, Pass A")

    def test_the_method_owns_the_one_ready_rule(self):
        others = [name for name, text in self.files().items() if name != "review-method.md" and "NOT READY" in text]
        self.assertEqual(others, [], "the READY rule is stated once, in the method")


class UpgradeSkillTests(unittest.TestCase):
    """/book:upgrade drives the 1.5 -> 1.6 move: its words must match what that upgrade does and asks."""

    def text(self) -> str:
        return (SKILLS / "upgrade" / "SKILL.md").read_text(encoding="utf-8")

    def test_it_does_not_say_apply_writes_only_template_files(self):
        self.assertNotIn("writes only `BEHIND` and `NEW`", self.text())
        for written in ("every `CLAUDE.md`", "`factory.toml`", "book-files.lock"):
            self.assertIn(written, self.text())

    def test_it_has_a_going_to_1_6_section_with_each_step_the_report_asks_for(self):
        text = self.text()
        self.assertIn("### Going to 1.6", text)
        section = text.split("### Going to 1.6", 1)[1].split("\n### ", 1)[0]
        for step in ("`SPLIT`", "`CONFIRM`", "drift_accepted", "`[book] declined`", "`CONFLICT`",
                     "python devtools/book.py defects classify", "python devtools/book.py requirements import",
                     "check-rules.py --write", "/book:check-sources", "enabled = false"):
            self.assertIn(step, section, step)

    def test_a_split_nested_claude_md_is_never_one_to_delete(self):
        text = self.text()
        self.assertIn("| `SPLIT` |", text)
        self.assertIn("never delete", text.split("| `SPLIT` |", 1)[1].splitlines()[0])
        self.assertIn("**never delete one**", text)

    def test_its_allowed_tools_take_the_follow_up_commands(self):
        front = self.text().split("\n---", 1)[0]
        for rule in ("Bash(python devtools/book.py defects*)", "Bash(python3 devtools/book.py defects*)",
                     "Bash(python devtools/book.py requirements*)", "Bash(python3 devtools/book.py requirements*)",
                     "Bash(git tag -l*)", "Bash(git tag --list*)"):
            self.assertIn(rule, front)

    def test_only_listing_tags_is_pre_approved(self):
        # A rule as wide as `git tag*` would pre-approve `git tag -d` and `git tag -f` too.
        for skill in ("upgrade", "release-notes"):
            front = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8").split("\n---", 1)[0]
            tags = re.findall(r"Bash\((git tag[^)]*)\)", front)
            self.assertEqual(tags, ["git tag -l*", "git tag --list*"], skill)

    def test_the_carry_over_steps_are_numbered_once_and_keep_pending_merge_for(self):
        steps = self.text().split("### 3. Apply, then carry over", 1)[1].split("###", 1)[0]
        numbers = [line.split(".", 1)[0] for line in steps.splitlines() if line[:1].isdigit()]
        self.assertEqual(numbers, [str(n) for n in range(1, len(numbers) + 1)])
        self.assertIn("keeping `[book]\n   pending_merge_for` as it is", steps)

    def test_it_shows_the_diffs_to_decide_on_and_offers_the_routine_ones(self):
        # Book 1.6.0's report keeps the BEHIND and NEW diffs in a file of their own (Book D79).
        text = self.text()
        self.assertIn("*Diffs to decide on*", text)
        self.assertIn("`--diffs <path>`", text)
        self.assertIn("| `RETIRED` |", text)


class CommandNameTests(unittest.TestCase):
    def test_no_skill_or_agent_runs_the_command_by_its_old_name(self):
        # From 0.6.0 every Book that pins the plugin is on template 1.5.0, where factory.py is no command:
        # no file runs it, under any path, with a command after it.
        plugin = SKILLS.parent
        named = [path.relative_to(plugin).as_posix() for path in sorted(plugin.rglob("*"))
                 if path.is_file() and re.search(r"factory\.py\s+[\w-]",
                                                 path.read_text(encoding="utf-8", errors="replace"))]
        self.assertEqual(named, [])


class PathTests(unittest.TestCase):
    """A skill runs from the plugin's folder: its links to the project cannot resolve, and a path it names
    through ${CLAUDE_SKILL_DIR} must say how to resolve it when the variable is not expanded."""

    def test_every_skill_that_uses_the_skill_dir_says_how_to_resolve_it(self):
        missing = [path.parent.name for path in sorted(SKILLS.glob("*/SKILL.md"))
                   if "${CLAUDE_SKILL_DIR}/" in (text := path.read_text(encoding="utf-8"))
                   or "${CLAUDE_SKILL_DIR}\\" in text
                   if "If it reaches you unexpanded" not in text]
        self.assertEqual(missing, [])

    def test_no_markdown_link_points_into_the_project(self):
        link = re.compile(r"\]\(((?:CLAUDE|AI-DEVELOPMENT-GUIDE|README)\.md|(?:docs|devtools|requirements|src|tests)/)[^)]*\)")
        found = [f"{path.relative_to(SKILLS).as_posix()}: {match.group(0)}" for path in sorted(SKILLS.rglob("*.md"))
                 for match in link.finditer(path.read_text(encoding="utf-8"))
                 if not (path.parent / match.group(0)[2:-1].split("#")[0]).exists()]
        self.assertEqual(found, [], "write a project path as text: the project's `CLAUDE.md`, section ...")

    def test_the_review_checks_are_counted_alike(self):
        texts = "\n".join(path.read_text(encoding="utf-8") for path in
                          [SKILLS / "self-review" / "SKILL.md", *(SKILLS / "peer-review" / "references").glob("*.md")])
        self.assertNotIn("160 checks", texts)
        self.assertNotIn("checks 16–160)", texts)
        self.assertIn("161 named checks", texts)


if __name__ == "__main__":
    unittest.main()
