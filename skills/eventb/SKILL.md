---
name: eventb
description: >
  Write and check Event-B formal models as `.eventb` text: contexts, machines,
  invariants, events, and justified refinement chains. Use for Event-B, Rodin,
  rossi, ProB/model checking, or requirements that need a discrete formal model.
  The core workflow uses rossi plus eventb-animate; interactive proof authoring is
  out of scope.
license: Apache-2.0
compatibility: >-
  Requires the rossi CLI 0.2.0+ and eventb-animate 6.4+ on PATH (Homebrew tap
  eventb-rossi/tap, APT, COPR, or Scoop), and Java 21+ for eventb-animate. No
  network access needed at run time.
metadata:
  author: "eventb-rossi"
  version: "1.2.0"
  homepage: "https://github.com/eventb-rossi/eventb-skill"
---

# Developing Event-B models

An Event-B model is a discrete transition system. A `CONTEXT` holds fixed sets,
constants, and axioms; a `MACHINE` holds variables, invariants, and guarded events.
This skill checks reachable behaviour with ProB and gates well-definedness. It does
not author interactive Rodin proofs.

## 1. Check the required tools

Require `rossi` 0.2.0+ and `eventb-animate` 6.4+. Check them; never install or
upgrade them yourself. If either is absent or older, stop and ask the user to do it.

```sh
command -v rossi eventb-animate
rossi --version
eventb-animate --version
```

## 2. Scope before modelling

Write a short requirement sheet in the model's `README.md`:

- system boundary and explicit exclusions;
- observable events and who performs them;
- state types and the safety properties that must always hold;
- one reachable success scenario, one important forbidden scenario, and whether a
  terminal state is intentional.

For a substantial model or any multi-level refinement, add a
requirement-to-refinement ledger with one row per level:
requirement/standard clause, new or replaced state, affected events,
invariant/gluing relation, and validation question. Split a level whose row contains
unrelated concerns.

Use **one machine by default**; split fixed data into as many small contexts as its
independent concerns require. Add a refinement level only when it isolates a
distinct requirement or replaces a data representation; write that reason and the
gluing invariant first. Refinement is a tool, not a required ceremony.

Keep each model in its own project directory. Use one component per file, with the
file named after the component. Do not put prose comments in `.eventb` files; keep
the explanation in `README.md`.

## 3. Read only the relevant reference

| Need | Read |
|---|---|
| Exact `.eventb` grammar and action forms | `references/syntax.md` |
| An operator or its precedence | `references/math-toolkit.md` |
| Help choosing state, invariants, or events | `references/modelling.md` |
| A genuine refinement step, or planning a chain | `references/refinement.md` |
| A core reactive-system pattern | the matching heading in `references/patterns.md` |
| Discrete time, deadlines, modes, or sensors/actuators | `references/patterns-control.md` |
| Multiple participants: topology, rounds, consensus, channels, long-running operations | `references/patterns-distributed.md` |
| Access control, authorization policy, or reservation | `references/patterns-security.md` |
| Deriving a loop from a postcondition, or an interpreter/ISA | `references/patterns-algorithms.md` |
| CLI troubleshooting or a conditional advanced command | `references/tooling.md` |
| Final design review | `references/best-practices.md` |

Start from `examples/counter/` only when witnesses or data refinement are involved;
use `examples/cars_on_bridge/` for event splitting/convergence and
`examples/array_maximum/` for terminating algorithms. Do not read examples merely
to begin a small single-machine model.

## 4. Author the smallest useful model

- Put carrier sets and fixed policy/configuration in a context.
- Type every variable with its first invariant, then state the actual safety rule.
- When sensing or control crosses a system boundary, keep physical, reported, and
  commanded state distinct and state the permitted delay/uncertainty between them.
- Make `INITIALISATION` establish every invariant.
- Give each event every guard required by the functional and transition-only
  requirements as well as invariant preservation; actions run simultaneously and
  unassigned variables stay unchanged.
- Represent an important outcome in state when a later state goal must observe it.
  Do not add a no-op event solely to obtain coverage; an enabled no-op changes
  deadlock and liveness behaviour.
- Keep finite checking scenarios small. Wide nondeterministic parameters multiply
  operation enablings and can make an otherwise finite check incomplete or slow.

