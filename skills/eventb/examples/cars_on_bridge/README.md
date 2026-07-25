# Example: cars on a bridge (the canonical Event-B development)

The classic Event-B development: a controller for a one-way bridge connecting the
mainland to a small island, with a bounded capacity and traffic lights. It is the
best single illustration of an Event-B **refinement chain**.

## The refinement chain

| Level | File(s) | Idea introduced |
|---|---|---|
| 0 — initial model | `bridge_ctx.eventb`, `bridge_m0.eventb` | Just *count the cars*. One variable `n` (cars in the bridge+island compound), invariant `n ≤ d` (capacity). Events `ML_out` (a car enters) / `ML_in` (a car leaves). |
| 1 — one-way bridge | `bridge_m1.eventb` | **Data refinement**: `n` is replaced by three variables `a` (on bridge → island), `b` (on island), `c` (on bridge → mainland). Gluing invariant `a + b + c = n`; safety invariant `a = 0 ∨ c = 0` (the bridge is one-way). Two **new convergent events** `IL_in` / `IL_out` move cars across, with `VARIANT 2 ∗ a + b`. |
| 2 — traffic lights | `bridge_ctx2.eventb`, `bridge_m2.eventb` | **Superposition refinement**: `a, b, c` are kept and traffic lights `ml_tl, il_tl ∈ COLOR` are added. Conditional gluing invariants (`ml_tl = green ⇒ …`) and `inv5` (never both green). The two **new convergent** light-switch events use a boolean→number variant `b_2_n(ml_pass) + b_2_n(il_pass)`. |

## Concepts illustrated

- **Successive approximation** — three models, each more precise, none
  contradicting its predecessor.
- **Data refinement vs superposition** — level 1 *replaces* the abstract variable
  (`n` → `a,b,c`); level 2 *keeps* the variables and *adds* new ones.
- **Gluing invariants** — `a + b + c = n` (level 1); the conditional
  `ml_tl = green ⇒ a + b < d ∧ c = 0` (level 2).
- **New events + convergence** — new events refine `skip` and are marked
  `convergent`; a `VARIANT` (a ℕ-expression that strictly decreases) proves they
  cannot run forever and starve the bridge.
- **Event splitting** — abstract `ML_out` becomes `ML_out_1` / `ML_out_2` at
  level 2 (both `REFINES ML_out`), distinguishing the last car (turns the light
  red) from the rest.
- **Enumerated set + booleans** — `COLOR = {green, red}`; `BOOL`, `TRUE`/`FALSE`,
  and a `BOOL → {0,1}` conversion used to build a numeric variant.

## Run it

```sh
rossi validate .
rossi build . -o /tmp/cars.zip
eventb-animate -m bridge_m2 /tmp/cars.zip   # the traffic-light cycle
eventb-animate -m bridge_m1 /tmp/cars.zip   # the one-way bridge
eventb-animate -m bridge_m0 /tmp/cars.zip   # the abstract counter
```

Each level model-checks clean (exit 0, `invariant_violated:0`, `deadlocked:0`). The
`bridge_m2` state space contains the realistic cycle
`ML_tl_green → ML_out_2 → IL_in → IL_tl_green → IL_out_2 → ML_in`.
A clean check has no counterexample for `--save`; capture the path to `c > 0` as
a goal trace instead (goal hits deliberately exit 1), then replay it. This trace
stops after `IL_out_2`, with `ML_in` enabled as the return transition:

```sh
eventb-animate -m bridge_m2 --goal 'c > 0' --no-invariant --no-deadlock \
  --save /tmp/cars-trace.json /tmp/cars.zip
eventb-animate replay -m bridge_m2 -t /tmp/cars-trace.json /tmp/cars.zip
```

The saved ProB trace uses JSON format 6 and replay reports `PERFECT`.

## Note on the level-2 initialisation

The level-2 `INITIALISATION` (both lights red, both "pass" flags `TRUE`) is the
unique consistent start state, and is spelled out here rather than left implicit.
Authoring interactive proofs is out of scope — correctness is checked by model
checking (every level reports `invariant_violated:0`, `deadlocked:0`, exit 0).
