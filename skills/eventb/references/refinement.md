# Refinement in Event-B

Refinement is the core method: instead of one big model, build a *chain* of models,
each more precise than the last, none contradicting its predecessor. Authoring
interactive proofs is out of scope — we state *what must hold* conceptually and check
it by model checking.

The worked example for everything below is `examples/cars_on_bridge`.

## Why refine

- **Successive approximation** makes a hard problem tractable: the first model is
  the **abstract** one; each successor is a **refinement** (a **concrete** model).
- Like viewing the system through a microscope at higher magnification — more state
  and more events become visible, all consistent with the coarser view.
- By the final refinement, every requirement must be accounted for.

Two styles, often mixed within one chain:

| Style | Also called | What changes |
|---|---|---|
| **Horizontal** | superposition / feature augmentation | add state & events; keep existing behaviour |
| **Vertical** | data refinement | replace abstract data with concrete/implementable data |

## The `REFINES` relationship

- A concrete **machine** names its abstract machine in `REFINES` (at most one; the
  graph must be acyclic). It must `SEES` at least the contexts the abstraction does.
- A concrete **event** names the abstract event(s) it refines in its `REFINES`
  clause — or is a **new event** (which conceptually refines `skip`).
- Variable names may be reused across the boundary; a kept variable is the same
  variable.

## What is inherited vs what you restate

Refinement is not a textual copy of the previous level. The tooling carries the
abstraction forward automatically (as Rodin does); restate only what this table
says you must:

| In the concrete machine | Restate? |
|---|---|
| Abstract **invariants** | **Never.** They keep holding and are inherited into the proof context automatically (`rossi build` copies them into the checked `.bcm`). Write only *new* predicates: typing for new variables, gluing invariants, new safety. |
| Kept **variables** | **Yes — required.** A variable not re-listed in `VARIABLES` *disappears*; referencing it afterwards is an error (`[EB025]`). |
| Seen **contexts** | **Yes** — `SEES` at least the contexts the abstraction sees. |
| Events kept as-is, or only added to | **No** — declare them `extends` (next section); parameters, guards and actions are inherited. |
| Events whose kept guards/actions change | **Yes** — a plain event `REFINES` inherits **nothing**; the event must restate its complete parameter/guard/action set. |

## Extended events (`extends`)

An event that keeps its abstract behaviour and only *adds* to it is declared with
`extends` in the header (in place of a `REFINES` clause):

```
EVENT inc extends inc
WHERE  @grd2 paused = FALSE
END
```

- Inherits the abstract event's **parameters, guards and actions** implicitly; the
  body lists only the additions (new `ANY` parameters, guards, actions). It may be
  empty — `EVENT reset extends reset END` carries `reset` forward unchanged.
- New labels must not collide with inherited ones — continue the numbering
  (abstract has `@grd1` → additions start at `@grd2`).
- `INITIALISATION` too: `EVENT INITIALISATION extends INITIALISATION` inherits the
  abstract init actions; add only the actions initialising the new variables.
- An event extends exactly **one** abstract event, and cannot drop or alter
  anything it inherits.

Prefer `extends` for superposition — it is the dominant style in published Rodin
models (unchanged events carried forward with empty bodies), and it keeps deep
chains readable because each level contains only its delta. Fall back to plain
`REFINES` + full restatement whenever something inherited must *change*: data
refinement (an action re-expressed over new variables), a kept guard rewritten
over new state, or event merging.

## Horizontal refinement (superposition)

Extend a model by *adding* detail while keeping old behaviour. You may:

1. add new variables (and their typing/safety invariants);
2. add new events acting on them;
3. strengthen the guards of existing events;
4. extend the actions of existing events to also assign the new variables.

For 3 and 4, declare the event with `extends` (above) when the abstract
guards/actions are kept as-is — the additions are then all you write. Use a plain
`REFINES` clause and restate the full event only when a kept guard or action must
itself be re-expressed — as below, where the abstract guard is *replaced* by the
stronger light-colour guard rather than kept.

Abstract variables are **kept**. The bridge's **second refinement** is pure
superposition: it keeps `a, b, c` and adds traffic lights `ml_tl, il_tl`, then
guards the existing `ML_out`/`IL_out` on the light colour instead of on the raw
condition:

```
// abstract (m1) ML_out guard:   a + b < d ∧ c = 0
// concrete (m2) ML_out_1 guard: ml_tl = green
```

`ml_tl = green` is *stronger* than the abstract guard, justified by a conditional
gluing invariant (below) guaranteeing green implies the abstract condition held.

