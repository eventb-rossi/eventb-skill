# Tooling: `rossi`, `eventb-animate`

Use `rossi` to parse, format, validate, build, and convert `.eventb` text models.
Use `eventb-animate` to model-check the checked Rodin artifacts, preserve and
replay traces, emit reports, and gate on proof obligations.

**Priority:** normal authoring needs only `fmt`, directory `validate`, zip `build`,
the default ProB check with a JSON report, and `wd`. Add goal/replay for a specific
scenario. Test generation, symbolic modes, Rodin proof-status gating, interchange,
and LTSmin are conditional workflows, not extra boxes to tick on every model.

## Contents

- [Versions and prerequisites](#versions-and-prerequisites)
- [Core loop](#core-loop)
- [`rossi` commands](#rossi-commands)
- [Default ProB model checking](#default-prob-model-checking)
- [LTSmin backends](#ltsmin-backends)
- [Reports are not traces](#reports-are-not-traces)
- [Proof-obligation gates](#proof-obligation-gates)
- [Other `eventb-animate` commands](#other-eventb-animate-commands)
- [Which tool when](#which-tool-when)

## Versions and prerequisites

Require these tested minimum versions:

| Tool | Minimum | Role |
|---|---:|---|
| `rossi` | 0.2.0 | text parser/formatter, static checker, Rodin conversion, LSP |
| `eventb-animate` | 6.4 | ProB/LTSmin model checking, report v3, trace v6, replay, proof gates |
| LTSmin tools | 3.0.2 | optional sequential/symbolic external backends |

Check versions; never install or upgrade tools without the user's approval:

```sh
command -v rossi eventb-animate
rossi --version
eventb-animate --version
```

The default ProB backend is bundled with `eventb-animate`. Only check LTSmin
when the user requests that backend or it is otherwise justified:

```sh
command -v prob2lts-seq prob2lts-sym ltsmin-printtrace
prob2lts-seq --version
prob2lts-sym --version
ltsmin-printtrace --version
```

LTSmin is optional and unavailable on Windows. For tools installed outside
`PATH`, pass their directory as `-p LTSMIN=/absolute/path`.

## Core loop

```sh
rossi fmt -i .                                      # 1. canonicalize
rossi validate .                                    # 2. semantic + project lints
rossi build . -o /tmp/model.zip                     # 3. emit .bcc/.bcm
eventb-animate --json /tmp/report.json /tmp/model.zip  # 4. check + report
eventb-animate wd /tmp/model.zip                     # 5. well-definedness gate
```

`rossi build` fails on error diagnostics. It produces the checked `.bcm`/`.bcc`
files that `eventb-animate` loads. `rossi export` writes source `.bum`/`.buc`
files only, so an exported archive is not a substitute for `build` when model
checking.

Read warnings as well as the exit code: a missing/ill-typed refinement witness may
be reported as `event is inaccurate` without making `validate` or `build` fail.
Treat that warning as a failed gate.

Use the default ProB backend first. It supports the complete check surface,
counterexample traces, event coverage, goals, LTL, and ProB's symbolic modes.
Select LTSmin deliberately for its alternate sequential or symbolic engines.

## `rossi` commands

### `rossi validate <FILE…>`

Parse and check `.eventb` files, Rodin `.zip` archives, or Rodin project
directories. `-` reads text from stdin; use `--stdin-filename` to control its
reported path.

- `-f, --format text|json|sarif` selects diagnostic output.
- `-q, --quiet` prints errors only.
- `-c, --continue-on-error` continues after a failing input.
- `--no-semantic` performs syntax-only checking where supported.
- `--no-lints` keeps semantic checks but suppresses advisory lints.
- `--deny-warnings` exits nonzero on advisory diagnostics too. Severities are
  unchanged — a warning stays a warning in every format, only the exit code hardens.
- `-o, --output <FILE>` writes the whole report to a file in any format, including
  the rows that would otherwise go to stderr.
- `--sarif-category <NAME>` names the SARIF run's analysis category, keeping several
  uploads from one repository apart.

Without `--deny-warnings`, `validate` exits 0 on an advisory lint: a dead variable,
an unmodified variable, an incomplete `INITIALISATION`, or a shadowed name never
fails the command on its own. Read the output, or harden the gate.

Validate the **project directory**, not a glob:

```sh
rossi validate .
```

Directory validation links the complete `SEES`/`EXTENDS`/`REFINES` graph and
runs project-level rules such as `EB024` (a new event assigning an inherited
variable) and `EB025` (using a variable removed by data refinement). A list or
glob of text files resolves types but skips those project-level lints.

### `rossi fmt <INPUT…>`

Reformat Event-B text to the canonical shape: uppercase structural keywords,
Unicode operators, four-space indentation, and inline event status.

- `-i, --in-place` rewrites inputs.
- `--check` makes formatting a non-mutating CI gate.
- `-o, --output` writes elsewhere.
- `--ascii` or `--unicode` selects text operator spelling.
- `--indent <STR>` changes indentation.

Directories are accepted. `-` reads stdin and writes stdout. Rodin XML/archives
must use Unicode. Keep `.eventb` files comment-free because formatting can reflow
comments awkwardly.

### `rossi build <INPUT> [-o OUT]`

Static-check a `.eventb` file/directory or Rodin file/archive/directory and emit
checked `.bcc`/`.bcm` XML. A `.zip` output is a repackaged checked archive; any
other output is a directory. The default is `<input-stem>.regen.zip`. The build
fails on error diagnostics and drops stale proof artifacts.

### `rossi import <INPUT…> -o <OUT>`

Convert Rodin `.zip`/`.buc`/`.bum` inputs into `.eventb` text. Output one file per
component to a directory, or use `--merge[=ORDER]` for one combined file.
`--ascii`, `--indent`, and `-v` are available. Proof artifacts stay in the
original Rodin project; importing to text does not transfer them.

### `rossi export <INPUT…> -o <OUT>`

Convert `.eventb` text into a source Rodin archive or directory. Use it for
handoff to Rodin or as the first step of an export → prove in Rodin → archive
workflow. Use `build`, not `export`, to feed `eventb-animate` directly.

### `rossi lsp` / `rossi completions <shell>`

Run the language server over stdio, or generate shell completions for
`bash`/`zsh`/`fish`/`elvish`/`powershell`.

## Default ProB model checking

Run `eventb-animate` with no subcommand to check invariants and deadlock:

```sh
eventb-animate /tmp/model.zip
eventb-animate -m bridge_m1 /tmp/model.zip
```

The input may be a `.bum`, a checked `.zip`, or a Rodin project directory. The
most refined machine is selected unless `-m/--machine` names another one. In a
multi-project archive, use `[<project>/]<machine>` or `<project>/` to select that
project's most refined machine.

### Result and exit contract

Human output distinguishes `full state space explored` from a bounded,
non-exhaustive check. Prefer JSON report v3 in automation because exit 0 and
`status: "ok"` alone do **not** imply exhaustiveness.

- `0`: no requested check found a violation, possibly only within a bound; an
  LTL property held; a symbolic mode proved safety; all requested LTSmin passes
  completed; or another command succeeded.
- `1`: definite negative result or input failure—invariant/assertion violation,
  deadlock, reached goal, LTL/symbolic/LTSmin counterexample, imperfect replay,
  failed trace adaptation, disproved PO, or failed conversion.
- `2`: no verdict—engine interruption/failure, inconclusive symbolic run,
  unavailable/timed-out LTSmin, undischarged PO, uncovered required test target,
  failed evaluation, or invalid command line.

A legitimate terminal state is still a deadlock. Use `--no-deadlock` only when
that terminal state is intentional and document the decision.

### A finite model can still be reported incomplete

`explored_but_not_all_transitions_computed` commonly means ProB stopped enumerating
enabled initialisations or operation instances at a preference cap. Inspect the
actual values:

```sh
eventb-animate info --prefs model.zip \
  | rg 'MAX_(INITIALISATIONS|OPERATIONS)|DEFAULT_SETSIZE'
```

`MAX_INITIALISATIONS` caps setup/initial-state choices; `MAX_OPERATIONS` caps the
enabled instances of each operation in a state. Raise only the cap required by the
known finite scenario (for example `-p MAX_OPERATIONS=1000`) and rerun until the
JSON completion is `complete`. Better still, reduce unnecessarily wide
nondeterminism: a bit-update event is usually cheaper and clearer to explore than
an event that guesses an entire policy relation.

### Main options

- `-z, --size <N>` sets ProB's default carrier-set size (default 4).
- `-m, --machine [<project>/]<name>` selects a refinement level.
- `--states <N>` and `--time-limit <seconds>` bound explicit ProB search.
- `--no-deadlock`, `--no-invariant`, and `--assertions` select checks.
- `--goal <predicate>` searches for a reachable state; a hit is a deliberate
  exit 1 and can be saved as a trace.
- `--ltl` / `--ltl-file` checks a ProB LTL property.
- `--symbolic <bmc|ic3|kinduction|tinduction>` invokes ProB's SAT/SMT invariant
  checker. It is a stand-alone invariant-only mode: consistency controls such as
  `--no-deadlock` and `--time-limit` are rejected. It returns a verdict without a
  trace; rerun explicit ProB checking to obtain one.
- `--search-strategy <mixed|bf|df>` controls traversal;
  `--stop-at-full-coverage` stops once every event is covered.
- `-p, --pref <KEY=VALUE>` sets a ProB preference. List preferences with
  `eventb-animate info --prefs <model>`.
- `--save <trace.json>` writes a counterexample trace only when one exists.
- `--eval <formula>` evaluates values in a counterexample state.
- `--json`, `--junit`, and `--markdown` write run reports.
- `--progress`, `--perf`, and `--debug` add diagnostics.

## LTSmin backends

Select LTSmin explicitly:

```sh
eventb-animate --backend ltsmin-sequential --ltsmin-por /tmp/model.zip
eventb-animate --backend ltsmin-symbolic --no-deadlock /tmp/model.zip
```

| Backend | Best use | Counterexample evidence |
|---|---|---|
| `prob` (default) | Complete feature surface and normal authoring loop | Replayable trace + state |
| `ltsmin-sequential` | Alternate explicit exploration; optional POR | Replayed through ProB; supports `--save` and `--eval` |
| `ltsmin-symbolic` | Symbolic invariant/deadlock verdict | No replayable trace or counterexample state |

Important backend rules:

- An LTSmin run supports invariant/deadlock checks, `-z`, `--time-limit`, and
  report outputs. It rejects ProB-only modes and controls: assertions, goals,
  LTL, `--symbolic`, state limits, coverage stops, search strategies, and
  progress output.
- The default LTSmin check performs an invariant pass and then a deadlock pass,
  stopping at the first violation. Use `--no-deadlock` when only invariant
  safety is required and one pass is enough.
- `--ltsmin-por` applies only to `ltsmin-sequential`; symbolic LTSmin is
  incompatible with partial-order reduction.
- Sequential LTSmin disables ProB hash symmetry by default so its external
  trace can be replayed reliably. An explicit `-p SYMMETRY_MODE=...` overrides
  this safeguard and may make replay fail.
- Symbolic LTSmin produces a definite verdict but no trace or final state. Rerun
  a failure with `ltsmin-sequential` to save and inspect a counterexample.
- ProB has no compatible final event-coverage or search-statistics data for the
  external LTSmin engines.
- LTSmin has a 600-second default wall-clock limit. An explicit time limit is
  shared across both passes; timeout is exit 2 with report reason `time_limit`.

Do not confuse `--backend ltsmin-symbolic` with ProB's
`--symbolic ic3|kinduction|…`; they are separate engines with separate option
contracts.

## Reports are not traces

`eventb-animate` uses two different versioned JSON formats. Never feed a report
to `replay`, and do not parse a trace as if it were a report.

### Run reports: format version 3

```sh
eventb-animate --json /tmp/report.json /tmp/model.zip
jq '{status, completion, finding, searchStatistics}' /tmp/report.json
```

Every run report contains `formatVersion: 3`, `status`, `exitCode`, and `checks`.
A top-level model-check report also includes `completion`:

- `classification`: `complete`, `counterexample`, `incomplete`, or `error`.
- `phase`: `load`, `constant_setup`, `initialization`, or `search`.
- `reason`: stable cause such as `exhaustive`, `proof`,
  `property_violation`, `goal_reached`, `state_limit`, `time_limit`, `partial`,
  `engine_failure`, or `input_failure`.

Definite findings add `finding.category` and `finding.check`. Built-in explicit
ProB checks add `searchStatistics` when final counters are available. ProB LTL,
ProB symbolic, and external LTSmin checks omit those counters. Non-check commands
omit `completion`, `finding`, and `searchStatistics`; usage errors write no
report because no run began.

Report v3 does **not** contain the `Covered operations` list printed by the default
ProB check. Inspect or capture the human command output when event coverage is part
of acceptance; use `testgen --operations EVENT_NAME --json ...` when a
machine-readable targeted transition witness is required. An uncovered testgen
target is inconclusive, not proof that the event is unreachable.

For a successful **and complete** check gate, inspect both fields:

```sh
jq -e '.status == "ok" and .completion.classification == "complete"' \
  /tmp/report.json
```

A bounded built-in check can exit 0 with `status: "ok"` while reporting
`completion.classification: "incomplete"`. Preserve that distinction when
summarizing results.

`--json -` writes only the JSON report to stdout and sends normal output to
stderr. Report files are overwritten per run. `--junit` and `--markdown` expose
the same findings for CI and human review.

### Replay traces: format version 6

`--save` writes a ProB trace JSON document with
`metadata.formatVersion: 6`. Its steps are stored in `transitionList`;
parameterized transitions contain a `params` map, so values such as an `ANY`
event parameter survive saving and replay.

Treat trace JSON as an opaque versioned artifact: save it, retain it as a
regression fixture, and use `replay` rather than hand-editing transition/state
objects.

```sh
# A goal hit is expected to exit 1 and writes the path that reached count > 0.
eventb-animate -m counter_abstract --goal 'count > 0' \
  --no-invariant --no-deadlock --save /tmp/count-trace.json /tmp/counter.zip

eventb-animate replay -m counter_abstract \
  -t /tmp/count-trace.json /tmp/counter.zip
```

A clean consistency check does not write `--save`, because it has no
counterexample. Use a goal search to capture a path to a chosen state, or use
`testgen` for operation-coverage traces. A perfect replay exits 0; partial or
imperfect replay exits 1.

Sequential LTSmin counterexamples are replayed into ProB, so `--save` and
`--eval` work. Symbolic LTSmin and ProB's `--symbolic` modes have no replayable
trace. To adapt an abstract trace to a concrete refinement, use:

```sh
eventb-animate replay --refine -m M2 -t trace_M1.json model.zip \
  --save trace_M2.json
```

`--refine-breadth` and `--refine-depth` bound adaptation. The adapted trace is
overwritten at `--save`; failure to find an adaptation is exit 1.

Reports and traces compose safely in one command:

```sh
eventb-animate --json report.json --save trace.json model.zip
```

The report records its saved trace path as `traceFile` when a trace was written.

## Proof-obligation gates

- `eventb-animate wd <model>` asks ProB to discharge well-definedness
  obligations from scratch. All discharged is exit 0; any undischarged is exit 2.
- `eventb-animate po <rodin-project>` reads recorded Rodin `.bpo`/`.bps` proof
  status without starting ProB. It passes only when all selected obligations are
  discharged. Open, reviewed (unless allowed), or broken/stale obligations are
  exit 2; `--disprove` can turn a found counterexample into exit 1.

Run `po` on an original/proved Rodin project that still contains proof files.
`rossi import` produces text, `rossi export` produces source, and `rossi build`
drops proof artifacts, so none of those outputs alone creates a proof-bearing
archive. Useful flags are `--allow-reviewed`, repeated `--filter <glob>`, `-v`,
`--disprove`, and `--disprove-timeout`.

## Other `eventb-animate` commands

- `replay -t trace.json <model>` regression-checks a saved trace; `--refine`
  adapts it to another refinement level.
- `info <model>` dumps model information, graphs, or ProB preferences.
- `testgen <model> --out traces/` generates one replayable operation-coverage
  trace per covered target. `--fail-on-uncovered` and `--fail-on-infeasible`
  turn gaps into gates.
- `eval -e '<formula>' <model>` evaluates formulas in an initialized state, or
  in matching explored states with `--where`.
- `convert out.mch <model>` translates Event-B to a Classical B machine.
- `cbc <model>` performs constraint-based invariant/feasibility checks without
  reachability. Treat it as best-effort; it can be slow or inconclusive.

## Which tool when

| Goal | Command |
|---|---|
| Tidy a project | `rossi fmt -i .` |
| Gate formatting | `rossi fmt --check .` |
| Catch syntax/type/scope/refinement errors | `rossi validate .` |
| Produce checked artifacts | `rossi build . -o model.zip` |
| Check invariants + deadlock with full features | `eventb-animate model.zip` |
| Check one refinement level | `eventb-animate -m <machine> model.zip` |
| Run sequential LTSmin + POR | `eventb-animate --backend ltsmin-sequential --ltsmin-por model.zip` |
| Run symbolic LTSmin | `eventb-animate --backend ltsmin-symbolic model.zip` |
| Prove invariant safety with ProB | `eventb-animate --symbolic ic3 model.zip` |
| Search for and save a state path | `eventb-animate --goal '<pred>' --save trace.json model.zip` |
| Replay a trace | `eventb-animate replay -t trace.json model.zip` |
| Check a temporal property | `eventb-animate --ltl '<formula>' model.zip` |
| Gate well-definedness | `eventb-animate wd model.zip` |
| Gate recorded Rodin proof status | `eventb-animate po <proved-rodin-project>` |
| Generate operation traces | `eventb-animate testgen model.zip --out traces/` |
| Inspect values | `eventb-animate eval -e '<expr>' model.zip` |
| Emit a stable CI report | `eventb-animate --json report.json model.zip` |
| Pull Rodin source into text | `rossi import project.zip -o src/` |
| Push text source to Rodin | `rossi export src/ -o project.zip` |
| Check a snippet | `echo '…' \| rossi validate -` |
