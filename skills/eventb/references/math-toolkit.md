# Event-B mathematical toolkit

The language of predicates and expressions used in axioms, invariants, guards,
actions, variants and witnesses. Each operator has a **Unicode** spelling (what
`rossi fmt` emits) and an **ASCII** spelling (convenient to type; rossi accepts
it). Semantics follow the standard Event-B / Rodin mathematical toolkit; the
spellings below are exactly those rossi accepts (verify any with
`echo '…' | rossi validate -`).

> Notation: `S, T` sets · `r` relation · `f, g` functions · `m, n` integers ·
> `P, Q` predicates · `E, F` expressions · `x, y` variables.

## Predicates (logic)

| Unicode | ASCII | Meaning | Notes |
|---|---|---|---|
| `⊤` / `⊥` | `true` / `false` | truth / falsity | |
| `∧` | `&` | and | `∧`/`∨` **cannot be mixed without parentheses**. |
| `∨` | `or` | or | |
| `⇒` | `=>` | implies | **non-associative** — parenthesize `P ⇒ (Q ⇒ R)`. |
| `⇔` | `<=>` | iff | non-associative. |
| `¬` | `not` | not | |
| `∀ x · P` | `! x . P` | for all | usually `∀x·P ⇒ Q`; type of `x` inferable from `P`. |
| `∃ x · P` | `# x . P` | there exists | usually `∃x·P ∧ Q`. |
| `·` | `.` | quantifier/binder separator | |

The binder separator and comprehension/lambda bodies use `·` (dot). Variable lists
in quantifiers are comma-separated: `∀x,y·P`.

## Comparison

| Unicode | ASCII | | Unicode | ASCII |
|---|---|---|---|---|
| `=` | `=` | | `≠` | `/=` |
| `<` | `<` | | `≤` | `<=` |
| `>` | `>` | | `≥` | `>=` |

## Sets

