# Book plugin

The Book's AI skills and agents, packaged as one Claude Code plugin named `book`. Its skills are called
with the plugin's name in front: `/book:self-review`, `/book:commit`, `/book:check-sources`.

## What is here, and what is not

- **Here:** the skills (`plugins/book/skills/`) and the reviewer and tester agents (`plugins/book/agents/`).
- **Not here, by design:** a project's docs, its `devtools/factory/factory.toml`, its checks and scripts,
  its git hooks and its guard. CI and the hooks must find those inside the repository, and the guard
  must protect everyone who opens it, whether or not they installed this plugin. They come from the
  Book boilerplate.

A skill reads a project's files by their path from the project's root (`CLAUDE.md`, `docs/project.md`),
and its own helper scripts through `${CLAUDE_SKILL_DIR}`.

## The skills

| Skill | What it does | Formerly |
|---|---|---|
| `/book:flow` | Lists the 18 ready-made recipes (which skills, in what order, where a person decides), or walks one | — (new in 0.3.0) |
| `/book:setup` | Sets up the Book in a repository, or checks it is ready | `/book-setup` |
| `/book:upgrade` | Moves a Book to a newer template release | `/book-upgrade` |
| `/book:check-sources` | Checks the client's documents are current | `/requirements-check` |
| `/book:sync-sources` | Carries a new requirements revision through the whole Book | `/requirements-sync` |
| `/book:plan` | Starts a feature's plan from the template | `/plan-feature` |
| `/book:outline-api` | Drafts the API a screen needs, before it is built | `/api-contract-draft` |
| `/book:impact` | Lists what a change reaches, and the tests to run | `/change-impact` |
| `/book:raise` | Writes one defect or question, with the next free id | — |
| `/book:self-review` | Reviews a branch before its commit or pull request | `/review-branch` |
| `/book:peer-review` | Reviews an open pull request and posts the findings | `/review-pr` |
| `/book:commit` | Reviews, then commits in logical groups | — |
| `/book:ship` | Runs the local CI and opens the pull request when asked | — |
| `/book:fact-check` | Checks the code and the plans against the FSD | `/fsd-audit` |
| `/book:check-docs` | Checks the docs against the code, both ways | `/docs-vs-code` |
| `/book:check-permissions` | Checks who may do what: the FSD's role rules against authorization §2 and the code; reports gaps, writes nothing | — (new in 0.4.0) |
| `/book:update-docs` | Brings the docs in line with code known to be right | `/docs-update-from-code` |
| `/book:check-consistency` | Finds docs that disagree or repeat each other | `/docs-consistency` |
| `/book:trim` | Trims and restructures the docs without losing anything | `/docs-trim` |
| `/book:progress` | Brings the task lists up to date with what merged | `/project-progress` |
| `/book:write-for` | A short message for a named non-engineer | — |

The agents are `book:reviewer` (formerly `book-reviewer`) and `book:tester` (formerly `book-tester`).
From Book template v1.5.0 the old names do nothing: a project keeps no stub under them.

From 0.5.0 the packs' skills are here too, and apply only where the project's `[book] packs` (in
`devtools/factory/factory.toml`) installed the pack; elsewhere they say so and stop. Their project facts
stay in `factory.toml`: `[fe_guides]` (the Drive folder, the internal error codes, the owners) and
`[deploy]` (the host, the environments, the runbook).

| Skill | Pack | Was, in the project |
|---|---|---|
| `/book:check-guides` | fe-guides | `/check-guides` (`/fe-guides-check` before 1.3) |
| `/book:publish-guides` | fe-guides | `/publish-guides` (`/fe-guides-publish` before 1.3) |
| `/book:release-notes` | fe-guides | `/release-notes` |
| `/book:deploy` | deploy | `/deploy` (`/deploy-dev-qa` before 1.3) |

Book template v1.5.0 needs this plugin at 0.6.0 or later (its `plugin_min`). From 0.6.0 a skill runs only
`python devtools/book.py`, the Book's command since template v1.4.0; a Book that pins 0.6.0 is on 1.5.0.

## Use it

```
claude plugin marketplace add SalmanslK/book-plugin
claude plugin install book@book-plugins
```

A project names it in its shared `.claude/settings.json` (`extraKnownMarketplaces` and
`enabledPlugins`), so everyone who opens the project is offered it.

## Change it

Edit the skills here, bump `version` in `plugins/book/.claude-plugin/plugin.json`, and run these before
committing. Push this plugin's release tag (v0.6.0) before the boilerplate release whose settings pin it (v1.5.0).

```
python tests/run.py
claude plugin validate plugins/book
claude plugin validate .
```

`tests/run.py` runs the self-tests of the skills' helper scripts and then `tests/check_skills.py`, which
checks every skill and agent loads: frontmatter, names, a `## What next` section, each description at
most 1,024 characters and all of them together under 9,000. It needs Python 3.11 or later and git, and
nothing else. A helper script finds the project from the folder it is run in (its git top level) and
reads the ledgers with that project's own `devtools/checks/ledger_ids.py` (and `/book:check-guides`, the
owner rule with its `devtools/checks/check-fe-guides.py`); the tests use copies of them from the
boilerplate in `tests/fixtures/`.

## Licence

Licensed for use only: see [LICENSE](LICENSE). You may install and use it in the projects you
work on; you may not redistribute it, or present it as your own, without the author's written
permission. Copyright (c) 2026 Salman Khan.
