# Modelling in Event-B

How to build a model: what a model *is*, what goes in contexts vs machines, and how
to write state, invariants, and events. Authoring interactive proofs is out of scope —
here, behaviour is checked by model checking.

## What Event-B is

Event-B builds **mathematical models of discrete transition systems**. A model is
*not* a program; it is a blueprint you reason about *before* coding, so the system
is correct by construction.

- A model is made of two kinds of **component**:
  - **Machines** — the *dynamic* part: variables, invariants, variant, events.
  - **Contexts** — the *static* part: carrier sets, constants, axioms.
- The state is a set of **variables** + **invariants** (permanent properties).
  Each **event** is a transition with a **guard** (when it may occur) and
  **actions** (how the state changes). Variables not assigned stay unchanged.

**Modelling vs programming.** Programming tells a computer how to do a task.
Modelling describes how a *whole system* — software *and its environment* — can be
observed. You formalise *what can be observed and what must stay true*, not the
algorithm. (The initial model of a sort program states *what a sorted file is*, not
*how* to sort.) Notation is ordinary first-order logic + set theory; variables may
be integers, sets, relations, functions — any mathematical object.

## Contexts — the static part

Use a context for the fixed mathematical scaffolding a machine depends on, so the
machine stays generic and is instantiated by changing only the context.

- **carrier sets** (`SETS`) — fresh, pairwise-disjoint *types*; the only thing you
  may assume is that they are **non-empty**.
- **constants** (`CONSTANTS`) + **axioms** (`AXIOMS`) — fixed values and the
  assumed predicates they satisfy.

```
CONTEXT bridge_ctx
CONSTANTS
    d
AXIOMS
    @axm1 d ∈ ℕ
    @axm2 d > 0
END
```

## Machines — the dynamic part

- **variables** (`VARIABLES`) — the state.
- **invariants** (`INVARIANTS`) — predicates always true of the state.
- **sees** (`SEES`) — the contexts whose sets/constants are visible.
- **events** — the transitions.

### Typing invariants come first

A machine variable carries no declared type; an invariant gives it one. **Make the
first invariant for each variable a typing predicate** `v ∈ …`, then add safety
invariants expressing relationships that must always hold.

```
INVARIANTS
    @inv1 n ∈ ℕ          // typing
    @inv2 n ≤ d          // safety: capacity never exceeded
```

## Events

An event is a guarded transition. The parts that matter for modelling:

- **`ANY`** — parameters: local, non-deterministically chosen inputs.
- **`WHERE` / `WHEN`** — guards: the *necessary enabling conditions*. The event may
  occur only when **all** guards hold.
- **`THEN`** — actions: how the state changes. Actions run **simultaneously**;
  right-hand sides read the *before* state; each variable is assigned at most once.

```
EVENT ML_out
WHERE
    @grd1 n < d
THEN
    @act1 n ≔ n + 1
END
```

### INITIALISATION

Every machine has the special `INITIALISATION` event: no guard, no parameters,
just actions that set the starting state. Its job is to **establish every
invariant** before any other event runs.

## Non-determinism

Abstraction leans on non-determinism; you make things deterministic *later*.

- **Parameters** (`ANY x WHERE …`) let an event choose a value subject to guards.
- **Non-deterministic actions**:
  - becomes-in `x :∈ S` — choose any member of `S`;
  - becomes-such-that `x :∣ P` — choose any after-value(s) making `P` true; `x'`
    is the after-value, e.g. `n :∣ n' ∈ ℕ ∧ n' < n`.

Why: an abstract model should leave choices *open* (e.g. "a car leaves the bridge"
without saying which), to be pinned down by a later refinement. (`counter_abstract`
in `examples/counter` uses both `ANY` and `:∣`.)

## Common state shapes

