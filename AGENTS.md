# Working on this repository

This file is for an agent (or person) editing **the skill itself**. For using the skill,
read [`skills/eventb/SKILL.md`](skills/eventb/SKILL.md). For the repository overview, read
[README.md](README.md).

Run `make check` before every commit, and `make check-models` when you touch an example.

## Sources of truth, in order

1. **`rossi`'s parser.** If a document and `rossi validate` disagree about `.eventb`
   syntax, the document is wrong. Never write a snippet you have not run.
2. **The tools' `--help` and JSON reports.** Flags, exit codes and report fields come
   from the installed binary, not from memory. `eventb-animate`'s report is format
   version 3 with `status`, `completion.classification` and `checks[]` — check the actual
   output before describing it.
3. **The [Agent Skills specification](https://agentskills.io/specification).** It defines
   the frontmatter and layout. Where it only recommends (500 lines, 5000 tokens), this
   repository enforces a concrete number in `scripts/validate.py`.
4. **Published Event-B developments** for the pattern references, with a link in the
   `Evidence:` line so a reader can go check.

## Never hand-edit generated files

`skills/index.json` and `llms.txt` are produced by `scripts/build_index.py`. Change the
frontmatter or the layout and run `make build`. `make check` fails on drift, so a
hand-edit will be caught, but it wastes a round trip.

## Adding or changing a reference

Do all four, in order — missing any one leaves the tree inconsistent:

1. Create the file under `skills/<skill>/references/`, one concern per file, at most 420
   lines. Give it a `# Title` first line: the generated catalogs use it as link text.
2. Add a row to the `SKILL.md` §3 routing table stating **when** to read it, phrased as
   the question the agent will actually have. A reference nothing routes to is an orphan
   and fails validation — that rule exists so `SKILL.md` stays a complete index of its own
   directory.
3. `make build` to regenerate the catalogs.
4. `make check`, and bump `metadata.version` in the skill's frontmatter.

If a reference outgrows 420 lines, **split it by topic**. Do not raise the limit: the
whole file is loaded to answer one question, so length is a direct cost to every use.
`references/tooling.md` at 411 lines is the accepted maximum because it is a single CLI
surface that would be worse split in two.

## Writing the skill body

- Keep "when to use this" in the `description` frontmatter, not in the body. A client
  matches the description against a task *before* loading the body.
- `SKILL.md` is the workflow, not the manual. If content answers an occasional question,
  it belongs in a reference with a routing-table row.
- Prefer an accept criterion over an instruction. "Require `status: "ok"` and no invariant
  violation" is checkable; "make sure the model is correct" is not.
- Quote `metadata` values. An unquoted `1.0` is a string under strictyaml and a float
  under PyYAML, and clients use whichever YAML library they already have.

## Claims about assurance

This is the easiest thing to get wrong and the most damaging. The skill checks reachable
behaviour with ProB and gates well-definedness. It does **not** discharge Event-B's
invariant or refinement proof obligations.

- A clean bounded run means "no bug found within the bound" — never "correct".
- A complete finite run proves something about the checked *reachable* behaviour. It can
  still accept an over-strong, non-inductive invariant, because the violating states are
  unreachable.
- An exit code of zero is not evidence of completeness. `completion.classification` is.

Do not soften these into implied proof, and keep the caveat next to the claim it
qualifies rather than in a footnote.

## Versions

`SKILL.md` §1 names the minimum `rossi` and `eventb-animate` versions, and the
`compatibility` frontmatter repeats them. Those floors must be versions the examples were
actually checked against — CI checks them on every push, so raise the floor only together
with a green `make check-models` on the new version.

The number lives in more places than those two, and nothing enforces agreement between
them: `grep -rn <old-version> --exclude-dir=.git` and change every hit. Raising the floors
to rossi 0.1.8 and `eventb-animate` 6.4 meant `SKILL.md` (×2), `references/tooling.md`,
`README.md`, `docs/install.md` (×2), `CONTRIBUTING.md`, `scripts/build_index.py`,
`scripts/validate.py` and `.github/workflows/ci.yml` — then `make build`, because the
catalogs embed the `compatibility` string and the generated prerequisites blurb.

## Examples

An example is a real project directory, not an illustration: CI formats, validates,
builds, model-checks and WD-checks it at every refinement level. So

- keep every example small enough to check quickly;
- put the explanation in the example's `README.md`, never as comments in `.eventb`;
- list every `.eventb` file in that README (validation enforces it);
- name the example in `SKILL.md` and say when reading it is worth the tokens;
- keep it clean under `rossi validate --deny-warnings`. An advisory lint — a dead variable,
  an unmodified variable, an incomplete `INITIALISATION`, a shadowed name — exits 0 on its
  own, but both `make check-models` and CI fail on it here, because an example teaches
  whatever it contains.

Illustrative fragments that are not standalone-checkable belong in a reference, and that
reference must say so — the `patterns-*.md` files each state it in their lead paragraph.

## Commits

- Conventional commit subjects, scoped when it helps: `feat(skill):`,
  `refactor(references):`, `build:`, `ci:`, `docs:`.
- One concern per commit. The reference split and the frontmatter change were separate
  commits precisely so each diff could be read on its own.
- Say what you verified in the body, with the command or the observed output. "Verified:
  `skills-ref validate` reports Valid skill" is worth more than "tested".