## Vertical refinement (data refinement)

Replace abstract variables with concrete data closer to implementation. The
abstract variable *disappears*; its relationship to the concrete state is captured
by a **gluing invariant**.

The bridge's **first refinement** is the canonical case: the single counter `n`
(cars in the compound) is replaced by three variables `a` (heading to the island),
`b` (on the island), `c` (heading to the mainland), glued by `a + b + c = n`. Each
abstract event is re-expressed over the concrete variables:

```
// abstract (m0) ML_in:  when 0 < n  then n ≔ n − 1
// concrete (m1) ML_in:  when 0 < c  then c ≔ c − 1
```

## Gluing invariants

A **gluing invariant** is a concrete-machine invariant that mentions an abstract
variable, tying the two state spaces together. Concrete invariants split into:

- **purely concrete** (only concrete variables): `@inv5 a = 0 ∨ c = 0`;
- **gluing** (mention an abstract variable): `@inv4 a + b + c = n`.

For pure superposition where a variable is *kept*, the gluing invariant is the
implicit identity `v_concrete = v_abstract`. Conditional gluing invariants are
common — they link new state to an abstract guard:

```
@inv3 ml_tl = green ⇒ a + b < d ∧ c = 0
@inv4 il_tl = green ⇒ 0 < b ∧ a = 0
```

Conceptually, every concrete step must **preserve the gluing invariant**: when the
concrete event moves the state, the corresponding abstract move must keep abstract
and concrete related.

## Refining events: guard strengthening

For a concrete event to refine an abstract one:

1. **Guard strengthening** — the concrete guard must *imply* the abstract guard
   (you can't enable the concrete event where the abstract one was disabled). The
   two `ML_out` guards `a + b < d` and `c = 0` together imply `a + b + c < d`, i.e.
   the abstract `n < d` (via `a + b + c = n`).
2. **Action consistency** — the concrete action must not contradict the abstract
   action, preserving the gluing invariant.

**Don't over-strengthen** guards: removing too much enabledness introduces
deadlock. *Relative deadlock-freedom* asks that the concrete machine not deadlock
more often than the abstract one — check it by model-checking the refinement.

## New events and convergence

New events (invisible at the abstract level) each refine `skip`. They must **not run
forever**, or they could starve the refined "real" events.

> **A new event may assign only variables introduced at its own level.** Because it
> refines `skip`, it must leave all *inherited* state unchanged; assigning an inherited
> variable makes the refinement proof obligation unprovable, and ProB silently disables
> the event (it has no valid `skip` step) — visible only as a never-firing event or an
> unexpected model-checking deadlock. `rossi validate .` (the **project directory**, not a
> file glob) flags this as `[EB024]`. To change an inherited variable, `REFINES` the
> abstract event that changes it, or data-refine the variable; to add genuinely new
> behaviour, hold it in a **new variable**.

- A **`VARIANT`** — a natural-number or finite-set expression — is exhibited at the
  machine level; every **`convergent`** new event must make it **strictly
  decrease** (a finite set strictly shrinks). One variant per machine; all
  convergent events must decrease the same one.
- Event **status** (the inline prefix on `EVENT`):

  | Status | Obligation |
  |---|---|
  | `ordinary` (default) | none (refines an abstract event, or just a normal event). |
  | `convergent` | must strictly **decrease** the variant. |
  | `anticipated` | must **not increase** the variant — defers the strict-decrease proof to a later refinement ("I'll make it convergent later"). |

The bridge's first refinement adds two convergent events `IL_in`/`IL_out` with
`VARIANT 2 ∗ a + b`; each decreases it:

```
convergent EVENT IL_in
WHERE  @grd1 0 < a
THEN   @act1 a ≔ a − 1
       @act2 b ≔ b + 1     // 2∗(a−1)+(b+1) = 2∗a+b − 1  <  2∗a+b
END
```

Booleans/enumerations can't be a variant directly — convert them to numbers (the
bridge defines `b_2_n ∈ BOOL → {0,1}` and uses `VARIANT b_2_n(ml_pass) +
b_2_n(il_pass)`). Convergence sometimes forces *strengthening the model* (extra
variables/guards) so a new event genuinely makes progress.

**Staging the variant (algorithm development).** A common move: mark a worker event
`anticipated` in the abstract machine precisely because *the quantity that will
decrease does not exist yet*, then make it `convergent` in the refinement that
introduces the loop counter (where the `VARIANT` — typically a **gap** like `n − i`,
or a shrinking **set** — first makes sense). See
[real-world-patterns.md](real-world-patterns.md) (Algorithm development by refinement)
and the worked `examples/array_maximum`.

