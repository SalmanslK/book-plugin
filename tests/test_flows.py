"""
The recipes `/book:flow` walks (plugins/book/skills/flow/flows/): each names only skills that exist, marks the
packs its steps need, starts each review in a fresh session, and every skill it names says, in its own
*What next*, where it goes in that flow.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "book" / "skills"
FLOWS = SKILLS / "flow" / "flows"
# A pack's skills live in the project (the Book boilerplate's packs), not in this plugin.
PACK_SKILLS = {"check-guides": "fe-guides", "publish-guides": "fe-guides", "release-notes": "fe-guides",
               "deploy": "deploy"}
STEP = re.compile(r"^(\d+)\. (.*)$", re.M)
COMMAND = re.compile(r"`/(book:)?([a-z-]+)")
FRESH_SESSION = ("self-review", "peer-review")


def recipes() -> dict[str, str]:
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(FLOWS.glob("*.md"))}


def section(text: str, heading: str) -> str:
    return text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0] if f"## {heading}\n" in text else ""


def step_skills(text: str) -> list[tuple[int, str, str]]:
    """(step number, skill, the step's line) for each step that starts with a skill call."""
    found = []
    for number, line in STEP.findall(section(text, "Steps")):
        match = COMMAND.match(line.lstrip("⏸✋ "))
        if match:
            found.append((int(number), match.group(2), line))
    return found


class RecipeTests(unittest.TestCase):
    def test_the_eighteen_recipes_are_the_ones_the_skill_lists(self):
        listed = re.findall(r"`([a-z-]+)`", (SKILLS / "flow" / "SKILL.md").read_text(encoding="utf-8")
                            .split("| Group | Flows |", 1)[1].split("\n\n", 1)[0])
        self.assertEqual(sorted(listed), sorted(recipes()))
        self.assertEqual(len(recipes()), 18)

    def test_each_recipe_has_a_trigger_steps_and_done_when(self):
        for name, text in recipes().items():
            with self.subTest(name):
                self.assertTrue(text.startswith(f"# {name}\n"))
                self.assertIn("**Trigger:**", text)
                self.assertTrue(STEP.findall(section(text, "Steps")), "numbered steps")
                self.assertTrue(section(text, "Done when").strip())

    def test_every_skill_a_recipe_names_exists(self):
        for name, text in recipes().items():
            for number, skill, _ in step_skills(text):
                with self.subTest(flow=name, step=number):
                    self.assertTrue(skill in PACK_SKILLS or (SKILLS / skill / "SKILL.md").is_file(), skill)

    def test_every_flow_a_recipe_hands_to_exists(self):
        names = set(recipes())
        for name, text in recipes().items():
            for mentioned in re.findall(r"`([a-z]+(?:-[a-z]+)+)`", section(text, "Steps")):
                if mentioned not in PACK_SKILLS and not (SKILLS / mentioned).is_dir():
                    with self.subTest(flow=name):
                        self.assertIn(mentioned, names, "a flow named in a step")

    def test_the_packs_line_names_exactly_the_packs_the_steps_need(self):
        for name, text in recipes().items():
            needed = sorted({PACK_SKILLS[s] for _, s, _ in step_skills(text) if s in PACK_SKILLS})
            line = re.search(r"\*\*Packs:\*\* ([^.]*)\.", text).group(1)
            with self.subTest(name):
                self.assertEqual(line, ", ".join(needed) if needed else "none")

    def test_each_review_starts_in_a_fresh_session(self):
        for name, text in recipes().items():
            for number, skill, line in step_skills(text):
                if skill in FRESH_SESSION and "again" not in line:
                    with self.subTest(flow=name, step=number):
                        self.assertTrue(line.startswith("⏸"), "a review never runs in the session that wrote it")

    def test_loops_have_a_limit(self):
        for name, text in recipes().items():
            for loop in section(text, "Loops").splitlines():
                if loop.startswith("- ⟲") and "until" in loop and "READY" in loop or "rounds" in loop:
                    with self.subTest(flow=name, loop=loop):
                        self.assertIn("at most 3 rounds", loop)

    def test_every_skill_says_where_it_goes_in_each_flow(self):
        for skill in sorted({s for text in recipes().values() for _, s, _ in step_skills(text)} - set(PACK_SKILLS)):
            body = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
            line = next((l for l in body.split("## What next", 1)[-1].splitlines() if "**In a flow**" in l), "")
            for name, text in recipes().items():
                if any(s == skill for _, s, _ in step_skills(text)):
                    with self.subTest(skill=skill, flow=name):
                        self.assertIn(f"`{name}` →", line)


if __name__ == "__main__":
    unittest.main()
