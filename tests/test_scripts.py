"""
Self-tests for the plugin's helper scripts: sync-sources' heading_guard.py and id_status.py, raise's next_id.py.

    python tests/run.py

Ported from the Book boilerplate's devtools/checks/test_checks.py. The scripts run from the plugin's own
folder, so each test builds a throwaway project with the boilerplate's devtools/checks/ledger_ids.py
(tests/fixtures/ledger_ids.py, from boilerplate v1.2.9). Standard library only; no network. Git runs with
no global or system config, so the developer's own identity, hooks and settings never reach a result.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent / "plugins" / "book" / "skills"
LEDGER_IDS = HERE / "fixtures" / "ledger_ids.py"
HEADING_GUARD = SKILLS / "sync-sources" / "scripts" / "heading_guard.py"
ID_STATUS = SKILLS / "sync-sources" / "scripts" / "id_status.py"
NEXT_ID = SKILLS / "raise" / "scripts" / "next_id.py"
_saved_env: dict[str, str | None] = {}
_empty_config = tempfile.NamedTemporaryFile(delete=False)
_empty_config.close()


def setUpModule() -> None:
    open(_empty_config.name, "a").close()
    isolated = {"GIT_CONFIG_GLOBAL": _empty_config.name, "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CEILING_DIRECTORIES": str(Path(tempfile.gettempdir()).resolve()),
                "GIT_CONFIG_COUNT": "2",
                "GIT_CONFIG_KEY_0": "maintenance.auto", "GIT_CONFIG_VALUE_0": "false",
                "GIT_CONFIG_KEY_1": "gc.auto", "GIT_CONFIG_VALUE_1": "0"}
    for key, value in isolated.items():
        _saved_env[key] = os.environ.get(key)
        os.environ[key] = value


def tearDownModule() -> None:
    for key, value in _saved_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    with contextlib.suppress(FileNotFoundError):
        os.unlink(_empty_config.name)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Repo:
    """A throwaway git repository."""

    def __init__(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name).resolve()
        self.git("init", "-q", "-b", "main")
        self.git("config", "core.autocrlf", "false")

    def git(self, *args: str) -> str:
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                              cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        if done.returncode != 0:
            raise AssertionError(f"git {' '.join(args)}: {done.stderr}")
        return done.stdout

    def write(self, rel: str, content: str | bytes, add: bool = True) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
        if add:
            self.git("add", "--", rel)
        return path

    def add_ledger_ids(self) -> None:
        self.write("devtools/checks/ledger_ids.py", LEDGER_IDS.read_bytes())

    def commit(self, message: str = "Change") -> None:
        self.git("commit", "-q", "--no-verify", "-m", message)

    def close(self) -> None:
        self._dir.cleanup()


class RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repo()
        self.addCleanup(self.repo.close)


def run_main(function, *args, **kwargs) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = function(*args, **kwargs)
    return code, out.getvalue()


@contextlib.contextmanager
def working_directory(path: Path):
    before = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


# ---------------------------------------------------------------- heading_guard

heading_guard = load("heading_guard", HEADING_GUARD)


class HeadingGuardClaimsTests(unittest.TestCase):
    """book:trim's Phase 5 relies on --claims for passages whose claims did not change."""

    BEFORE = ("Deleted users keep their email (D27, FSD-USERS-R04); see [the plan](plans/users.md).\n"
              "Lockout after 5 tries, 15 minutes.\n")

    def test_a_compression_that_keeps_every_claim_loses_nothing(self):
        after = "Deleted users keep their email (D27, FSD-USERS-R04; [plan](plans/users.md)). Lockout: 5 tries, 15 minutes.\n"
        self.assertEqual(heading_guard.lost_claims({"a.md": self.BEFORE}, {"a.md": after}), [])

    def test_a_dropped_id_link_or_number_is_lost_with_the_file_it_was_in(self):
        after = "Deleted users keep their email. Lockout after 5 tries.\n"
        lost = {(kind, token) for kind, token, _, paths in
                heading_guard.lost_claims({"a.md": self.BEFORE}, {"a.md": after}) if paths == ["a.md"]}
        self.assertEqual(lost, {("id", "D27"), ("id", "FSD-USERS-R04"), ("link", "plans/users.md"),
                                ("number", "15")})

    def test_a_passage_moved_into_another_changed_file_is_not_lost(self):
        before = {"a.md": self.BEFORE, "b.md": "# B\n"}
        after = {"a.md": "Moved to B.\n", "b.md": "# B\n\n" + self.BEFORE}
        self.assertEqual(heading_guard.lost_claims(before, after), [])

    def test_a_deleted_file_loses_its_claims(self):
        self.assertTrue(heading_guard.lost_claims({"a.md": self.BEFORE}, {}))

    def test_a_claim_held_twice_and_kept_once_is_lost_once(self):
        lost = heading_guard.lost_claims({"a.md": "D27 and D27\n"}, {"a.md": "D27\n"})
        self.assertEqual(lost, [("id", "D27", 1, ["a.md"])])


