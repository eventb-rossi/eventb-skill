# Example: bounded counter (data refinement + witnesses)

A small, self-contained two-level development. Read it to see the *mechanics* of
refinement — `REFINES`, gluing invariants, and `WITH` witnesses — without any
domain noise.

## Files

| File | What it shows |
|---|---|
| `counter_ctx.eventb` | A context: one constant `cap ∈ ℕ1` (the capacity). |
| `counter_abstract.eventb` | The abstract machine. State `count`; typing invariant `count ∈ ℕ` and safety invariant `count ≤ cap`. `add` increases the count by a **non-deterministic** amount (`ANY d`); `remove` decreases it **non-deterministically** (`count :∣ count' ∈ ℕ ∧ count' < count`). |
| `counter_concrete.eventb` | A data refinement. The abstract `count` is **replaced** by `level`, glued with `@glue count = level`; a new variable `step` is introduced. `add`/`remove` become deterministic (move by `step`); a new event `set_step` changes the step. |

## Concepts illustrated

- **Typing invariant first** — every variable gets a `v ∈ …` invariant before any
  safety property.
- **Non-determinism in the abstraction** — `ANY d` (parameter) and `:∣`
  (becomes-such-that) leave choices open, to be pinned down by the refinement.
- **Data refinement** — `count` disappears in the concrete machine; the **gluing
  invariant** `count = level` ties the two state spaces together.
- **Witnesses (`WITH`)** — when an abstract quantity vanishes concretely you must
  witness it:
  - `@d d = k ∗ step` witnesses the disappeared abstract **parameter** `d` of `add`.
  - `@count' count' = level − step` witnesses the disappeared abstract
    **after-value** `count'` of the non-deterministic `remove`.
- **New event** — `set_step` exists only in the refinement (it refines `skip`).

## Run it

```sh
rossi validate .                  # static + semantic checks
rossi fmt --check *.eventb        # confirm canonical formatting
rossi build . -o /tmp/counter.zip # static-check -> .bcm/.bcc (needed to model-check)
eventb-animate /tmp/counter.zip   # model-checks counter_concrete
```

`eventb-animate` auto-selects the most refined machine; use
`-m counter_abstract` to model-check the abstract level instead. A clean run exits 0
with `invariant_violated:0` and `deadlocked:0`.
