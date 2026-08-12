# Event-B Agent Skills

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-1.0-6f42c1.svg)](https://agentskills.io/specification)
[![skills.sh](https://skills.sh/b/eventb-rossi/eventb-skill)](https://skills.sh/eventb-rossi/eventb-skill)
[![CI](https://github.com/eventb-rossi/eventb-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/eventb-rossi/eventb-skill/actions/workflows/ci.yml)

An [Agent Skill](https://agentskills.io/specification) that teaches a coding agent to
write **Event-B** formal models as `.eventb` text and to check them, rather than to
produce specification-shaped prose that has never been run. An Event-B model is a
discrete transition system: a `CONTEXT` holds fixed sets, constants and axioms; a
`MACHINE` holds variables, invariants and guarded events.

The skill's core loop is a gate, not a suggestion. Every model it delivers is formatted
and statically checked by [rossi](https://github.com/eventb-rossi/rossi), built into an
archive, model-checked with ProB through
[eventb-animate](https://github.com/eventb-rossi/eventb-animate), and put through the
well-definedness obligations — and the skill states plainly what a clean run does and
does not prove.

**Out of scope, deliberately:** authoring interactive Rodin proofs. Model checking
explores reachable behaviour; it does not discharge Event-B's invariant and refinement
proof obligations. The skill says so where it matters instead of implying more assurance
than it delivers.

## Install

```sh
npx skills add eventb-rossi/eventb-skill
```

That works for any client the [skills CLI](https://github.com/vercel-labs/skills)
supports, including Claude Code, Codex, Cursor, Windsurf and VS Code. For manual
installation or per-client paths, see [docs/install.md](docs/install.md).

## Prerequisites

The skill drives two command-line tools and checks for them before it starts modelling.
It will never install or upgrade them itself — if either is missing, it stops and asks.

| Tool | Minimum | Purpose |
|---|---|---|
| [`rossi`](https://github.com/eventb-rossi/rossi) | 0.1.8 | Parser, static checker, formatter, Rodin round-tripping |
| [`eventb-animate`](https://github.com/eventb-rossi/eventb-animate) | 6.4 | ProB model checking, well-definedness gates, trace replay (needs Java 21+) |

```sh
brew install eventb-rossi/tap/rossi eventb-rossi/tap/eventb-animate
```

Debian/Ubuntu (APT), Fedora (COPR) and Windows (Scoop) packages are listed in
[docs/install.md](docs/install.md).

## Skills

| Skill | Description |
|---|---|
| [`eventb`](skills/eventb/SKILL.md) | Write and check Event-B models: contexts, machines, invariants, events, and justified refinement chains. |

## What the skill contains

`SKILL.md` is 189 lines — the workflow an agent needs on every run, and a routing table
that names exactly one file per question. Everything else is loaded only when that
question comes up.

| Reference | Lines | The agent reads it when it needs |
|---|---|---|
| [`syntax.md`](skills/eventb/references/syntax.md) | 215 | Exact `.eventb` grammar, component and action forms |
| [`math-toolkit.md`](skills/eventb/references/math-toolkit.md) | 196 | An operator, its ASCII spelling, or its precedence |
| [`modelling.md`](skills/eventb/references/modelling.md) | 192 | Help choosing state, invariants or events |
| [`refinement.md`](skills/eventb/references/refinement.md) | 332 | A genuine refinement step, or a chain to plan |
| [`patterns.md`](skills/eventb/references/patterns.md) | 158 | A core reactive-system pattern |
| [`patterns-control.md`](skills/eventb/references/patterns-control.md) | 258 | Discrete time, deadlines, modes, sensors and actuators |
| [`patterns-distributed.md`](skills/eventb/references/patterns-distributed.md) | 193 | Topology, rounds, consensus, channels, long-running operations |
| [`patterns-security.md`](skills/eventb/references/patterns-security.md) | 89 | Access control, authorization policy, reservation |
| [`patterns-algorithms.md`](skills/eventb/references/patterns-algorithms.md) | 156 | A loop derived from a postcondition, or an interpreter |
| [`tooling.md`](skills/eventb/references/tooling.md) | 411 | CLI troubleshooting or a conditional advanced command |
| [`best-practices.md`](skills/eventb/references/best-practices.md) | 193 | A final design review |

Three worked developments ship with the skill. Each is a real project directory that CI
formats, validates, builds, model-checks and WD-checks at **every** refinement level:

| Example | Levels | What it demonstrates |
|---|---|---|
| [`counter`](skills/eventb/examples/counter/) | 2 | The mechanics of refinement — `REFINES`, gluing invariants, `WITH` witnesses — with no domain noise |
| [`cars_on_bridge`](skills/eventb/examples/cars_on_bridge/) | 3 | The canonical refinement chain: count cars, data-refine to per-section counters with a `VARIANT`, then superpose traffic lights |
| [`array_maximum`](skills/eventb/examples/array_maximum/) | 3 | Deriving a loop from a postcondition: counter, termination variant, partial-progress invariant |

## How it works

Skills load in tiers, and this one is built for that:

1. **Metadata** — `name` and `description` are in context from the start, so the agent
   knows the skill exists and when it applies (~100 tokens).
2. **Instructions** — the `SKILL.md` body loads when the skill activates: check the
   tools, scope the model, author the smallest useful model, run the core gate, add
   targeted evidence, deliver a readable artifact.
3. **Resources** — a reference or example loads only when the routing table sends the
   agent there. No reference exceeds 420 lines, so no single load is expensive.

For clients with no skills support, [`llms.txt`](llms.txt) and
[`skills/index.json`](skills/index.json) list every file with a raw URL, so an agent can
fetch just the entry point or a single reference on demand.

## Repository structure

```
skills/eventb/            the skill — the only directory a user installs
├── SKILL.md              workflow, core gate, routing table
├── references/           11 focused references, loaded on demand
├── examples/             3 worked developments, checked in CI
└── agents/openai.yaml    Codex interface metadata
skills/index.json         GENERATED catalog
llms.txt                  GENERATED remote-discovery index
scripts/validate.py       spec conformance, conventions, Event-B gates
scripts/build_index.py    catalog generator with a --check drift gate
docs/install.md           per-client installation
AGENTS.md                 contributor spec (also read as CLAUDE.md)
```

## Development

```sh
make check         # spec + convention rules, then catalog drift (no external tools)
make check-models  # the full gate; needs rossi and eventb-animate on PATH
make build         # regenerate skills/index.json and llms.txt
```

`make check` is the gate to run before every commit. `skills/index.json` and `llms.txt`
are generated — never edit them by hand; `make check` fails if they drift.

### Validation rules

`scripts/validate.py` enforces the conventions rather than documenting them:

- **Spec conformance** — frontmatter starts at byte 0, only the six fields the
  specification allows, and the `name`, `description` and `compatibility` constraints.
  `name` must equal its directory name. `metadata` values must be quoted, because an
  unquoted `1.0` is a string under strictyaml and a float under PyYAML.
- **Budgets** — `SKILL.md` at most 500 lines, each reference at most 420. Split a file
  that outgrows its budget; do not raise the limit.
- **Structure** — every reference is named in the routing table (no orphans), every
  routed path exists, every relative link resolves inside the skill, no absolute paths,
  no unfinished markers, every example documented by its own README, and no `SKILL.md`
  outside `skills/` that `skills add --full-depth` would publish by accident.
- **Event-B gates** — every example formatted, validated, built, model-checked and
  WD-checked at every refinement level, with `--require-tools` for CI. Validation uses
  `rossi validate --deny-warnings`, so an example must be free of rossi's advisory lints
  and not merely free of errors.

### Adding or changing a reference

1. Write the file in `skills/<skill>/references/`, one concern per file.
2. Add a row to the `SKILL.md` routing table saying **when** to read it. A reference
   nothing routes to is an orphan and fails validation.
3. `make build` to regenerate the catalogs.
4. `make check`, then `make check-models` if you touched an example.
5. Bump `metadata.version` in the skill's frontmatter.

### Writing guidelines

Every `.eventb` snippet that claims to be checkable must pass `rossi validate` — rossi's
parser is the ground truth, not any document. Keep "when to use this" in the
`description` frontmatter, where a client can match it before loading the body. State
what a check does *not* prove wherever it would otherwise be overread.

See [AGENTS.md](AGENTS.md) for the full contributor spec and
[CONTRIBUTING.md](CONTRIBUTING.md) for the workflow.

## Related

- [rossi](https://github.com/eventb-rossi/rossi) — Rust toolchain for Event-B: parser, static checker, CLI, LSP
- [eventb-animate](https://github.com/eventb-rossi/eventb-animate) — ProB-backed model checking without Rodin
- [rossi-action](https://github.com/eventb-rossi/rossi-action) — GitHub Action running rossi over your models; used by this repository's CI
- [eventb-checker](https://github.com/eventb-rossi/eventb-checker) — JVM model validator with a GitHub Action; used by this repository's CI as a second opinion on the static checks
- [rodin-headless](https://github.com/eventb-rossi/rodin-headless) — headless Rodin build, model-check and prove
- [tree-sitter-eventb](https://github.com/eventb-rossi/tree-sitter-eventb) — grammar for the `.eventb` syntax
- [awesome-event-b](https://github.com/eventb-rossi/awesome-event-b) — curated Event-B resources

## License

[Apache-2.0](LICENSE).
