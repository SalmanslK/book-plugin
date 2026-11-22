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


class CommandNameTests(unittest.TestCase):
    def test_no_skill_or_agent_runs_the_command_by_its_old_name(self):
        # From 0.6.0 every Book that pins the plugin is on template 1.5.0, where factory.py is no command:
        # no file runs it, under any path, with a command after it.
        plugin = SKILLS.parent
        named = [path.relative_to(plugin).as_posix() for path in sorted(plugin.rglob("*"))
                 if path.is_file() and re.search(r"factory\.py\s+[\w-]",
                                                 path.read_text(encoding="utf-8", errors="replace"))]
        self.assertEqual(named, [])


if __name__ == "__main__":
    unittest.main()
