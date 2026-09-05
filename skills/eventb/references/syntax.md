# `.eventb` concrete syntax

The ground truth for `.eventb` syntax is the parser inside `rossi` itself. This
page is the practical surface-syntax reference; every snippet here has been run
through `rossi validate`. When in doubt, **write it and run `rossi validate`** —
the parser is the authority, and `rossi fmt` will rewrite anything well-formed
into the canonical shape shown below.

## A file holds components

A `.eventb` file contains one or more **components**, each either a `CONTEXT` or a
`MACHINE`. Convention: one component per file, file name = component name
(`bridge_m0.eventb` holds `MACHINE bridge_m0`). `rossi import` produces files this
way and the tools happily take many files at once.

## Conventions the formatter enforces

- **Keywords are case-insensitive on input** (`machine`, `Machine`, `MACHINE` all
  parse). `rossi fmt --style rossi` — this skill's style — canonicalizes structural
  keywords to **UPPERCASE**; 0.2's default `--style camille` emits them lowercase.
- **Operators may be ASCII or Unicode on input** (`:=`/`≔`, `:`/`∈`, `NAT`/`ℕ`,
  `|->`/`↦`, `<=`/`≤`). `rossi fmt` canonicalizes to **Unicode**. See
  `math-toolkit.md` for the full spelling table.
- **Indentation** is four spaces; each clause keyword sits on its own line with its
  payload indented under it. Let `rossi fmt -i --style rossi` do it, never by hand.
