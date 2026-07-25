# Algorithm, interpreter, and code-generation patterns

Field-guide idioms for deriving a *program* by refinement: a loop from its
postcondition, and an interpreter or ISA from a single abstract step. Extends the core
reactive-system patterns in [patterns.md](patterns.md) with shapes observed across
substantial, publication-backed developments. For the mechanics of `VARIANT`,
`convergent`, and `anticipated`, see [refinement.md](refinement.md).

Snippets are **illustrative fragments** (a context, an event, a few invariants) in the
skill's surface syntax — not standalone-checkable files. The fully runnable, validated
shape for the algorithm section lives in
[`examples/array_maximum`](../examples/array_maximum). Operator spellings follow
[math-toolkit.md](math-toolkit.md) (note: relational override is `<+`).

## Contents

- [Algorithm development by refinement](#algorithm-development-by-refinement) — postcondition as a `final` guard, `anticipated` → `convergent`, gap and set variants, partial-progress invariant, body/exit split, arrays as functions, permutation ghosts, determinisation
- [Interpreters and machine-state models](#interpreters-and-machine-state-models) — ISA state vector, status-driven progressive split, generic core → architecture branches → code normal form

## Algorithm development by refinement

A whole genre: derive a *loop* from its *specification*. The validated worked example
is [`examples/array_maximum`](../examples/array_maximum); the idioms below are its
moving parts. The skeleton is always: **context = the fixed input** → **m0 = the
specification only** → **m1 = the loop (counter + variant + partial-progress
invariant)** → **m_last = deterministic, directly codeable**.

### Postcondition as the guard of a `final` event

The most abstract machine encodes *what* the answer is, never *how*: the result is set
arbitrarily, and a terminal `final` event whose **guard is the postcondition** (often
with no action) simply *recognises* a correct answer.

```eventb
EVENT final                       // "r indexes an occurrence of key" — no THEN
    WHERE @grd1 r ∈ 1 ‥ n
          @grd2 f(r) = key END
```

### `anticipated` placeholder → `convergent` loop body

The spec machine carries one `anticipated` `progress` event that merely scrambles the
result and has *no variant* — because the quantity that decreases does not exist yet.
The refinement that introduces the loop counter is where `progress` splits into
`convergent` body events and the `VARIANT` is finally given.

### Gap variant and set variant

The termination measure is usually a **gap** between a moving index and a fixed bound
(`n − i`), or the **size of a shrinking region**; the exit event is guarded by the gap
being closed (`i = n`). A variant need not be a number — a finite **set** is a valid
variant and decreases whenever an element is removed.

```eventb
VARIANT remaining                 // remaining ⊆ TASK : decreases under ⊂
EVENT work ANY x WHERE @g x ∈ remaining THEN @a remaining ≔ remaining ∖ {x} END
```

### Partial-progress (loop) invariant

The central refinement invariant is the postcondition *restricted to the processed
region* — so that when the gap closes it *becomes* the full postcondition, which is
exactly what discharges the exit event.

```eventb
@inv2 m ∈ f[1 ‥ i]                 // "m is the max seen so far" …
@inv3 ∀x· x ∈ 1 ‥ i ⇒ f(x) ≤ m     // … which at i = n is the full postcondition
```

### Body/exit split with exhaustive guards

Refine the one abstract step into body events that partition on a data comparison plus
an exit event on the variant bound; keep the guards **jointly exhaustive** so the
machine never deadlocks before producing the answer (`eventb-animate` then reports
`deadlocked:0`).

### Array as a function; swap by override

Model arrays as functions `1 ‥ n → VALUE`; an in-place swap is a double functional
override, and every access needs an index-in-range guard.

```eventb
EVENT swap ANY i j WHERE @g1 i ∈ 1 ‥ n  @g2 j ∈ 1 ‥ n   // WD: both indices in dom before access
    THEN @a a ≔ a <+ {i ↦ a(j), j ↦ a(i)} END
```

### Permutation ghost, then data-refined away

To say "the output is a rearrangement of the input" abstractly, carry a bijection
`perm` over indices and define the visible array as the composition `out = perm ; f`;
a later refinement drops `perm`, with `out = perm ; f` as the gluing invariant.

### Determinisation as the closing step

The last machine replaces every `:∈`/`:∣` with a closed-form assignment and makes the
guards a disjoint, exhaustive decision tree — an `if/elif/else` ready to transcribe to
code (e.g. `r :∈ lo ‥ hi` becomes `r ≔ (lo + hi) ÷ 2`).

---

## Interpreters and machine-state models

### Interpreter / ISA state vector

A reusable state shape for any byte-code VM or processor: registers as a total
function over a zero-indexed interval (holding integer machine words), memory and the
loaded program as functions over address intervals, and a program counter. Reads are
function application; writes are functional override; multi-core nests the register
file one level (`THREAD → (REG → ℤ)`).

```eventb
INVARIANTS
    @t1 regs ∈ REG_DOM → ℤ             // register file (integer words)
    @t2 mem  ∈ MEM_DOM → ℤ             // memory map
    @t3 prog ∈ MEM_DOM → INSTR         // loaded program
EVENT step ANY r v WHERE @g1 r ∈ REG_DOM  @g2 r ≠ PC_IDX  @g3 v ∈ ℤ
    THEN @a regs ≔ regs <+ {r ↦ v, PC_IDX ↦ regs(PC_IDX) + 1} END   // one action: write a register *and* advance the PC
```

### Status-driven progressive split (fetch-decode-execute)

Build the interpreter loop by refinement: an abstract single `iterate` event updates a
`status` over `{LOADING, RUNNING, HALTED, FAILED}`; each refinement *splits* `iterate`
first by status, then by instruction class — and in lock-step a **parallel context
refinement** splits the instruction carrier set (`Inst = ValidInst ∪ InvalidInst`, …).
Choose the terminal semantics explicitly. With no event enabled at `HALTED`, the state
is an intentional deadlock and should be documented as such. A guard-only `halted`
event instead models observable stuttering at `HALTED`; because it remains enabled,
it prevents deadlock and is not a terminal transition.

```eventb
// abstract:    EVENT iterate THEN @a status :∈ STATUS END
// refinement:  EVENT running REFINES iterate WHERE @g status = RUNNING
//                  THEN @a status :∈ {RUNNING, HALTED, FAILED} END
//              EVENT halted  REFINES iterate WHERE @g status = HALTED END   // optional stutter
```

### Generic core → architecture branches → code normal form

For a substantial ISA, refine one generic execution contract through coherent
layers—control flow, register/storage access, memory, flags, and calculations—while
refining the instruction-set context in parallel. Branch into stack/register or
other architecture-specific state only after the common instruction semantics are
stable.

Reserve the last refinement for the code generator's mathematical subset. It may
replace symbolic constants with literals, range membership with comparisons, or
global assignment forms with equivalent local ones, but it must introduce no new
requirement. Prove this representation-only step, then replay model traces against
the generated executable.

Large final machines need generated inventories and refinement-delta views; a
100-event file is not a practical review interface by itself.

Evidence: [MIDAS practical experience](https://research-information.bris.ac.uk/en/publications/practical-experiences-constructing-working-virtual-machines)
and [B2C normal-form guidance](https://wiki.event-b.org/index.php/B2C_plugin).
