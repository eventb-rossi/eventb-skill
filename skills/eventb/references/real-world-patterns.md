# Patterns from real-world models

A domain-organized catalog of modelling idioms observed across a broad survey of
substantial and publication-backed Event-B developments — controllers, distributed
protocols, sequential algorithms, access-control systems, and interpreters. It complements
[patterns.md](patterns.md): that file holds the *core* reactive-system patterns;
this one is the wider field guide, grouped by the kind of system you are modelling.

Snippets are **illustrative fragments** (a context, an event, a few invariants) in
the skill's surface syntax — not standalone-checkable files. The fully runnable,
validated shape for the algorithm section lives in
[`examples/array_maximum`](../examples/array_maximum). Operator spellings follow
[math-toolkit.md](math-toolkit.md) (note: relational override is `<+`).

## Contents

- [Planning a substantial refinement chain](#planning-a-substantial-refinement-chain)
- [Real-time and timing](#real-time-and-timing)
- [Modes and state machines](#modes-and-state-machines)
- [Sensors and actuators](#sensors-and-actuators)
- [Distributed and concurrent systems](#distributed-and-concurrent-systems)
- [Communication channels](#communication-channels)
- [Fallible and long-running operations](#fallible-and-long-running-operations)
- [Access control and security](#access-control-and-security)
- [Algorithm development by refinement](#algorithm-development-by-refinement)
- [Interpreters and machine-state models](#interpreters-and-machine-state-models)

## Planning a substantial refinement chain

Published developments use at least two successful refinement shapes:

- a **feature ladder**, where each level adds one user-visible concern (arrival-manager
  interaction and CDIS display features); or
- a **subsystem ladder**, where each level adds a dependent group of services from a
  standard (partition/process management, IPC, then health monitoring in ARINC 653).

Before authoring either shape, keep a requirement-to-refinement ledger:

| Step | Requirement/concern | New or replaced state | Affected events | Invariant/gluing relation | Validation question |
|---|---|---|---|---|---|
| `m0` | Core observable service | Minimal state | Core events | Core safety property | Can success and forbidden scenarios be distinguished? |
| `m1` | One named concern | State needed only by it | Exact event subset | Type + safety/gluing rule | Does it constrain or split the intended behaviour? |

Use the ledger to choose steps, not to justify a chain after the fact. If a row
contains unrelated concerns, split it. When a step only strengthens inherited events
for its new concern, use `extends` so the review view exposes the delta instead of
restating every inherited guard and action.

For a normative standard, extend the ledger with the source section, assumptions,
and evidence status. A formal model is also a requirements-review artifact: the
ARINC 653 formalisation reported three errors and three incomplete specifications.

Evidence: [AMAN](https://abz-conf.org/publication/mammarl23/),
[ARINC 653](https://lvpgroup.github.io/papers/ISSRE2015.pdf), and
[CDIS](https://eprints.soton.ac.uk/264964/).

## Real-time and timing

The single biggest gap a first model usually has. Time is *discrete* and modelled
as ordinary state; the recurring trick is a **time-progress event whose guard
forbids stepping past a pending deadline**, which both keeps a deadline invariant
and forces the obligated event to fire before time may advance.

### Monotonic clock with a deadline-respecting tick

Carry `now ∈ ℕ` and advance it with one `tick` event. Capture deadlines as
absolute times; guard `tick` so it cannot jump over an open deadline.

```eventb
VARIABLES now due
INVARIANTS
    @t1 now ∈ ℕ
    @t2 due ∈ ℕ
    @t3 now ≤ due                       // time may never overrun a pending deadline
EVENTS
    EVENT arm  THEN @a1 due ≔ now + PERIOD END
    EVENT fire WHERE @g1 now = due THEN @a1 due ≔ now + PERIOD END
    EVENT tick                          // the one time-progress event
        ANY delta
        WHERE @g1 delta ∈ ℕ1
              @g2 now + delta ≤ due      // forbid jumping over the deadline
        THEN  @a1 now ≔ now + delta END
END
```

The deadline form `pending = TRUE ⇒ now − start ≤ D` with the matching `tick` guard
`pending = TRUE ⇒ now + 1 − start ≤ D` is the same idiom written as a relative bound.

### Countdown / watchdog timers

The dual of the monotonic clock: each obligation is a counter in `−1 ‥ MAX` (with
`−1` ≙ disarmed). One `tick` decrements every timer (`max({t − 1, −1})`); a
companion `tick_timeout` event fires in exactly the states `tick`'s guard excludes
and raises an anomaly. Good for "stimulus must get a response within N steps."

```eventb
EVENT tick                              // normal step: response still possible
    WHERE @g1 ¬(timer = 1 ∧ pending = TRUE)
    THEN  @a1 timer ≔ max({timer − 1, −1}) END
EVENT tick_timeout                      // companion: the deadline was missed
    WHERE @g1 timer = 1 ∧ pending = TRUE
    THEN  @a1 timer ≔ max({timer − 1, −1})
          @a2 anomaly ≔ TRUE END
```

### State as a function of time (history variable)

To reason about *rates of change* or *sensor latency*, model a varying physical
quantity not as a scalar but as a total function over past time
`level ∈ 0 ‥ clk → ℤ`. Invariants can then quantify over time points (bounding how
fast it moves), and a controller can act on a *delayed* sample `level(clk − a)`.

```eventb
INVARIANTS
    @h1 level ∈ 0 ‥ clk → ℤ                                  // value latched at every past instant
    @h2 ∀i,j· i ∈ 0‥clk ∧ j ∈ 0‥clk ∧ i ≤ j ⇒ level(j) ≥ level(i) − D∗(j − i)
// a control event may then read level(clk − a) with 0 ≤ a ≤ A (a bounded sample age)
```

### Audit time progress as a scheduling policy

Dense real-time models can accumulate a giant disjunction in `tick`: one clause for
every phase in which time may advance. That shape was observed in a published CRT
pacemaker model, but it is difficult to review and extend.

Prefer one of these equivalent decompositions when the requirements permit it:

- an explicit phase/mode variable with one time-window rule per phase;
- a finite map of pending obligations to absolute deadlines, with `tick` bounded by
  the earliest pending deadline;
- separate time-progress events whose guards form a documented, exhaustive
  partition.

Whichever shape you choose, keep the scheduling rule visible: time must not step
over an enabled deadline transition. Add a boundary scenario for every lower and
upper timing limit.

Evidence: [Formalizing the Cardiac Pacemaker Resynchronization Therapy](https://experts.mcmaster.ca/scholarly-works/1092491).

## Modes and state machines

[patterns.md §5](patterns.md) covers a single mode variable. Real models add structure.

### Modes as an ordered integer interval

When modes have a natural ordering ("more vs. less operational"), encode them as an
interval `0 ‥ Top` plus a sentinel `None = Top + 1`. Safety properties become
arithmetic (`cur < target`), the next mode up is just `cur + 1`, and direction of
travel (escalate vs. degrade) is `<` vs. `≤` — no successor constant needed.

```eventb
CONTEXT modes_ctx
CONSTANTS Off Top None
AXIOMS
    @a1 Off = 0
    @a2 Top ∈ ℕ1
    @a3 None = Top + 1                          // "no target above the top mode"
END
```

### Transition / decision table in a context

Put the *allowed* moves (or the recovery policy) in a context as a constant relation
`trans ∈ STATE ↔ STATE` (or a function for a deterministic table), then write **one**
generic event whose guard tests an `ANY` parameter against the table
(`st ↦ nx ∈ trans`, as in the machine line below — never a primed `st'`, which is
illegal in a guard). Changing behaviour means editing the table, not the events.

```eventb
CONTEXT fsm_ctx
SETS STATE ERR
CONSTANTS trans recover
AXIOMS
    @a1 trans   ∈ STATE ↔ STATE                 // legal moves, enumerated as pairs
    @a2 recover ∈ STATE × ERR → STATE           // deterministic fault policy
    @a3 ∀s,e· s ↦ e ∈ dom(recover) ⇒ recover(s ↦ e) ≠ s
END
// machine:  EVENT move ANY nx WHERE @g st ↦ nx ∈ trans THEN @a st ≔ nx END
```

### Mode → required-configuration table (controller fan-out)

The canonical fan-out from one internal mode to many actuators: a two-level constant
table `RequiredConfig ∈ MODE → (UNIT → CONFIG)`, a monotonicity axiom tying mode
order to per-unit config order, and a "when settled, units match the mode" invariant.

```eventb
@a1 RequiredConfig ∈ MODE → (UNIT → CONFIG)
@a2 ∀m1,m2,u· m1 ≤ m2 ⇒ RequiredConfig(m1)(u) ≤ RequiredConfig(m2)(u)
// invariant:  settled = TRUE ⇒ config = RequiredConfig(mode)
// event:      drive ANY u WHERE config(u) ≠ RequiredConfig(target)(u)
//                          THEN config ≔ config <+ {u ↦ RequiredConfig(target)(u)}
```

### Stage recovery, then commit once

For fault recovery across many units, keep the externally visible request unchanged
while a finite work set is analysed. Accumulate the proposed mode and
reconfiguration set in temporary variables; publish them together only when the work
set is empty.

```eventb
INVARIANTS
    @r1 phase ∈ {idle, analysing}
    @r2 remaining ⊆ UNIT
    @r3 proposed_mode ∈ MODE
    @r4 proposed_reconf ⊆ UNIT
    @r5 phase = idle ⇒ remaining = ∅
VARIANT remaining
convergent EVENT analyse_unit
    ANY u
    WHERE @g1 phase = analysing  @g2 u ∈ remaining
    THEN  @a1 remaining ≔ remaining ∖ {u}
          @a2 proposed_mode ≔ recover(proposed_mode ↦ fault(u)) END
EVENT commit_recovery
    WHERE @g1 phase = analysing  @g2 remaining = ∅
    THEN  @a1 requested_mode ≔ proposed_mode
          @a2 requested_reconf ≔ proposed_reconf
          @a3 phase ≔ idle END
```

The full protocol also needs an idle/active phase, initialization of the temporary
state, and explicit semantics for faults that arrive during analysis. This
prepare/commit shape prevents other events from observing a half-computed recovery
decision.

Evidence: [Developing mode-rich satellite software by refinement in Event-B](https://eprints.ncl.ac.uk/190370).

### Per-entity lifecycle (two encodings)

"Each of N entities runs its own open→…→close state machine." Two interchangeable
forms: (a) a **status function** `entity → STATUS` over an enumerated set, advanced by
functional override; (b) a **family of disjoint phase-sets** with a `partition`
invariant, where an event moves one element from one set to the next.

```eventb
// (a) status function
EVENT open  ANY p WHERE @g status(p) = IDLE THEN @a status ≔ status <+ {p ↦ OPEN} END
// (b) disjoint phase-sets
INVARIANTS @part partition(known, pending, open, closing)
EVENT establish ANY p WHERE @g p ∈ pending
    THEN @a1 pending ≔ pending ∖ {p}  @a2 open ≔ open ∪ {p} END
```

---

## Sensors and actuators

Extends the controller/environment split in [patterns.md §1](patterns.md).

### Sensor freshness flag (sample-then-use-once)

Pair every sampled input with a `fresh ∈ BOOL` flag. A sensing event writes the value
and sets `fresh ≔ TRUE`; every event that *uses* the value is guarded by `fresh = TRUE`
and resets it to `FALSE` — forcing a new sample before the next use ("act only on
up-to-date data").

```eventb
EVENT sample ANY v WHERE @g1 v ∈ ℕ THEN @a1 reading ≔ v  @a2 fresh ≔ TRUE END
EVENT act WHERE @g1 fresh = TRUE THEN @a1 actuator ≔ decide(reading)  @a2 fresh ≔ FALSE END
```

### Sensor redundancy and agreement voting

Replicate a measurement over `1 ‥ N` sensors, keep a `valid ⊆ 1 ‥ N` set, prune any
sensor that no longer agrees with a still-valid peer, and raise an anomaly when the
quorum is lost. Models fail-safe behaviour for safety-critical sensing.

```eventb
EVENT recheck                                  // keep a sensor only if a peer confirms it
    THEN @a1 valid ≔ {s∣s ∈ valid ∧ (∃p·p ∈ valid ∧ p ≠ s ∧ reading(p) = reading(s))} END
EVENT raise_anomaly WHERE @g1 valid = ∅ THEN @a1 anomaly ≔ TRUE END
```

### Physical truth, reported state, and commanded state

Do not use one variable for what the environment is doing, what the controller last
heard, and what the controller requested. Introduce them in that order:

1. physical state, changed by environment events;
2. reported/observed state, changed by sensing or communication events;
3. target/command state, changed by controller events.

Relate observation to truth with an invariant that admits the specified delay or
uncertainty. Scope degraded operation explicitly rather than weakening the nominal
rule globally:

```eventb
@safe degraded(t) = FALSE ⇒ actual_blocks[{t}] ⊆ authority[{t}]
@lag  reported_front(t) ≤ actual_front(t)                  // report may lag, never lead
```

Give `degraded` controlled entry and recovery events and state who may raise it.
This three-view split is central when stale reports are a hazard, as in Hybrid
ERTMS Level 3.

Evidence: [An Event-B Model of the Hybrid ERTMS/ETCS Level 3 Standard](https://abz-conf.org/publication/mammarffl18/).

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

## Access control and security

### POSIX mode bits: select one class, never union classes

For basic POSIX discretionary access, represent mode bits as
`mode ∈ (FILE × CLASS) → ℙ(RIGHT)`, with owner/group/other classes. The
authorization decision is ordered and mutually exclusive: use owner bits when
`u = owner(f)`; otherwise use group bits when the user belongs to the file's group;
otherwise use other bits. In particular, an owner does **not** fall through to
group or other bits when an owner bit is absent. Split grant/deny events by class
when you want model-checking coverage to show that all three decisions are
reachable. Model root/capability bypass, ACLs, directory rules, and open-descriptor
persistence as separate requirements rather than silently folding them into this
core rule.

### Policy as a relation + authorization invariant

Model the static security policy as a relation/function in a context, and state the
core safety property as one **subset invariant**: the set of currently-held accesses
is contained in what the policy permits. RBAC adds a `role_of` function composed in;
MAC adds a `label_of` function and decides access by relational image of a rules
relation.

```eventb
CONTEXT access_policy
SETS SUBJECT OBJECT ACCESS ROLE
CONSTANTS role_of may
AXIOMS
    @rbac role_of ∈ SUBJECT → ROLE                       // each subject has a role
    @pol  may     ∈ ROLE ↔ (OBJECT × ACCESS)             // policy as a relation
END
// machine:
//   @auth ∀s,o,a· s ↦ (o ↦ a) ∈ held ⇒ role_of(s) ↦ (o ↦ a) ∈ may   // every grant is permitted
//   EVENT grant ANY s o a WHERE @g role_of(s) ↦ (o ↦ a) ∈ may  …
```

### Layer independent policy mechanisms

Large OS security models become difficult to maintain when RBAC, integrity,
confidentiality, hierarchy, and information-flow constraints are introduced in one
machine. Give each mechanism a planned refinement/module and one named invariant
family:

1. principals, resources, active accesses, and the core authorization subset;
2. role membership, role hierarchy, and administrative rights;
3. integrity labels and rules;
4. confidentiality/information-flow rules;
5. implementation-facing representations only after the policy is stable.

Define derived helpers such as `ancestors`, `descendants`, effective rights, and
authorization once, then reuse them in guards and invariants. Prove their types,
domains, and defining properties strongly enough that every application is
well-defined. Keep a policy-to-event matrix: each row is a policy invariant, and
each column is a create/delete/grant/revoke event that can affect it.

This recommendation is supported by the MROSL DP experience: its authors report
that a monolithic model was quick to begin but hard to explore and maintain, while
planned refinement improved readability and automatic proof at the cost of more
up-front domain analysis.

Evidence: [Using Refinement in Formal Development of OS Security Model](https://www.ispras.ru/en/publications/2015/using_refinement_in_formal_development_of_os_security_model/).

### Exclusive reservation / locking

Allocate shared resources atomically with two nested layers — a `reserved` set and an
`in_use ⊆ reserved` set — and reserve only when the request's footprint is disjoint
from everything already reserved. Yields "no two trains on one block" / mutual
exclusion without an explicit lock variable.

```eventb
INVARIANTS @t2 in_use ⊆ reserved                       // can only use what you reserved
EVENT reserve ANY r WHERE @g footprint[{r}] ∩ reserved = ∅   // exclusivity check
    THEN @a reserved ≔ reserved ∪ footprint[{r}] END
```

> The same **acyclic-topology** idiom (no successor-closed subset) is the reusable
> well-formedness axiom for physical layouts — track blocks, routes, location graphs.
> See the network/topology context above.

---

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