## Witnesses (`WITH`)

When refining an event, an abstract quantity may **disappear** concretely. A
**witness** re-expresses it in terms of the concrete state, keeping the link
well-defined. A witness is needed when:

1. an abstract **parameter** (from `ANY`) is gone — witness its value;
2. an abstract variable assigned **non-deterministically** (`:∣`/`:∈`) is gone —
   witness its **after-value** (the primed name `x'`).

The witness label *is* the witnessed name; the predicate constrains it (usually a
deterministic `name = E`):

```
EVENT add
REFINES add
ANY k
WHERE  @grd1 k ∈ ℕ1
       @grd2 level + k ∗ step ≤ cap
WITH   @d d = k ∗ step          // witnesses the disappeared abstract parameter d
THEN   @act1 level ≔ level + k ∗ step
END

EVENT remove
REFINES remove
WHERE  @grd1 level ≥ step
WITH   @count' count' = level − step   // witnesses the disappeared after-value count'
THEN   @act1 level ≔ level − step
END
```

No witness is needed for a variable/parameter that is **kept**. (`examples/counter`
shows both witness kinds.)

## Event splitting

Several concrete events may refine the **same** abstract event, partitioning its
behaviour. The bridge's `ML_out` splits into `ML_out_1` (a normal car) and
`ML_out_2` (the last admissible car, which turns the light red) — both
`REFINES ML_out`, with complementary guards.

## Event merging (the dual)

The inverse move also exists: several abstract events whose guards and actions have
become identical at some refinement level can be **merged** into one concrete event
that `REFINES` them all. This is the standard way to *remove* a distinction once the
state that justified it has been abstracted away (e.g. collapsing three per-phase
round events into a single `round` event once the phase variable is gone).

## A caution: model checking is not proof

Model checking is this skill's behavioural correctness check. When the state space is
finite and the run is complete, it establishes that the checked invariants hold in
every reachable state; when deadlock checking is enabled, it also establishes that no
reachable deadlock exists. `--symbolic ic3`/`kinduction` can prove invariant safety on
unbounded spaces. But a model with unbounded types (`ℕ`, `ℤ`, an unpinned carrier) is
only checked *up to the set size* — the run reports `not an exhaustive check`, and a
violation hiding in a larger instance is missed. Model checking only ever visits
**reachable** states and does not discharge Event-B invariant-preservation or
refinement proof obligations.

That reachability limit is the sharp failure mode: an **over-strong invariant** — one
that asserts more than the events actually maintain — is *unprovable*, yet a model
carrying it still validates *and* model-checks with `invariant_violated:0`, because the
states that would break it are simply never reached. The defect surfaces only under
proof of the invariant's preservation obligation — beyond this skill's model checking
(gate on it with `eventb-animate po` once the model carries Rodin proofs).

Practical guard-rails: keep each invariant no stronger than the safety property you
actually need; make the check exhaustive where you can (pin the constants, keep `-z`
small); when an invariant ties two pieces of state, check it is *established by
INITIALISATION* and *preserved by every event* by reading each event, not just by
model-checking; and treat a clean run as "no bug found", not "correct".

## Planning a refinement chain

Decide the order up front from the requirements (the rules of thumb R0–R9 in
`modelling.md`): most abstract first, most concrete last; one or few concerns per
step; abstract hard conditions as booleans/non-determinism and make them concrete
later. For each step decide **superposition vs data refinement**, and write the
**gluing invariant before refining the events**. Expect to iterate the plan as
model checking (and, beyond this skill, proof) exposes missing invariants or guards.

### Checklist per refinement step

- [ ] `REFINES` the previous machine; `SEES` at least its contexts.
- [ ] Kept variables re-listed in `VARIABLES`; abstract invariants **not** restated.
- [ ] Unchanged / purely-augmented events declared `extends`; plain event `REFINES`
      (full restatement) only where a kept guard or action changes.
- [ ] New variables typed by invariants; gluing invariant(s) written.
- [ ] Each refined event's guard *implies* its abstract guard (no over-strengthening
      → model-check to check no new deadlock).
- [ ] Each new event marked `convergent`/`anticipated`; a `VARIANT` present and
      decreased.
- [ ] Witnesses (`WITH`) for every disappeared abstract parameter / after-value.
- [ ] `rossi validate` clean, then `rossi build` + `eventb-animate` model-checks
      clean (exit 0, `invariant_violated:0`, no unexpected deadlock), and
      `eventb-animate wd` discharges every well-definedness obligation.
