# Distributed, concurrent, and long-running patterns

Field-guide idioms for systems with more than one participant or more than one step:
network topology, round-based and consensus algorithms, interleaved processes,
unreliable channels, and operations that can partly succeed. Extends the core
reactive-system patterns in [patterns.md](patterns.md) with shapes observed across
substantial, publication-backed developments.

Snippets are **illustrative fragments** (a context, an event, a few invariants) in the
skill's surface syntax — not standalone-checkable files. Operator spellings follow
[math-toolkit.md](math-toolkit.md) (note: relational override is `<+`).

## Contents

- [Distributed and concurrent systems](#distributed-and-concurrent-systems) — topology as a relation, round-based algorithms, leader election, consensus safety, mutual exclusion, program counters, decentralizing data refinement, anonymity
- [Communication channels](#communication-channels) — lossy channels, bounded retransmission
- [Fallible and long-running operations](#fallible-and-long-running-operations) — atomic service split into start/step/success/failure

## Distributed and concurrent systems

### Network/topology as a relation in a context

Model a network of nodes by a carrier set `NODE` plus an edge relation, and pin its
shape with axioms. Neighbours are `adj[{x}]`; "acyclic" is expressed without
recursion as "no non-empty node-set is closed under the successor."

```eventb
CONTEXT topology
SETS NODE
CONSTANTS adj
AXIOMS
    @t   adj ∈ NODE ↔ NODE
    @sym adj = adj∼                            // undirected
    @irr NODE ◁ id ∩ adj = ∅                   // no self-loops
    @con ∀S· S ≠ ∅ ∧ adj[S] ⊆ S ⇒ NODE ⊆ S     // connected
    @acy ∀S· S ⊆ NODE ∧ S ⊆ adj[S] ⇒ S = ∅     // acyclic ⇒ it is a tree
END
```

### Round-based algorithms with a distinguished decision round

Drive a round-based algorithm with one counter `rnd` whose value partitions execution
into before / at / after a decisive round `k`. `k` can be an *unknown* constant
asserted only to exist; a "done" phase (`rnd = R + 1`) signals termination. The safety
property is "guaranteed once past the decision round."

```eventb
INVARIANTS @safe rnd > k ⇒ agreed(st)
EVENT pre_round  WHERE @g rnd < k           THEN @a rnd ≔ rnd + 1 END
EVENT decision   WHERE @g rnd = k           THEN @a rnd ≔ rnd + 1 END   // establishes agreed(st)
EVENT post_round WHERE @g rnd > k ∧ rnd ≤ R THEN @a rnd ≔ rnd + 1 END
```

### Leader election (elect only when one candidate remains)

State the goal abstractly as "pick any node as leader"; in refinement keep a shrinking
candidate set and strengthen `elect`'s guard so it fires only when one candidate is
left — *uniqueness emerges from the protocol* rather than being assumed.

```eventb
// abstract:   EVENT elect ANY x WHERE @g x ∈ NODE THEN @a leader ≔ x END
// refinement: EVENT elect REFINES elect ANY x WHERE @g cand = {x} THEN @a leader ≔ x END
```

### Consensus safety: agreement + validity over *correct* agents

Capture a consensus protocol with two invariants on a partial `decided` map, both
scoped to a `correct ⊆ AGENT` subset (the standard way to model fault tolerance —
faulty agents are excluded by restriction, not removed).

```eventb
INVARIANTS
    @typ   decided ∈ AGENT ⇸ VALUE
    @agree ∀p,q· {p,q} ⊆ correct ∩ dom(decided) ⇒ decided(p) = decided(q)   // agreement
    @valid ∀p· p ∈ correct ∩ dom(decided) ⇒ decided(p) ∈ proposal[correct]  // validity
```

### Mutual exclusion with a `turn` tie-breaker

"At most one in the critical section" is a plain disjunction `csA = 0 ∨ csB = 0`.
Refinement breaks the symmetric deadlock with a `turn` variable that weakens one
entry guard and is recorded by one-way implication invariants.

```eventb
INVARIANTS
    @mutex csA = 0 ∨ csB = 0                    // safety (abstract)
    @tie   turn = A ∧ wantA = 1 ⇒ csB = 0       // the turn resolves the tie one way
EVENT enterA REFINES enterA
    WHERE @g1 wantA = 1  @g2 csA = 0  @g3 wantB = 0 ∨ turn = A THEN @a csA ≔ 1 END
```

### Per-process program counter

Model interleaved imperative processes by giving each its own counter `pc ∈ 1 ‥ k`,
one event per atomic statement guarded by `pc = i`. Data-race freedom is then a safety
invariant relating the two counters.

```eventb
INVARIANTS @race pcW = 3 ∧ pcR = 2 ⇒ slotW ≠ slotR   // never touch one cell at once
EVENT W_write WHERE @g pcW = 3 THEN @a1 buf(slotW) ≔ x  @b pcW ≔ 4 END
```

### Decentralizing data refinement (global → local → counter)

A refinement ladder that turns a centralized spec into a distributed one: a guard
reading a global structure becomes a per-node set, then a per-node integer counter,
each tied to its predecessor by a gluing invariant — until every guard a node
evaluates is local (`deg(x) = 0`, `deg(x) = 1`).

```eventb
@glue1 ∀x· x ∈ active ⇒ nb(x) = adj[{x}] ∩ active     // global image → per-node set
@glue2 ∀x· x ∈ dom(deg) ⇒ deg(x) = card(nb(x))        // set → scalar counter
```

### Anonymity via an indistinguishability set

Model secrecy by carrying the observer's set `K` of still-possible secret states.
Each public action *filters* `K`; the anonymity property is "the whole class of
indistinguishable secrets stays in `K`" — the observer cannot narrow within it.

```eventb
INVARIANTS @anon acted(secret) ⇒ class(secret) ⊆ K
EVENT observe THEN @a K ≔ {s · s ∈ K ∧ pub(s) = pub(secret) ∣ s} END
```

> **Caution (validation ≠ proof).** An over-strong indistinguishability invariant here
> is *unprovable* even though the model still validates and model-checks cleanly — see
> [refinement.md](refinement.md) ("model checking is not proof") for why.

---

## Communication channels

Extends the protocol pattern in [patterns.md §7](patterns.md).

### Lossy channel (silent drop daemon)

Model arbitrary message loss with a stand-alone daemon event whose only precondition
is "a message is present" and which just empties the channel.

```eventb
EVENT drop WHERE @g inflight = TRUE THEN @a inflight ≔ FALSE END   // silent loss
```

### Bounded retransmission (retry counter + failure threshold)

A retry counter capped at `MAX`, a `timeout` event that re-arms the sender, and a
failure state reached exactly when the counter overflows.

```eventb
INVARIANTS
    @c2 retries ∈ 0 ‥ MAX + 1
    @c3 retries = MAX + 1 ⇔ st = failure
EVENT timeout WHERE @g1 inflight = FALSE  @g2 retries < MAX THEN @a retries ≔ retries + 1 END
EVENT give_up WHERE @g  retries = MAX THEN @a1 st ≔ failure  @a2 retries ≔ retries + 1 END
```

## Fallible and long-running operations

### Atomic service → start/step/success/failure

First model the operation as one abstract event with its successful postcondition.
When implementation detail matters, refine it into an explicit protocol:

- `op_start` captures parameters and creates temporary state;
- one or more convergent `op_step` events shrink a finite work set or gap;
- `op_end_ok` establishes the abstract postcondition;
- `op_end_fail` establishes the specified failure/rollback state.

The essential invariant describes partial progress, so completing the work set is
enough to establish the abstract result.

```eventb
INVARIANTS
    @p1 phase ∈ {idle, busy}
    @p2 remaining ⊆ ITEM
    @p3 completed = job ∖ remaining
    @p4 phase = idle ⇒ remaining = ∅
VARIANT remaining
convergent EVENT op_step
    ANY x
    WHERE @g1 phase = busy  @g2 x ∈ remaining
    THEN  @a1 remaining ≔ remaining ∖ {x}
          @a2 temp ≔ apply_one(temp ↦ x) END
```

Plan convergence for every internal event, including entry to the protocol; a
phase-weighted natural variant or an earlier `anticipated` step is often needed
because `op_start` initially creates work. Make the success and failure guards
disjoint, and decide whether failure preserves partial effects, rolls them back, or
marks them for recovery.

Evidence: [Applying Event and Machine Decomposition to a Flash-Based Filestore in Event-B](https://eprints.soton.ac.uk/268301/1/FileSysSBMF.pdf).