# ---------------------------------------------------------------- id_status

QUESTIONS = ("# Questions\n\n## Still open\n\n| Q | What |\n|---|---|\n| [Q1](#q1) | x |\n\n"
             "#### Q1 — Is it?\n\nAsked.\n\n## Superseded\n")
DEFECTS = ("# Defects\n\n## Open\n\n| Id | Sev | Status | Defect |\n|---|---|---|---|\n"
           "| D3 | 🔵 | Open | Still wrong |\n\n## Fixed\n\n"
           "- **D21** — the save broke when the folder was open; fixed. Fixed on `fix/D21-save`.\n")
CLOSED = "# Closed defects\n\n## Fixed\n\n| Id | Sev | Defect |\n|---|---|---|\n| D7 | 🔵 | Old one |\n"


def id_status(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ID_STATUS), *args], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd)


class IdStatusTests(unittest.TestCase):
    """The skill's stale-citation pass: a fixed defect is a one-line entry under Fixed."""

    def run_on(self, citing: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory) / "docs"
            (docs / "archive").mkdir(parents=True)
            checks = Path(directory) / "devtools" / "checks"
            checks.mkdir(parents=True)
            shutil.copy(LEDGER_IDS, checks / "ledger_ids.py")
            (docs / "open-questions.md").write_text(QUESTIONS, encoding="utf-8")
            (docs / "defects.md").write_text(DEFECTS, encoding="utf-8")
            (docs / "archive" / "defects-closed.md").write_text(CLOSED, encoding="utf-8")
            (docs / "plan.md").write_text(citing, encoding="utf-8")
            done = id_status(directory)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_a_fixed_entry_or_an_archived_row_cited_as_open_is_flagged(self):
        out = self.run_on("The upload waits on D21, still open.\nAnd D7 remains open.\n")
        self.assertIn("plan.md:1  D21  closed, cited as open", out)
        self.assertIn("plan.md:2  D7  closed, cited as open", out)
        self.assertNotIn("defects.md:", out, "a defect's own Fixed entry is not a citation")
        self.assertIn("2 candidates", out)

    def test_an_open_defect_cited_as_fixed_is_flagged_and_a_true_citation_is_not(self):
        out = self.run_on("D3 is fixed now.\nD21 was fixed.\n")
        self.assertIn("plan.md:1  D3  open, cited as closed", out)
        self.assertIn("1 candidates", out)


class IdStatusProjectRootTests(RepoTestCase):
    """id_status.py runs from the plugin's folder: the project is the git top level of where it is run."""

    def setUp(self) -> None:
        super().setUp()
        self.repo.write("docs/open-questions.md", QUESTIONS)
        self.repo.write("docs/defects.md", DEFECTS)
        self.repo.write("docs/archive/defects-closed.md", CLOSED)
        self.repo.write("docs/plan.md", "D3 is fixed now.\n")

    def test_run_from_a_subfolder_it_reads_the_project_at_the_git_top_level(self):
        self.repo.add_ledger_ids()
        done = id_status(cwd=self.repo.root / "docs")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("plan.md:1  D3  open, cited as closed", done.stdout)

    def test_a_project_without_ledger_ids_could_not_be_checked(self):
        done = id_status(cwd=self.repo.root)
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("could not check", done.stderr)
        self.assertIn("devtools/checks/ledger_ids.py", done.stderr)

    def test_outside_a_git_repository_it_could_not_be_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            done = id_status(cwd=Path(directory))
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("could not check", done.stderr)


# ---------------------------------------------------------------- next_id