| Unicode | ASCII | Meaning |
|---|---|---|
| `∈` / `∉` | `:` / `/:` | membership / non-membership |
| `⊆` / `⊈` | `<:` / `/<:` | subset / not subset |
| `⊂` / `⊄` | `<<:` / `/<<:` | proper subset / not |
| `∪` / `∩` | `\/` / `/\` | union / intersection |
| `∖` | `\` | set difference |
| `×` | `**` | Cartesian product |
| `ℙ` / `ℙ1` | `POW` / `POW1` | powerset / non-empty powerset |
| `∅` | `{}` | empty set |
| `{E, F}` | | set enumeration |
| `{ x · P \| E }` | | set comprehension (general); also `{ x \| P }` and `{ E \| P }` |
| `⋃ x · P \| E` | `UNION x.P \| E` | quantified union |
| `⋂ x · P \| E` | `INTER x.P \| E` | quantified intersection |

Set-valued operators written as **application** (identifier + parentheses):
`card(S)`, `finite(S)`, `min(S)`, `max(S)`, `union(U)`, `inter(U)`,
`partition(S, A, B)`.

> **No finite sum/product (Σ/Π).** The core toolkit has no fold over a set — that needs
> the Theory plugin, out of scope here. For value/quantity **conservation**, track an
> **incremental counter** updated in the relevant action and pin each contribution with a
> **per-element structural invariant** — e.g. `minted ∈ S ⇸ ℕ` with
> `∀s· s ∈ dom(minted) ⇒ minted(s) = amount(s)`. A one-directional counter invariant such
> as `total_out ≤ total_in` expresses **solvency**, not full conservation — it silently
> misses the under-counting direction.

`partition(S, A, B)` asserts the parts are disjoint and cover `S`. With **singleton** parts —
`partition(COLOR, {red}, {green})` — it is *the* way to enumerate a carrier set: the members
are ordinary `CONSTANTS`, coverage fixes `S` to exactly them, and disjointness of the
singletons is what makes them pairwise distinct. It stays one axiom where explicit `≠` pairs
grow quadratically. The parts may instead be named **subsets** that are themselves
partitioned, building a structured/hierarchical type:
`partition(PERM, USER_PERM, GROUP_PERM)` then `partition(USER_PERM, {read}, {write})`.

## Numbers

| Unicode | ASCII | Meaning |
|---|---|---|
| `ℤ` | `INT` | integers |
| `ℕ` | `NAT` | naturals (≥ 0) |
| `ℕ1` | `NAT1` | positive naturals (≥ 1) |
| `+` `−` `∗` `÷` | `+` `-` `*` `/` | arithmetic (`−`/`∗` are the canonical minus/multiply) |
| `mod` | `mod` | remainder |
| `^` | `^` | exponentiation |
| `m ‥ n` | `m .. n` | integer interval `{ i \| m ≤ i ≤ n }` |

## Relations

A relation is a set of pairs. Build a pair with the **maplet** `↦` (`|->`).

| Unicode | ASCII | Meaning |
|---|---|---|
| `↦` | `\|->` | maplet (ordered pair) — also typed as `,,` |
| `↔` | `<->` | relation `S ↔ T = ℙ(S × T)` |
| `` | `<<->` | total relation |
| `` | `<->>` | surjective relation |
| `` | `<<->>` | total surjective relation |
| `dom(r)` / `ran(r)` | | domain / range (parentheses required) |
| `r∼` | `r~` | inverse (postfix) |
| `r[S]` | | relational image |
| `◁` / `⩤` | `<\|` / `<<\|` | domain restriction / subtraction |
| `▷` / `⩥` | `\|>` / `\|>>` | range restriction / subtraction |
| `` | `<+` | relational override `r1 <+ r2` |
| `;` | `;` | forward composition `p ; q` |
| `∘` | `circ` | backward composition |
| `⊗` | `><` | direct product |
| `∥` | `\|\|` | parallel product |
| `id` | | identity relation |
| `prj1` / `prj2` | | projections |

The total/surjective-relation arrows and override have **no standard Unicode
glyph** — Rodin uses private-use codepoints, so `rossi fmt` round-trips them but
they may not render in your editor. Prefer the ASCII spellings `<<->`, `<->>`,
`<<->>`, `<+` for these.

The relation constructors `↔ <<-> <->> <<->>` share a single **non-associative**
operator group with the function arrows below (no relative priority, no
associativity) — nested relation/function types must be parenthesized (see
**Functions**).

`id`, `prj1`, `prj2` are **generic** (no argument) — Rodin infers their type from
context, so scope them by domain restriction: `S ◁ id` (e.g. irreflexivity
`r ∩ id = ∅`), `(S × T) ◁ prj1` (maps `x ↦ y` to `x`), and `(S × T) ◁ prj2` (maps
`x ↦ y` to `y`). The parameterized `id(S)` / `prj1(A, B)` forms are **not** accepted.

## Functions

A function is a relation mapping each domain element to at most one value. Arrow
types bind tighter than `↦` and are **non-associative** (see the note below):

| Unicode | ASCII | Meaning |
|---|---|---|
| `⇸` | `+->` | partial function |
| `→` | `-->` | total function |
| `⤔` | `>+>` | partial injection |
| `↣` | `>->` | total injection |
| `⤀` | `+->>` | partial surjection |
| `↠` | `-->>` | total surjection |
| `⤖` | `>->>` | bijection |
| `f(E)` | | application — **single argument**; a pair is `f(x ↦ y)`, never `f(x, y)`. |
| `λ x · P \| E` | `% x . P \| E` | lambda abstraction |

> **Arrow types don't chain.** The relation and function arrows form one operator
> group with **no associativity and no relative priority**. A nested
> (higher-order / curried) type MUST be parenthesized: write `S → (T → U)` or
> `(S → T) → V`, never `S → T → U` — Rodin rejects the unparenthesized form. This
> is why the examples write `RequiredConfig ∈ MODE → (UNIT → CONFIG)`.

Function update has a compact form `f{x ↦ y}` (sugar for `f <+ {x ↦ y}`); in an
action you normally write the override directly: `f(x) ≔ y`.

## Booleans

`BOOL` is the type `{FALSE, TRUE}`. `bool(P)` converts a predicate to a `BOOL`
value. Useful for turning a flag into a number for a variant, e.g. a constant
`b_2_n ∈ BOOL → {0, 1}` with `b_2_n(TRUE) = 1`, `b_2_n(FALSE) = 0`.

**Defined operators without the Theory plugin.** Classical Event-B has no user-defined
operators; encode one as a total-function constant with a universally-quantified
defining axiom, using `bool(…)` for a predicate-valued helper:

```
@op  even ∈ ℤ → BOOL
@def ∀a· a ∈ ℤ ⇒ even(a) = bool(a mod 2 = 0)
```

then write `even(x) = TRUE` in a guard.

## Precedence (loosest → tightest)

1. `⇔`, `⇒` (non-associative — and can't be mixed with each other unparenthesized)
2. `∧`, `∨` (one level — parenthesize when mixing the two)
3. `¬`, quantifiers
4. comparison / set predicates (`=`, `∈`, `⊆`, …)
5. `↦` (maplet)
6. relation & function arrows (`↔`, `→`, …) — **non-associative**, one group; parenthesize any nesting
7. binary set operators (`∪`, `∩`, `∖`, `×`, `◁`, `;`, `⊗`, `∥`, …)
8. interval `‥`
9. `+` `−`
10. `∗` `÷` `mod`
11. `^` (exponent — non-associative)
12. unary `−`, `ℙ`, `ℙ1`
13. application `f(E)`, `r[S]`, `r∼`, `dom`/`ran`

When unsure, **parenthesize and run `rossi validate`** — and `rossi fmt` will show
you how the parser grouped your formula.

## Common gotchas

- `⇒`/`⇔` are non-associative and `∧`/`∨` can't be mixed unmodified — parenthesize.
- Relation/function arrows don't chain — parenthesize nesting: `S → (T → U)`, not `S → T → U`.
- Functions take **one** argument; use a maplet for pairs: `f(x ↦ y)`.
- `dom`/`ran` require parentheses: `dom(r)`, not `dom r`.
- A pair is `x ↦ y`, **not** `(x, y)`; commas build *lists*, not pairs.
- `∖` (set difference) and `\` are the same character to type (`\`); `/` is
  division.
