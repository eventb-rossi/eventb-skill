# Example: maximum of an array (algorithm development by refinement)

A self-contained three-level development that derives a *loop* from its
*specification*. Read it to see how an algorithm is built in Event-B: start from
"the answer satisfies this postcondition", then introduce a loop counter, a
**variant** for termination, and a **partial-progress invariant** — the recipe
behind every sequential-algorithm model.

This complements the `counter` example (refinement mechanics) and `cars_on_bridge`
(a reactive system): here the goal is a *terminating computation*.

## Files

| File | What it shows |
|---|---|
| `array_max_ctx.eventb` | The fixed input: a non-empty array as a total function `f ∈ 1‥n → ℤ` with `n ∈ ℕ1`. |
| `array_max_m0.eventb` | The **specification only**. The result `m` is set arbitrarily; the `final` event's *guard is the postcondition* (`m ∈ ran(f) ∧ ∀x· f(x) ≤ m`) and has no action — it just *recognises* a correct answer. A single `anticipated` `progress` event stands in for the not-yet-written loop. |
| `array_max_m1.eventb` | The **loop**. A counter `i` scans the array; the partial-progress invariants say "`m` is the max of `f[1‥i]`". The abstract `progress` splits into two `convergent` body events, `keep` and `update`, with `VARIANT n − i`. `final` fires when `i = n`. |
| `array_max_m2.eventb` | A superposition that also returns the **index** `p` of a maximum (`f(p) = m`), glued to `m` — a second accumulator carried alongside the first. |

## Concepts illustrated

- **Postcondition-as-guard** — the most abstract machine encodes *what* the answer
  is (the `final` guard), never *how* to compute it.
- **`anticipated` → `convergent`** — `progress` is `anticipated` in `m0` because the
  quantity that decreases (`n − i`) does not exist yet; it becomes `convergent` in
  `m1`, where the `VARIANT` is finally given. Anticipated events defer the
  termination argument to the refinement that introduces the measure.
- **Gap variant** — `n − i` strictly decreases on every loop step and the exit
  event `final` is guarded by the gap being closed (`i = n`): "variant at its bound
  ⇒ `final` enabled" is the whole termination story.
- **Partial-progress invariant** — `m ∈ f[1‥i]` and `∀x· x ∈ 1‥i ⇒ f(x) ≤ m` are the
  postcondition *restricted to the processed prefix*; at `i = n` they become the full
  postcondition, which is exactly what discharges `final`'s guard-strengthening.
- **Body/exit split with exhaustive guards** — `keep` (`f(i+1) ≤ m`), `update`
  (`f(i+1) > m`) and `final` (`i = n`) are jointly exhaustive, so the machine never
  deadlocks before producing the answer (model checking reports `deadlocked:0`).
- **Index-in-range guard** — `i ≠ n` guarantees `i+1 ∈ 1‥n`, so `f(i+1)` is
  well-defined before it is read.
- **Second accumulator (`m2`)** — `p` is introduced by superposition and kept in step
  with `m` by the gluing-style invariant `f(p) = m`.

## Run it

```sh
rossi validate .                     # static + semantic checks
rossi fmt --check *.eventb           # confirm canonical formatting
rossi build . -o /tmp/array_max.zip  # static-check -> .bcm/.bcc (needed to model-check)
eventb-animate /tmp/array_max.zip    # model-checks array_max_m2
```

`eventb-animate` auto-selects the most refined machine; use `-m array_max_m1` (or
`-m array_max_m0`) to model-check an earlier level. A clean run exits 0 with
`invariant_violated:0`, `deadlocked:0`.

### Watch the loop run — and make the check exhaustive

The context leaves the array abstract (`n ∈ ℕ1`, `f ∈ 1‥n → ℤ`), so the state
space is unbounded: `eventb-animate` bounds it by the set size, reports
`not an exhaustive check`, and the small instances it explores leave `keep`/`update`
**uncovered** (with `n = 1` the loop exits immediately). To watch `keep`/`update`
step across a real array — *and* turn the run into a genuine exhaustive check —
build a throwaway copy that **pins the context's constants** the machines already
`SEES` (ProB then has one concrete, finite array to scan):

```sh
mkdir -p /tmp/maxdemo && cp array_max_m*.eventb /tmp/maxdemo/
cat > /tmp/maxdemo/array_max_ctx.eventb <<'EOF'
CONTEXT array_max_ctx
CONSTANTS n f
AXIOMS
    @axm1 n = 5
    @axm2 f = {1 ↦ 3, 2 ↦ 5, 3 ↦ 5, 4 ↦ 2, 5 ↦ 7}
END
EOF
rossi build /tmp/maxdemo -o /tmp/maxdemo.zip
eventb-animate /tmp/maxdemo.zip   # full state space explored; covers keep, update, final
```

With the constants pinned the reachable state space is finite, so the run reports
`full state space explored` and covers `keep`/`update`/`final` — an exhaustive proof
that this array is scanned correctly.
