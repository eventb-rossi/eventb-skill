# Design patterns

Reusable modelling idioms for reactive systems: a mechanical press, a file-transfer
protocol, a bridge controller. Each is a *shape* — variables, events, guards,
invariants — you instantiate by renaming. Pick the pattern that matches the
requirement, then refine it into your model.

These are the *core* reactive-system patterns. For idioms specific to a domain, see the
field guides: [patterns-control.md](patterns-control.md) (real-time/timing, modes &
state machines, sensors & actuators), [patterns-distributed.md](patterns-distributed.md)
(distributed protocols, channels, long-running operations),
[patterns-security.md](patterns-security.md) (access control and policy), and
[patterns-algorithms.md](patterns-algorithms.md) (algorithm development by refinement,
interpreters).

## 1. Controller vs environment split (reactive systems)

**Problem.** Software (a *controller*) drives and reacts to physical equipment (the
*environment*) through actuators and sensors, with a time lag — it can't observe or
act on the world instantaneously.

**Structure.**
- Build a **closed model**: model controller *and* environment together so your
  assumptions about the world are explicit (the controller is correct only while
  the environment honours them).
- For each physical quantity keep **two variables** — a `*_sensor` (world →
  controller) and a `*_actuator` (controller → world) — because the physical state
  changes before the controller learns of it, and vice-versa.
- Partition events into **environment events** (e.g. `motor_start`,
  `push_button`) and **controller events** (name them with a `treat_` prefix, e.g.
  `treat_start_motor`) so the split is visible at a glance. Controller events read
  sensors / set actuators; environment events read actuators / set sensors.

**When.** Any embedded/reactive system mediating between input devices (buttons) and
output devices (motor, door, lights). Start with no equipment at all and introduce
one sensor/actuator connection per refinement.

## 2. Action–reaction without retro-action (weak synchronization)

**Problem.** A stimulus `a` is followed by a reaction `r` that need only *follow*;
`a` may change many times while `r` lags, and brief pulses may be missed.

**Structure.** State `a, r ∈ {0,1}` (or `BOOL`). The **action events are
unconstrained by `r`** — `a` is free to go on/off testing only `a`. The **reaction
events are guarded by the action**: `r_on` needs `r = 0 ∧ a = 1`; `r_off` needs
`r = 1 ∧ a = 0`. The constraint "reaction never overtakes action" holds.

**When.** Loosely-coupled "notice the stimulus" relationships where losing events is
acceptable (e.g. button → controller: a quick tap may be missed). Requirement form:
"X and Y are *weakly* synchronized."

## 3. Action–reaction with retro-action (strong synchronization)

**Problem.** As above but lossless: the action may not run ahead more than one step,
so no pulse is lost — the reaction *retro-acts* on the action.