class NextIdTests(RepoTestCase):
    """book:raise's next_id.py: the next D and Q free on every branch, never only the one checked out."""

    def setUp(self) -> None:
        super().setUp()
        self.next_id = load("next_id", NEXT_ID)
        self.repo.add_ledger_ids()
        self.repo.write("devtools/factory/factory.toml", 'base_ref = "main"\n')
        self.repo.write("docs/defects.md", "## Open\n\n| Id | Sev |\n|---|---|\n| D3 | 🔵 |\n\n## Fixed\n\n- **D2** — x.\n")
        self.repo.write("docs/open-questions.md", "## Still open\n\n#### Q2 · Default?\n")
        self.repo.commit()

    def test_the_highest_id_on_any_branch_or_the_working_tree_is_taken(self):
        self.repo.git("checkout", "-q", "-b", "fix/other")
        self.repo.write("docs/archive/defects-closed.md", "| **D5** | 🔵 | Fixed |\n")
        self.repo.commit()
        self.repo.git("checkout", "-q", "main")
        self.repo.write("docs/open-questions.md", "## Still open\n\n#### Q2 · Default?\n\n#### Q7 — New?\n", add=False)
        code, out = run_main(self.next_id.main, [str(self.repo.root)])
        self.assertEqual(0, code, out)
        self.assertIn("next D: D6  (highest D5, on fix/other)", out)
        self.assertIn("next Q: Q8  (highest Q7, on working tree)", out)

    def test_an_id_mentioned_loosely_does_not_count_and_ties_go_to_the_first_source(self):
        # A text whose loose bound (D9 in prose) is high but whose ledger rows are not must not win.
        self.repo.git("checkout", "-q", "-b", "chore/notes")
        self.repo.write("docs/defects.md", "## Open\n\nSee D9 in the notes.\n\n| Id | Sev |\n|---|---|\n| D3 | 🔵 |\n")
        self.repo.commit()
        self.repo.git("checkout", "-q", "main")
        code, out = run_main(self.next_id.main, [str(self.repo.root)])
        self.assertEqual(0, code, out)
        self.assertIn("next D: D4  (highest D3, on main)", out)

    def test_the_ledgers_of_every_branch_are_read_in_one_batch(self):
        self.repo.git("checkout", "-q", "-b", "fix/other")
        self.repo.write("docs/archive/defects-closed.md", "| **D5** | 🔵 | Fixed |\n")
        self.repo.commit()
        self.repo.git("checkout", "-q", "main")
        blobs = self.next_id.read_blobs(self.repo.root, ["main:docs/defects.md", "fix/other:docs/archive/defects-closed.md",
                                                         "main:docs/archive/defects-closed.md", "nope:docs/defects.md"])
        self.assertEqual({"main:docs/defects.md", "fix/other:docs/archive/defects-closed.md"}, set(blobs))
        self.assertIn("| D3 |", blobs["main:docs/defects.md"])
        self.assertEqual("| **D5** | 🔵 | Fixed |\n", blobs["fix/other:docs/archive/defects-closed.md"])

    def test_a_base_that_is_not_here_stops_with_could_not_check(self):
        self.repo.write("devtools/factory/factory.toml", 'base_ref = "origin/dev"\n', add=False)
        code, out = run_main(self.next_id.main, [str(self.repo.root)])
        self.assertEqual(2, code)
        self.assertIn("fetch it first", out)
        self.repo.write("devtools/factory/factory.toml", "", add=False)
        code, out = run_main(self.next_id.main, [str(self.repo.root)])
        self.assertEqual(2, code)
        self.assertIn("sets no base_ref", out)

    def test_a_book_with_a_settings_loader_reads_the_base_through_it(self):
        # From Book 1.6 a value equal to the Book's default leaves factory.toml; the project's loader merges it back.
        self.repo.write("devtools/factory/factory.toml", "", add=False)
        self.repo.write("devtools/factory/book_config.py",
                        "def load(root):\n    return {'base_ref': 'main'}\n", add=False)
        self.assertEqual("main", self.next_id.base_ref(self.repo.root))
        self.repo.write("devtools/factory/book_config.py", "def load(root):\n    raise ValueError('bad')\n", add=False)
        with self.assertRaises(self.next_id.CouldNotCheck):
            self.next_id.base_ref(self.repo.root)

    def test_a_remote_and_its_head_are_read_once(self):
        self.repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.repo.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        self.assertEqual([("refs/heads/main", "main"), ("refs/remotes/origin/main", "origin/main")],
                         self.next_id.refs(self.repo.root, "main"))

    def test_a_branch_is_read_by_its_full_name_where_a_tag_shares_its_short_name(self):
        # A tag fix/other on an older commit: the short name reads the tag, the full name the branch (Book D58).
        self.repo.git("tag", "fix/other")
        self.repo.git("checkout", "-q", "-b", "fix/other")
        self.repo.write("docs/archive/defects-closed.md", "| **D5** | 🔵 | Fixed |\n")
        self.repo.commit()
        self.repo.git("checkout", "-q", "main")
        code, out = run_main(self.next_id.main, [str(self.repo.root)])
        self.assertEqual(0, code, out)
        self.assertIn("next D: D6  (highest D5, on fix/other)", out)

    def test_with_no_argument_the_project_is_the_git_top_level_of_the_current_directory(self):
        with working_directory(self.repo.root / "docs"):
            code, out = run_main(self.next_id.main, [])
        self.assertEqual(0, code, out)
        self.assertIn("next D: D4  (highest D3, on main)", out)
        self.assertIn("next Q: Q3  (highest Q2, on main)", out)

    def test_a_project_without_ledger_ids_could_not_be_checked(self):
        self.repo.git("rm", "-q", "devtools/checks/ledger_ids.py")
        code, out = run_main(self.next_id.main, [str(self.repo.root)])
        self.assertEqual(2, code, out)
        self.assertIn("could not check", out)
        self.assertIn("devtools/checks/ledger_ids.py", out)

    def test_outside_a_git_repository_it_could_not_be_checked(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(Path(directory)):
            code, out = run_main(self.next_id.main, [])
        self.assertEqual(2, code, out)
        self.assertIn("could not check", out)

    def test_the_skill_calls_it_from_its_own_folder(self):
        text = (SKILLS / "raise" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn('python "${CLAUDE_SKILL_DIR}/scripts/next_id.py"', text)
        self.assertIn('Bash(python "${CLAUDE_SKILL_DIR}/scripts/next_id.py"*)', text)


if __name__ == "__main__":
    unittest.main()
