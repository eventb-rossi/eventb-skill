# Access control and security patterns

Field-guide idioms for authorization models: discretionary mode bits, policy as a
relation with a subset invariant, layering independent policy mechanisms across a
refinement chain, and exclusive reservation. Extends the core reactive-system patterns
in [patterns.md](patterns.md) with shapes observed across substantial,
publication-backed developments.

Snippets are **illustrative fragments** (a context, an event, a few invariants) in the
skill's surface syntax — not standalone-checkable files. Operator spellings follow
[math-toolkit.md](math-toolkit.md) (note: relational override is `<+`).

## POSIX mode bits: select one class, never union classes

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

## Policy as a relation + authorization invariant

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

## Layer independent policy mechanisms

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

## Exclusive reservation / locking

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
> See "Network/topology as a relation in a context" in
> [patterns-distributed.md](patterns-distributed.md).
