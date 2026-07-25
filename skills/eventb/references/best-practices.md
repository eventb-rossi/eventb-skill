# Best practices

A checklist of dos and don'ts for authoring an Event-B model, covering ordinary
developments as well as industrial and safety-critical ones. Use it while authoring
and as a review pass before declaring a model done.

## Contents

- [Start abstract, stay small](#start-abstract-stay-small)
- [State and invariants](#state-and-invariants)
- [Events and actions](#events-and-actions)
- [Contexts](#contexts)
- [Refinement](#refinement)
- [Protocols and optimisation](#protocols--optimisation)
- [Workflow discipline](#workflow-discipline)
- [Smells](#smells-reconsider-the-model)

## Start abstract, stay small

- **Start far more abstract than the real system.** The initial model should capture
  one or two constraints and the core safety property — *ignore all equipment and
  detail*. You should be able to reason about it "from high in the sky."
- **Do not refine by default.** One machine is the right endpoint for a small,
  coherent model; use however many small contexts its independent static concerns
  require. Add a refinement only when it isolates another requirement or replaces a
  data representation; do not retain an abstract ghost variable that only restates
  a concrete derived value.
- **Model the problem, not the solution.** State *what must be observed and stay
  true* (e.g. "the bridge never holds more than `d` cars"), never the algorithm.
- **Introduce one concern per refinement.** Write an explicit refinement *strategy*
  up front mapping each requirement to a step; keep each step small enough to
  understand (and, beyond this skill, to prove).
- **Keep a requirement-to-refinement ledger for a substantial chain.** For every
  level record the requirement/standard clause, new or replaced state, affected
  events, invariant or gluing relation, and one validation question. If one row
  contains unrelated concerns, split the step.
- **Most abstract first, most concrete last.** Data structures, encodings and
  communication come at the end of the chain.

## State and invariants

- **Type every variable with its first invariant** (`v ∈ …`), then add safety
  invariants.
- **Separate physical, reported, and commanded state.** Introduce environment truth,
  observations (including age/quality), and controller targets as different
  variables; relate them with invariants that admit the specified delay or
  uncertainty.
- **Prefer a mode/phase variable** to encoding a phase implicitly across several
  booleans when you need "exactly once" / strict-alternation semantics.
- **Scope degraded operation precisely.** If an `unsafe`/`degraded` mode relaxes a
  nominal invariant, state the implication explicitly, restrict who can enter the
  mode, and provide a checked recovery path. A flag by itself is not a safety
  argument.
- **Express constraints as invariants** and discharge them by **strengthening the
  guards** of the events that could violate them — rather than ad-hoc fixes. When
  the reacting events are physically fixed, add guards to the *action* events
  instead.
- **Some safety properties are guard/transition-only.** "Do X at most once", "no Y
  while paused", "Z only after W" constrain *which transitions may fire* and have no
  pure state-predicate form — encode them as **guards** (optionally backed by a
  state-invariant shadow where one exists). Model checking cannot *falsify* a guard-only
  property (guards can't be violated by construction), so add a scenario that actually
  **exercises** the guarded transition. Model checking covers a transition only if it is
  reachable in the *explored* state space; if it stays uncovered (check the coverage
  block), pin the seen-context constants so the transition becomes reachable. A
  `--goal '<pred>'` can find an enabling state, but cannot prove an actionless event
  fired; use full-check operation coverage or `testgen --operations EVENT_NAME` for the
  transition itself.
- **Keep auxiliary/ghost variables out of guards.** Use them only to state a
  constraint precisely, then remove them.

## Events and actions

- **Name events for the real-world action** (`push_start_button`, `ML_out`), and use
  a naming convention that encodes the controller/environment split (e.g. a `treat_`
  prefix for controller events).
- **One variable per action**; remember actions in a `THEN` run simultaneously and
  read the *before* state.
- **Keep sensor and actuator as separate variables**; never assume the controller
  and the equipment share an instantaneous view of the world.
- **Refine a fallible long operation into an explicit protocol:** `start`, bounded
  `step`, disjoint `end_ok`, and `end_fail`. Relate temporary progress to the
  abstract atomic result with an invariant and give every internal event a
  convergence/variant story.
- **Compute recovery privately and commit once.** Traverse a finite work set into
  temporary mode/configuration proposals, then publish the complete request in one
  event; specify what happens if another fault arrives during the computation.
- **Guard before you apply a function.** Any `f(i)` (array access, table lookup)
  needs a guard or invariant putting `i ∈ dom(f)` — its well-definedness obligation.
  Pair an index advance `i ≔ i + 1` with a guard like `i ≠ n` so the next access stays
  in range.

## Contexts

- **One concern per context; layer with `EXTENDS`.** A small context per component
  (one carrier set + its `partition`) lets machines `SEES` only what they touch.
- **Pre-prove reusable facts as context `theorem`s** — finiteness, "this override
  preserves the type", or a lookup table's totality (`theorem @t decode ∈ RAW → CMD`,
  which also makes every later `decode(x)` well-defined) — so later obligations get
  them for free.
- **Trace a normative standard explicitly.** Map each section/service to assumptions,
  static declarations, run-time state, events, invariants, refinement level, and
  proof/validation evidence. Record ambiguities instead of resolving them silently.
- **Separate the abstract spec from a concrete instance for model checking.** Keep
  carrier sets and loose axioms *general* (that is the proof/refinement story) and put
  the **feasibility constraints** a valid configuration must satisfy as axioms there. To
  *model-check a concrete scenario* — and make the check exhaustive (`full state space
  explored`) — pin concrete values in an instance the checked machine actually `SEES`:
  the quick way is a throwaway build that overwrites the seen context's constants (see
  `examples/array_maximum`); the Rodin-idiomatic way is a separate `EXTENDS` instance
  context plus a thin scenario machine that `SEES` it. An `EXTENDS` context that no
  machine `SEES` changes nothing checked.

## Refinement

- **Decide superposition vs data refinement per step**, and write the **gluing
  invariant before** refining the events.
- **Strengthen guards just enough** to track new state — over-strengthening
  introduces deadlock (model-check to confirm the refinement didn't add one).
- **Use extended events for small deltas.** When a level only adds guards/actions
  for its new concern, prefer `extends` to copying the inherited event; for legacy
  full-restatement models, generate a refinement-delta view for review.
- **Mark every new event `convergent`/`anticipated` and give the machine a
  `VARIANT`** it decreases, so new events can't run forever.
- **Provide a witness (`WITH`)** for every disappeared abstract parameter or
  non-deterministic after-value; none is needed for kept variables.
- **Reuse named patterns; instantiate by renaming.** Build a small catalogue (see
  `patterns.md` for core reactive-system shapes and the `patterns-control.md`,
  `patterns-distributed.md`, `patterns-security.md`, and `patterns-algorithms.md`
  field guides for domain idioms) and apply it across similar connections.
- **Layer independent security mechanisms.** Keep core authorization, RBAC,
  integrity, confidentiality/information flow, and implementation representation in
  planned levels; centralise typed helper relations/functions and keep a
  policy-to-event impact matrix.

## Protocols & optimisation

- **Model the achieved result first ("what, not how")**, then progressively open the
  observer's eyes — allow parties to "cheat" (direct state access) before forcing
  real message-passing.
- **Model messages/channels as state variables** with gluing invariants relating
  in-transit data to the true sender state.
- **Optimise in a final, behaviour-preserving refinement** — keep correctness and
  efficiency in separate steps.
- **Normalise for code generation only after semantics are stable.** The last level
  may replace mathematical forms with equivalent codeable forms, but must add no
  requirement; prove it and replay model traces against the generated executable.

## Workflow discipline

- **Validate and model-check continuously.** After every change:
  `rossi fmt -i` → `rossi validate` → `rossi build` → `eventb-animate`. Aim for exit 0
  with `invariant_violated:0` and no unexpected deadlock at every level; document an
  intentional terminal predicate and use `--no-deadlock` for that model. Add
  `eventb-animate wd` to gate on well-definedness.
- **Model-check each refinement level by name** (`-m <machine>`), not just the most
  refined one — a bug is cheapest to find at the level that introduced it.
- **Pin nondeterminism in a throwaway "scenario" build to check a case exhaustively.**
  With unbounded constants the run is bounded by the set size and may leave events
  uncovered; to exercise the interesting behaviour *and* get `full state space
  explored`, model-check a concrete instance the machine `SEES` (`examples/array_maximum`
  pins the seen context's constants in a throwaway build), or a refinement that only
  restricts `ANY` parameters to scenario values — the lightweight form of a validation
  obligation.
- **Remember model checking proves safety only for the states it reaches** — an
  over-strong invariant can pass validation and model-checking yet be unprovable, since
  the breaking states are never reached (see `refinement.md`, "model checking is not
  proof"). Exhaustive (`full state space explored`) and `--symbolic ic3`/`kinduction`
  runs can establish absence of reachable invariant violations in the checked model;
  they do not discharge Event-B invariant-preservation or refinement obligations. A
  bounded run proves neither.
- **Let failed checks guide discovery.** A deadlock or invariant violation found by
  model checking usually points straight at a missing guard or invariant — read it off
  the counter-example (`--save trace.json`) and add it.
- **Revise the requirements and the plan freely.** Progress is not linear; modelling
  routinely exposes gaps. Drop a requirement you genuinely cannot model (and note
  it).

## Smells (reconsider the model)

- The abstract model already mentions equipment, encodings, or channels → it's not
  abstract enough.
- A refinement step changes many concerns at once → split it.
- A phase is reconstructed from three+ booleans → introduce a mode variable.
- A new event has no variant / convergence story → it can diverge; fix it.
- An invariant needs many special cases → the events may be doing too much; simplify.
- `tick` has a screenful of disjuncts → introduce phases, deadline data, or a
  generated/exhaustive scheduling table.
- Authorization formulas are copied into many guards → define one typed policy
  helper and prove its domain/meaning.
- A final machine has tens or hundreds of events and no inventory/delta view → the
  model is no longer reviewable as a file.
- A refinement has no ledger row or validation question → its purpose is unclear.