- **Comments**: `// line` and `/* block */`. They parse, but `fmt` reflows them
  unpredictably (a line comment migrates onto the preceding token's line), so keep
  `.eventb` files comment-free and put prose in a sibling `README.md`.
- **Identifier lists are whitespace-separated, not comma-separated.** In `SEES`,
  `VARIABLES`, `CONSTANTS`, `SETS`, `ANY`, items are separated by spaces/newlines.
  Commas appear only *inside formulas* (set enumerations `{1, 2}`, quantifier
  variable lists `∀x,y·…`, predicate calls `partition(S, a, b)`).
- **Identifiers** are alphanumeric + `_` (no hyphens), starting with a letter or
  `_`. A single trailing prime marks an after-state value: `x'` (used in witnesses
  and becomes-such-that). **Component and event names** additionally allow internal
  hyphens (`A-C0`).

## Context

The static part: carrier sets, constants, and the axioms they obey. All clauses
are optional and may appear in any order; `END` closes the component.

```
CONTEXT bridge_ctx2
EXTENDS
    bridge_ctx
SETS
    COLOR
CONSTANTS
    red
    green
AXIOMS
    @axm1 partition(COLOR, {green}, {red})
    @thm1 theorem  d ∈ ℕ1
END
```

| Clause | Meaning |
|---|---|
| `EXTENDS` | inherit the sets/constants of other contexts (transitive). |
| `SETS` | declare fresh **carrier sets** (new pairwise-disjoint types; assumed non-empty), by name only. To *enumerate* one, list its members in `CONSTANTS` and give a single `partition` axiom as above — see `math-toolkit.md`. |
| `CONSTANTS` | declare constant identifiers. |
| `AXIOMS` | labelled predicates the constants satisfy (assumed true). |
| `THEOREMS` | labelled predicates that should *follow from* the axioms (out of scope here, but accepted). |

**Theorems** can also be flagged inline inside `AXIOMS`/`INVARIANTS` with the
`theorem` keyword (either order): `@thm1 theorem P` or `theorem @thm1 P`. Write one
only when it *derives* something later obligations reuse — `@thm1` above needs both
inherited axioms. `partition` already gives `green ≠ red`, so restating it as a
theorem proves nothing.

## Machine

The dynamic part: state (variables) constrained by invariants, changed by events.

```
MACHINE bridge_m1
REFINES
    bridge_m0
SEES
    bridge_ctx
VARIABLES
    a
    b
    c
INVARIANTS
    @inv1 a ∈ ℕ
    @inv4 a + b + c = n
VARIANT
    2 ∗ a + b
EVENTS
    EVENT INITIALISATION
    THEN
        @act1 a ≔ 0
    END
    ...
END
```

| Clause | Meaning |
|---|---|
| `REFINES` | the (single) abstract machine this one refines. |
| `SEES` | the contexts whose sets/constants are visible here. |
| `VARIABLES` | the state identifiers. |
| `INVARIANTS` | labelled predicates always true of the state (typing first, then safety; a predicate mentioning an abstract variable is a *gluing invariant*). |
| `THEOREMS` | predicates provable from the invariants (out of scope, accepted). |
| `VARIANT` | a ℕ-valued or finite-set expression; required when the machine has `convergent`/`anticipated` events. |
| `EVENTS` | the events (must be the last clause). |

## Events

```
EVENT add
REFINES
    add
ANY
    k
WHERE
    @grd1 k ∈ ℕ1
    @grd2 level + k ∗ step ≤ cap
WITH
    @d d = k ∗ step
THEN
    @act1 level ≔ level + k ∗ step
END
```

Clause order inside an event is fixed: **status → refines → any → where → with →
then**.

| Clause | Meaning |
|---|---|
| status | `ordinary` (default), `convergent`, or `anticipated`. Written as an **inline prefix**: `convergent EVENT IL_in` (the canonical form `fmt` produces) — a `STATUS\n convergent` block is also accepted on input. |
| `REFINES` | the abstract event(s) this refines. Several concrete events may refine the same abstract event (**event splitting**: `ML_out_1` and `ML_out_2` both `REFINES ML_out`). Inherits **nothing** — the event restates its full parameter/guard/action set. |
| `extends` | **extended event** — a header form replacing `REFINES`: `EVENT inc extends inc`. Inherits the abstract event's parameters, guards and actions implicitly; the body lists only the *additions* and may be empty. Single abstract target. See [refinement.md](refinement.md) § Extended events. |
| `ANY` | event **parameters** (local, non-deterministic), whitespace-separated. |
| `WHERE` / `WHEN` | **guards** — labelled predicates; the event may occur only when all hold. `WHEN` is a synonym (`fmt` normalizes it to `WHERE`). |
| `WITH` | **witnesses** for abstract parameters / after-values that disappear under refinement (see `refinement.md`). Label is the witnessed name: `@d d = …`, `@count' count' = …`. |
| `THEN` / `BEGIN` | **actions**. `BEGIN` is a synonym for `THEN`. |

### INITIALISATION

Every machine has the special event `INITIALISATION`: no guard, no parameters,
just actions establishing the invariant in the start state.

```
EVENT INITIALISATION
THEN
    @act1 n ≔ 0
END
```

In a refining machine, `EVENT INITIALISATION extends INITIALISATION` inherits the
abstract initialisation and lists only the actions for the new variables.

## Actions

Actions in one `THEN` run **simultaneously** (order is irrelevant; right-hand
sides read the *before* state). **A variable may be assigned by at most one action
of an event.** Labels (`@act1`) are optional but recommended.

| Form | Syntax | Meaning |
|---|---|---|
| Deterministic | `x ≔ E` | becomes equal to `E`. |
| Parallel (multi) | `x, y ≔ E, F` | simultaneous deterministic assignment. |
| Functional override | `f(i) ≔ E` | shorthand for `f ≔ f <+ {i ↦ E}` (relational override). |
| Becomes-in | `x :∈ S` | becomes an arbitrary member of set `S`. |
| Becomes-such-that | `x :∣ P` | becomes any value(s) making predicate `P` true; `x'` denotes the after-value, e.g. `count :∣ count' ∈ ℕ ∧ count' < count`. |
| Skip | `skip` | no change. |

(Unicode `:∣` / `≔` are the canonical spellings of `:|` / `:=`.)

## Labels

A label is `@` followed by any run of non-whitespace characters: `@inv1`, `@grd2`,
`@act1`, and even primed/quoted forms like `@count'`. Labels are required on
invariants, axioms, guards, witnesses, and theorems; optional on actions.

## Minimal templates

Context:

```
CONTEXT c
CONSTANTS
    k
AXIOMS
    @axm1 k ∈ ℕ
END
```

Machine:

```
MACHINE m
SEES
    c
VARIABLES
    x
INVARIANTS
    @inv1 x ∈ ℕ
EVENTS
    EVENT INITIALISATION
    THEN
        @act1 x ≔ 0
    END

    EVENT step
    WHERE
        @grd1 x < k
    THEN
        @act1 x ≔ x + 1
    END
END
```

See `math-toolkit.md` for operators, `modelling.md`/`refinement.md` for how to use
these constructs, and `tooling.md` for `validate`/`fmt`/`build`/model-check.