Pick the mathematical object that makes the safety property easiest to *state* — a
relation/function for a policy or graph, a `status` function for a per-entity
lifecycle, a function of time for rates of change, an array as a function `1 ‥ n →
VALUE` for algorithm data. These are worked out, with the events that go with them, by
domain in [patterns-control.md](patterns-control.md) (time, modes, lifecycles),
[patterns-distributed.md](patterns-distributed.md) (topology, channels),
[patterns-security.md](patterns-security.md) (policy relations), and
[patterns-algorithms.md](patterns-algorithms.md) (arrays, machine state).

One shape worth stating here: an **optional / nullable** single value can't be
"absent" from a typed variable, so give the type a sentinel constant (`null ∈ REF`, or
add it to a carrier set via `partition`) and test `current = null` directly. A paired
`current_set ∈ BOOL` flag is redundant — `current = null` already carries that bit — so
prefer the single variable.

## The modelling process — start abstract

Build by **successive approximation**: drastically simplify first, then
re-introduce detail gradually (don't take all complexity at once).

**A refinement chain is optional.** If the scoped requirements and safety property
fit clearly in one small machine, stop there. Add a level only when it separates a
distinct concern or replaces a representation; an abstract variable that merely
duplicates a concrete derived value adds proof and model-checking cost without
adding insight.

- The **initial model** captures the *main function* / most abstract requirement
  and the safety property it must keep — **not** the algorithm or the equipment.
- Concrete requirements come **last**.
- It's often a **closed model**: include an abstraction of the *environment*
  alongside the controller, so your assumptions about the world are explicit (see
  `patterns.md`, controller/environment split).
- Communication between parts is "cheated" early (parts read each other's abstract
  state directly); real messages/channels are introduced only late.

The detail is then added by **refinement** (see `refinement.md`): horizontal
(superposition — add variables/events/guards) until every requirement is modelled,
then vertical (data refinement — move toward implementable data structures).

## Deadlock and enabledness

- An event is **enabled** when all its guards hold. Operationally: pick one enabled
  event, apply it, re-check guards, repeat.
- **Deadlock** = no event is enabled; execution stops. Most systems we model are
  meant to run forever, so deadlock is usually a bug.
- **Exception — a finite carrier of consumable identities.** When each element of a
  carrier set is processed once (submit-then-claim, allocate-then-free), the model
  *legitimately* reaches an all-settled terminal state once the set is exhausted — an
  **intended** deadlock, not a bug. Exhaustive model checking *will* find that state
  and report it as a deadlock (exit 1), so either model an unbounded id source, or run
  the intended-terminal model with `eventb-animate --no-deadlock` and note the
  terminal predicate in the README. Do not describe that run as deadlock-free.
- **Model checking reveals deadlock and invariant violations cheaply** — even on very
  abstract models, before any proof. For models expected to remain enabled,
  `eventb-animate` reports `deadlocked:0` / `invariant_violated:0` when all is well
  (and `full state space explored` when the check was exhaustive). Use it early and
  often.

## Rules of thumb

- **R0** Take a *small* number of requirements per step.
- **R1/R2** Take a complex requirement *partially*; finish it in later steps.
- **R3** Abstract a many-case condition as a non-deterministic boolean first; make
  it concrete later.
- **R4** Introduce the system's functions *gradually*.
- **R5** Start with the *most abstract* requirements (the main functions).
- **R6** Introduce the *most concrete* requirements *last*.
- **R7** Balance software and environment requirements.
- **R8** Don't forget any requirement; **R9** drop any you genuinely can't model.

And: **model the problem, not the solution** — the safety property must be *in the
model* from the start; revise your requirements and plan freely as modelling
exposes gaps (progress is not linear).

## Quick glossary

| Construct | Lives in | Purpose |
|---|---|---|
| carrier set | context `SETS` | a fresh, non-empty type |
| constant + axiom | context | fixed value + its assumed property |
| variable | machine `VARIABLES` | a piece of mutable state |
| invariant | machine `INVARIANTS` | always-true property (typing first, then safety) |
| guard | event `WHERE`/`WHEN` | enabling condition |
| action | event `THEN` | simultaneous state change |
| parameter | event `ANY` | non-deterministic local input |
| INITIALISATION | machine (mandatory) | establishes the invariant in the start state |
