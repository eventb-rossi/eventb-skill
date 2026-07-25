# Contributing

Thanks for helping improve the Event-B skill. This file covers the workflow; the
substance — what makes a good reference, what claims are allowed about assurance, which
source wins a disagreement — is in [AGENTS.md](AGENTS.md). Read that before changing the
skill's content.

## Setup

You need Python 3.9+ for the tooling. To run the Event-B gates you also need `rossi`
0.1.8+ and `eventb-animate` 6.4+ on `PATH`; see [docs/install.md](docs/install.md).

```sh
git clone https://github.com/eventb-rossi/eventb-skill
cd eventb-skill
make check          # no external tools needed
make check-models   # requires rossi and eventb-animate
```

There are no dependencies to install: the scripts use only the Python standard library.

## Before you open a pull request

```sh
make check          # spec conformance, conventions, catalog drift
make check-models   # only if you touched skills/*/examples/
```

CI runs both, plus the specification's own reference validator, `rossi-action` (which
annotates every finding on the diff and publishes it to code scanning), a validation pass
over the built Rodin archives, and `eventb-checker` — a JVM checker of Rodin's static
rules — over those same archives, so the static checks have a second implementation behind
them and not just rossi. If `make check` passes locally it will normally pass there —
`make check-models` uses `rossi validate --deny-warnings`, the same gate CI applies, so an
advisory lint fails on your machine too.

## What to change where

| Change | Where |
|---|---|
| The workflow every run follows | `skills/eventb/SKILL.md` (keep it under 500 lines) |
| Detail needed occasionally | a file in `skills/eventb/references/` **plus** a routing-table row |
| A worked model | `skills/eventb/examples/<name>/` with a `README.md` |
| A convention worth enforcing | a rule in `scripts/validate.py`, not a paragraph of prose |
| Installation or client specifics | `docs/install.md` |

`skills/index.json` and `llms.txt` are generated. Run `make build`; never edit them
directly.

## Pull requests

- One concern per pull request. A content change and a tooling change are two PRs.
- Conventional commit subjects: `feat(skill):`, `refactor(references):`, `docs:`,
  `build:`, `ci:`, `fix:`.
- Bump `metadata.version` in the skill's frontmatter when its content changes.
- In the description, say what you verified and how. For a model, paste the check
  commands and their result.

## Adding a reference

The four steps are in [AGENTS.md](AGENTS.md#adding-or-changing-a-reference); the one that
gets forgotten is the routing-table row. A reference nothing routes to never gets read, so
validation rejects it.

## Reporting a problem

Open an issue with the smallest `.eventb` input that shows it, the exact commands you ran,
and the output including tool versions (`rossi --version`, `eventb-animate --version`).

If the problem is in `rossi` or `eventb-animate` rather than in the skill's guidance,
report it on [rossi](https://github.com/eventb-rossi/rossi/issues) or
[eventb-animate](https://github.com/eventb-rossi/eventb-animate/issues) — and if this
repository documented the wrong behaviour, please open an issue here too so the reference
gets corrected.

## License

Contributions are accepted under [Apache-2.0](LICENSE), the license of this repository.
