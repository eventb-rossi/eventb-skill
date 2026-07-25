# Control-system patterns: timing, modes, sensors

Field-guide idioms for controllers and other reactive systems: discrete time and
deadlines, mode and state-machine structure, and the sensing/actuation boundary.
Extends the core reactive-system patterns in [patterns.md](patterns.md) with shapes
observed across substantial, publication-backed developments.

Snippets are **illustrative fragments** (a context, an event, a few invariants) in the
skill's surface syntax — not standalone-checkable files. Operator spellings follow
[math-toolkit.md](math-toolkit.md) (note: relational override is `<+`).

## Contents

- [Real-time and timing](#real-time-and-timing) — monotonic clock with a deadline-respecting tick, countdown/watchdog timers, state as a function of time, auditing time progress
- [Modes and state machines](#modes-and-state-machines) — ordered mode intervals, transition tables, mode → configuration fan-out, stage-then-commit recovery, per-entity lifecycles
- [Sensors and actuators](#sensors-and-actuators) — freshness flags, redundancy voting, the physical/reported/commanded split

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