## 5. Run the core gate

Run from the model's project directory, not from a parent containing unrelated
models. Build a `.zip`; it contains the checked files the animator needs.

```sh
rossi fmt -i .
rossi validate .
rossi fmt --check .
rossi build . -o /tmp/model.zip
eventb-animate --json /tmp/model-report.json /tmp/model.zip
eventb-animate wd /tmp/model.zip
```

Accept the result only when:

- validation and build have no errors; treat `missing or ill-typed witness` and
  `event is inaccurate` warnings as failures even if the command exits zero;
- the report has `status: "ok"` and no invariant violation;
- there is no **unexpected** deadlock; for a deliberate terminal state, document
  the terminal predicate and rerun with `--no-deadlock` instead of claiming
  deadlock-freedom;
- the human `Covered operations` block contains the expected events (report v3 does
  not store operation coverage, so capture the command output when this must be
  audited);
- `completion.classification` is `complete` for a finite acceptance scenario;
- every well-definedness obligation is discharged.

An exit code of zero is not proof of completeness. If a finite model is reported
incomplete, inspect the reason and the relevant ProB caps:

```sh
eventb-animate info --prefs /tmp/model.zip \
  | rg 'MAX_(INITIALISATIONS|OPERATIONS)|DEFAULT_SETSIZE'
```

Raise `MAX_INITIALISATIONS` or `MAX_OPERATIONS` **strictly above** the known finite
count, never to exactly it — reaching a cap is itself the incompleteness signal, so
an event with 16 enablings still reports incomplete at `-p MAX_OPERATIONS=16`. Rerun
and require `completion.classification: "complete"`.
For an intentionally generic/unbounded model, report the bounded result honestly
and add a separate small finite scenario when an exhaustive gate matters.

The default run also applies ProB hash symmetry reduction (`SYMMETRY_MODE = hash`,
overriding ProB's own `off`), so the state count it prints is a quotient, not the
concrete state space. Rerun with `-p SYMMETRY_MODE=off` before reporting a count.
Both settings detect the same invariant violations; only the number moves.

If there is a refinement chain, repeat the model check and `wd` for every level
with `-m <machine>`.

## 6. Add targeted evidence when it answers a question

Use a goal trace when the question is whether a **state predicate** is reachable:

```sh
eventb-animate -m M --goal '<predicate>' --no-invariant --no-deadlock \
  --save /tmp/scenario.json /tmp/model.zip
eventb-animate replay -m M -t /tmp/scenario.json /tmp/model.zip
```

A reached goal deliberately exits 1; require a `PERFECT` replay. On an invariant or
deadlock failure, save and replay its counterexample before changing the model.

A state goal cannot prove that an actionless or guard-only event fired: it may stop
as soon as the enabling state is reached. Confirm a specific transition through the
complete check's `Covered operations` block, or target it with test generation:

```sh
eventb-animate testgen -m M --operations EVENT_NAME \
  --out /tmp/scenario-traces /tmp/model.zip
```

Use these only when their narrower purpose applies:

- `testgen`: witness a specific transition or generate replayable operation
  fixtures; it is not a stronger gate than an exhaustive check, and “uncovered” is
  inconclusive.
- `--symbolic ic3|kinduction`: unbounded invariant safety; it does not check
  deadlock, report event coverage, or provide traces.
- `po`: gate an existing Rodin project that already carries `.bpo`/`.bps` proofs.
- `import`/`export`: Rodin interchange, not the normal authoring loop.

See `references/tooling.md` for these conditional workflows. The default ProB
backend is the normal authoring path.

## 7. Finish with a readable artifact

Deliver the `.eventb` files plus a short `README.md` containing scope, model shape,
the safety invariant in plain language, any refinement ledger, exact check commands
including every `-p` preference, completeness, the reported state count, event
coverage, WD result, and any deliberate abstraction. A count that moves with a
preference is not a result unless the preference is recorded beside it. A clean
bounded run means
“no bug found within the bound.” A complete finite run proves only the checked
**reachable behaviour**: it can still accept an over-strong, non-inductive
invariant because violating states are unreachable. It does not discharge Event-B
invariant/refinement proof obligations; only an applicable proof gate supports
that claim. See `references/refinement.md`, “model checking is not proof.”
