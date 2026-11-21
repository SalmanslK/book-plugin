"""The skills check: it fails what it should, and the plugin's own skills and agents pass it."""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_skills  # noqa: E402

GOOD = "---\nname: {name}\ndescription: >\n  Use when it is needed. {extra}\n---\n\n# x\n\n## What next\n\n- Done.\n"
AGENT = "---\nname: {name}\ndescription: A second pair of eyes.\ntools: Read, Grep\n---\n\nBody.\n"


class CheckSkillsTests(unittest.TestCase):
    def plugin(self, skills: dict[str, str], agents: dict[str, str] | None = None) -> Path:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        for name, text in skills.items():
            (root / "skills" / name).mkdir(parents=True)
            (root / "skills" / name / "SKILL.md").write_text(text, encoding="utf-8")
        (root / "agents").mkdir()
        for name, text in (agents or {}).items():
            (root / "agents" / f"{name}.md").write_text(text, encoding="utf-8")
        return root

    def test_the_plugins_own_skills_and_agents_pass(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_skills.main([])
        self.assertEqual(0, code, out.getvalue())

    def test_a_sound_skill_and_agent_pass(self):
        root = self.plugin({"plan": GOOD.format(name="plan", extra="")}, {"reviewer": AGENT.format(name="reviewer")})
        self.assertEqual(([], len("Use when it is needed.")), check_skills.problems(root))

    def test_a_name_that_is_not_the_folder_fails(self):
        failures, _ = check_skills.problems(self.plugin({"plan": GOOD.format(name="book:plan", extra="")}))
        self.assertTrue(any("it must be the folder's name" in line for line in failures), failures)

    def test_a_missing_what_next_or_an_unknown_key_fails(self):
        text = "---\nname: plan\ndescription: x\ncolour: red\n---\n\nNo ending.\n"
        failures, _ = check_skills.problems(self.plugin({"plan": text}))
        self.assertEqual(2, len(failures), failures)

    def test_a_long_description_or_a_total_over_budget_fails(self):
        long = GOOD.format(name="a", extra="x" * 1100)
        failures, _ = check_skills.problems(self.plugin({"a": long}))
        self.assertTrue(any("the limit is 1,024" in line for line in failures), failures)
        many = {f"s{n}": GOOD.format(name=f"s{n}", extra="y" * 900) for n in range(11)}
        failures, _ = check_skills.problems(self.plugin(many))
        self.assertTrue(any("keep them under 9,000" in line for line in failures), failures)

    def test_an_agent_without_tools_fails(self):
        text = "---\nname: tester\ndescription: Runs the tests.\n---\n"
        failures, _ = check_skills.problems(self.plugin({"plan": GOOD.format(name="plan", extra="")}, {"tester": text}))
        self.assertTrue(any("no `tools` list" in line for line in failures), failures)


if __name__ == "__main__":
    unittest.main()