**Structure.** Same variables; **add a retro-acting guard on `r` to the action
events**: `a_on` needs `a = 0 ∧ r = 0` (can't restart until the reaction reset);
`a_off` needs `a = 1 ∧ r = 1` (can't end until the reaction acknowledged). Reaction
events unchanged from pattern 2.

**When.** Tight, lossless coupling (controller ↔ equipment: every command must be
confirmed before the next). Requirement form: "X and Y are *strongly* synchronized."
Note an event can be an *action* at one layer and the *reaction* at the next — roles
flip under refinement.

## 4. One-way dependency between two subsystems

**Problem.** Subordinate one synchronized pair to another: "B only while A" (e.g.
*clutch engaged only while the motor runs*), and you **may not modify the reacting
events** (the physical equipment's behaviour is fixed).

**Structure.** Express the constraint as an **implication invariant**
(`s = 1 ⇒ r = 1`, or `clutch = engaged ⇒ motor = running`) and discharge it by
**strengthening the guards of the *action* events** that could break it — never the
fixed reaction events. The readable form is often a single invariant like
`b = 1 ∨ s = 1 ⇒ a = 1 ∧ r = 1` ("second pair active ⇒ first pair fully active").

**When.** A directional "B requires A" constraint where the reacting hardware is
untouchable. Key idiom: **constrain reactions by acting on the actions that enable
them**, captured as invariants.

## 5. Mode / phase variable

**Problem.** A "whose turn is it" / "exactly once" constraint that scattered
booleans can't pin down (e.g. strict alternation between two subsystems).

**Structure.** Introduce one explicit `mode`/`phase` variable (`m ∈ {0,1}`, or an
enumerated set) that records the current phase. One event *claims* the turn
(`m ≔ 1`), another is guarded by `m = 1` and *consumes* it (`m ≔ 0`). The mode
variable forces alternation the booleans alone can't express.

**When.** Mutual interlocks, "once per cycle" semantics, or any time you find
yourself reconstructing a phase from several booleans — prefer one explicit variable.

**Variants.** When the modes have a natural order ("more vs. less operational"),
encode them as an integer interval `0 ‥ Top` so safety becomes arithmetic; when the
*allowed transitions* are the interesting part, declare them as a constant relation
`trans ∈ MODE ↔ MODE` in a context and let one generic event test an `ANY` parameter
against it (`mode ↦ nx ∈ trans`). Both are in
[patterns-control.md](patterns-control.md) (Modes and state machines), along
with per-entity lifecycles (a `status` function or a family of disjoint phase-sets).

## 6. "False"/no-op companion event

**Problem.** A refinement adds bookkeeping (e.g. record a button impulse) to an event
whose original guard may be false — so the bookkeeping would be silently lost when
the guard doesn't hold.

**Structure.** Split into two events: the "true" event fires when the full guard
holds and does both effects; a companion `*_false` event fires when the
bookkeeping-side guard holds but the equipment-side guard is *negated*, and performs
only the bookkeeping half.

**When.** Whenever a superposed side-effect must be total over all environment
occurrences, not just the ones where the main action fires.

## 7. Protocol / message-passing (channels, in-transit data, acks)

**Problem.** Model a distributed protocol (sender ↔ receiver over a network) — e.g.
copy a file. Writing the distributed program directly is too error-prone.

**Structure — refine in this characteristic order:**
1. **Initial model = the goal, observed, not the mechanism.** Put both parties on
   one site; a single abstract event captures *what the protocol achieves* (the
   final result), not how. This is the most general spec of the whole *class* of
   such protocols.
2. **Refine gradually, letting parties "cheat."** Transfer piece-by-piece with a new
   event (e.g. `receive` with an index); the receiver may still read the sender's
   memory directly. Mark the worker event **convergent** with a variant so it can't
   run forever and the final result stays reachable.
3. **Stop cheating — introduce real channels.** Model each **channel as a state
   variable** carrying the in-transit item plus a counter, with a gluing invariant
   relating channel contents to the sender's true state (a message is a *delayed,
   possibly-stale copy*). An **acknowledgement** is the receiver sending a counter
   back so the sender can compare and advance.
4. **Optimise, protocol unchanged.** A final behaviour-preserving refinement (e.g.
   transmit only parities of the counters) separates correctness from efficiency.

**Key idioms.** channel/message as a state variable + gluing invariant; ack =
returning state to compare; convergent worker event + variant so the observable
result stays reachable; consider an **`anticipated`** worker event in the initial
model to avoid inventing artificial gluing variables just so a new event can refine
`skip`.

**Unreliable channels.** For loss and recovery — a silent `drop` daemon and a
bounded-retransmission counter — see
[patterns-distributed.md](patterns-distributed.md) (Communication channels).

## Minor reusable idioms

- **One-way constraint as an implication invariant:** "B only when A" → `B ⇒ A`,
  discharged by guard-strengthening. (The bridge's `a = 0 ∨ c = 0`.)
- **Ghost counters to *specify*, not implement:** auxiliary counters make a timing
  constraint precise; forbid them in guards and strip them from the final model.
- **Enumerated mode set** over booleans when there are more than two phases.
- **Contrapose a safety property** to spot that it's implied by others (and delete a
  redundant refinement).
