---
name: cutover-migration
description: Playbook for migrating a core component or data model out of a legacy codebase in place, without a big-bang rewrite. Combines Branch by Abstraction (in-process seam) with Strangler Fig (slice-by-slice displacement) and golden-master verification. Use when a subsystem is too large or too risky to rewrite in one pass, when AI-assisted rewrites keep re-surfacing the same class of bugs, or when planning any incremental cutover of a core model/engine.
---

# Cutover Migration Skill

## When to use this

- A component (data model, persistence layer, execution engine) has accumulated enough
  untested, tangled behavior that a full rewrite would mean re-deriving correctness from
  scratch, with no way to prove parity.
- The component can't be swapped at a network boundary (it's a library, an ORM, a model,
  an in-process engine) — there's no facade/router to put in front of it.
- Repeated review passes (human or AI) keep surfacing new issues rather than converging,
  which usually means there's no stable ground truth for current behavior, not that the
  code is inexhaustibly bad.

## Core methods, and how they compose

**Branch by Abstraction** (Fowler) is the mechanism: introduce an interface between callers
and the current implementation, wrap the existing code behind it with zero behavior change,
then build a new implementation behind the *same* interface so both can coexist in one
running process, switched by configuration rather than a long-lived branch.

**Strangler Fig** (Fowler) is the sequencing: don't flip the whole component at once — move
one slice (a feature, a step type, a call-site cluster) over at a time, verify it, then move
the next, until the legacy implementation has no callers left and can be deleted.

Use Branch by Abstraction to decide *how* old and new coexist; use Strangler Fig to decide
*in what order* pieces move. They are not alternatives — for an in-process component, you
almost always want both at once: the abstraction interface is the seam, and the slice order
is the strangler plan for retiring what's behind it.

Reach for Strangler Fig *alone* (facade/router, no in-process interface) only when the
boundary really is interceptable — a service, an API, a request path. Reach for Branch by
Abstraction alone (no slicing) only for something small enough to flip in one shot; for
anything large enough to need this skill, slice it.

## Workflow

1. **Seam inventory.** Find every call site that reads or writes the component's state
   today — file, function, what it does. This is the exact surface the interface has to
   cover. Don't design the interface before this step; let the inventory drive its shape.

2. **Golden-master / characterization tests** (Feathers). Before writing any new code,
   capture current behavior — run real or replayed inputs through the existing path, save
   the outputs as an approved baseline. This is what lets later steps be verified rather
   than asserted. If the legacy behavior is undocumented or inconsistent, this step *is*
   the documentation.

3. **Define the abstraction interface.** A small `Protocol`/interface with only the methods
   the seam inventory actually requires. This is a concrete artifact — a handful of method
   signatures — not a design philosophy. Get this wrong and everything downstream inherits
   the mistake, so keep it minimal and revisit it once, hard, before step 4.

4. **Wrap the legacy implementation behind the interface. No behavior change.** Route every
   call site from step 1 through the interface instead of touching the old code directly.
   This is valuable on its own before any new code exists: it proves the interface is
   complete, and any gap shows up immediately with no new-implementation risk mixed in.

5. **Build the new implementation behind the same interface.** Model its internal state so
   invalid states are unrepresentable (discriminated unions over a bare status string with
   optional fields) rather than re-encoding the old implicit rules as new code. Verify
   against the golden masters from step 2 — a parallel run, comparing old vs. new output on
   the same inputs, before trusting the new path with anything real.

6. **Migrate slice by slice.** Flip one unit (whatever slice you chose in the pattern
   above) over to the new implementation at a time, via the switch in step 3. Each slice
   gets its own verification against the golden masters before the next one moves.

7. **Decommission legacy per slice.** Once a slice's old code path has zero callers, delete
   it. Don't leave it running "just in case" — that's how migrations stall with two
   permanent systems instead of finishing.

8. **Exit criteria, stated as checkable facts, not vibes.** E.g.: "N call sites routed
   through the interface, zero direct access to the old store outside it, parallel run
   shows zero diffs over M sampled cases for two weeks." Write these before starting a
   phase, not after.

## Design principles for the new implementation

- **Parse, don't validate.** Convert untrusted/legacy-shaped input into the new typed
  model once, at the interface boundary — don't scatter validation across call sites.
- **Make illegal states unrepresentable.** Model lifecycle/status as a discriminated union
  with only the fields valid for that state, not a string plus a pile of optional fields.
- **Decouple the model change from the schema change.** The interface can parse/validate
  the new model out of the *existing* storage first. Don't require a schema migration and
  a domain-model migration to land in the same step — that's how a bounded migration turns
  into the big-bang rewrite this skill exists to avoid. Schema migration (expand → dual-write
  → backfill → cutover → contract) is a separate, later concern.
- **Decide explicitly how in-flight state is handled** at the moment of cutover (only new
  work uses the new path; existing work drains under the old path) rather than assuming
  the new model can retroactively make sense of state it didn't create.

## Pitfalls checklist

- Interface designed from imagination instead of the seam inventory — missing a method
  discovered mid-migration, forcing rework of already-migrated slices.
- Skipping golden-master capture because "we know what it does" — this is exactly the
  untested-code trap; if reviewers keep finding new issues, there's no ground truth yet.
- Coupling schema migration to model migration in the same change.
- Never revisiting slice size — a slice too big to verify confidently is a sign to split it
  further, not push through faster.
- Leaving the old implementation in place after a slice reaches zero callers "for safety."
- Treating "abstraction" as a design exercise instead of what it is here: a fixed, small
  set of method signatures written down once from the seam inventory.

## Spec-doc prompt (adapt per migration)

```
You are producing a migration spec for extracting [component] out of [codebase] using
Branch by Abstraction (in-process seam, since this isn't interceptable at a network
boundary) and Strangler Fig (slice-by-slice displacement, sliced by [chosen axis: feature /
step type / entity / call-site cluster]).

First, inventory in the repo: every call site touching [component]'s state, the current
persistence/storage mechanism, and how in-flight state is handled today. Don't guess —
report what's actually there.

Then produce a spec with: problem statement grounded in the inventory; the abstraction
interface (methods only, derived from the inventory); migration phases (golden-master
capture, wrap legacy behind the interface with no behavior change, build new implementation
behind the same interface verified via parallel run, slice-by-slice cutover, decommission);
in-flight-state handling; explicit confirmation that schema migration is out of scope for
this spec; risks and per-phase rollback; and exit criteria per phase stated as checkable
facts.

Ask clarifying questions about anything the repo doesn't make clear before finalizing.
```

## Sources

- Fowler, "Strangler Fig Application" — https://martinfowler.com/bliki/StranglerFigApplication.html
- Fowler, "Branch By Abstraction" — https://martinfowler.com/bliki/BranchByAbstraction.html
- Sam Newman, "Branch By Abstraction" — https://samnewman.io/patterns/architectural/branch-by-abstraction/
- Shopify Engineering, "Refactoring Legacy Code with the Strangler Fig Pattern" — https://shopify.engineering/refactoring-legacy-code-strangler-fig-pattern
- Solita, "Decoupling a Legacy Spring Boot Monolith with Branch by Abstraction" — https://dev.solita.fi/2026/01/08/decoupling-legacy-monolith.html
- Feathers, *Working Effectively with Legacy Code* — seams, characterization/golden-master testing
- Minsky / King, "make illegal states unrepresentable" / "parse, don't validate"
