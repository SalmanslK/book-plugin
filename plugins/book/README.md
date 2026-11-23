# Book plugin

The Book plugin gives Claude Code the skills and agents for a project made from the Book boilerplate.
The Book is a set of documents that say what a project builds, why, how, and what is done, kept true
by checks in the project's own repository. This plugin carries the skills that work on those documents:
plan a feature, raise a defect or a question, review a branch or a pull request, commit and ship,
check the client's requirements, keep the docs consistent, track progress, and set up or upgrade a
Book. Skills are called with the plugin's name in front, such as `/book:self-review` or `/book:plan`.

It works only on a project made from the Book boilerplate. The project keeps its own docs, settings,
checks and guard; this plugin reads them from the project's root and runs the project's command,
`python devtools/book.py`.

## Install

```
claude plugin marketplace add SalmanslK/book-plugin
claude plugin install book@book-plugins
```

A Book names the plugin in its shared `.claude/settings.json`, pinned to a release tag, so everyone who
opens the project is offered the same version.

## Headless runs

A headless session (`claude -p`) in the default permission mode refuses a shell command that chains or
pipes (`&&`, `;`, `|`, `$(…)`, a `for` loop) unless the permission rules allow every command in it,
because nobody is there to approve it. The skills prefer the Grep and Glob tools and one command per
call. Where a recipe still pipes (the `pdftotext` recipes in `fact-check/references/reading-the-fsd.md`,
the PDF fingerprint in `check-sources/references/diffing-and-capturing.md`), run that step
interactively, or start the run with each command allowed, for example
`claude -p --allowedTools "Bash(pdftotext *)" "Bash(awk *)" "Bash(wc *)" "Bash(git *)" …`.

## Licence

All rights reserved, with use permitted as the [LICENSE](LICENSE) file in this folder sets out.
