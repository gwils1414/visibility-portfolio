---
name: strategic-design
description: Spend the extra 20% on design before writing code — settle the philosophy by grilling, then put three real architectures side by side and compare their impacts before picking one, then hand the winner to a spec doc. Use when starting a feature, module, pipeline or service that doesn't have an obvious shape; when asked "how should we structure this", "what's the best layout", "which approach"; when a design problem surfaces mid-task and the fast move would be to patch around it; or when a change is about to establish a pattern other code will copy. Do not use for a one-line fix or a bug with a named cause.
---

# Strategic design

## Tactical vs Strategic Programming

- Tactical programming:
	- the main focus is to get something working quickly. It is hard to produce good system design this way.
	- You aren't planning for the future, it is short sighted. The cost of additional complexity seems to be outweighed by hitting a deadline quickly.
	- This is how systems become more complex, as complexity grows incrementally. The accumulation of dozens or hundreds of small tactical decisions.
	- Using patches over refactoring , since refactoring takes time, is a tactical decision, instead of building the system correctly.
	- As these tactical decisions add up issues start to arise.
	- Tactical programming creates technical debt, by borrowing time from the future to produce fixes faster today. The debt has to be paid back in the future.
- Strategic Programming
	- Realize that working code is not enough.
	- A codebase will perpetually grow and expand as features are added and the software evolves. Changes should be easy and bug free.
	- This requires an investment mindset, rather than approaching the fastest path, invest the time to improve the design f the system.
	- This slows is down in the short run but speeds us up in the long run.
	- When you discover a design problem , don't just patch around it. Take the time to think through a strategic design. Try a few alternative designs to find the cleanest one.

How much to invest?
- Make a lot of small investments continually
- Spend 20% extra time on a problem to develop a good design.
- It will slow productivity down by 20% in the short run, but make up for it in the long run. Working with a complex, degraded, poorly managed code base adds atleast 20% on the backend.

That 20% is not optional and it is not "if we have room." You either pay it
deliberately now or involuntarily later, with interest.

For what complexity actually is, how to quantify it, and the symptoms to watch
for, see the `complexity` skill. This skill is the practice; that one is the
theory it rests on.

## The workflow

Three skills in sequence, each with one job: `grill-me` gets us on the same
**page**, this skill gets us on the same **design**, and `superpowers:writing-plans`
turns that design into the **spec**.

### 1. Settle the philosophy first — gate on `grill-me`

Do not propose architectures against an unsettled problem. You will produce
three variations of one guess.

If the shape of the problem, the constraints, or what "good" means here are not
already agreed, **run the `grill-me` skill and stop**. Come back when the design
tree's frontier is empty and the user has confirmed shared understanding.

If they are already settled — the user has just finished a grilling, or the
constraints are explicit in the request — say so in one line and go to step 2.

### 2. Fan out: three candidates, three different constraints

Three. Two is a false binary and invites a coin flip; five is padding and the
last two will be variations of the first three.

Dispatch **one sub-agent per candidate**, in a single message so they run
concurrently. This is the step that makes the comparison real: a single pass
writes three variants of its own first idea, because the first idea anchors
everything after it. Independent agents handed *different optimizing
constraints* come back with genuinely different architectures.

Give each agent a different constraint to optimize for. Pick three that actually
pull against each other for this problem. Useful defaults:

- **Fewest moving parts.** Smallest number of files, functions and indirections
  that solves it. Reuse stdlib and existing deps before anything new.
- **Lowest cost of the likely next change.** Name the change you expect next and
  design so it touches one place.
- **Conforms to what's already here.** The shape the existing code already uses,
  even where you'd do it differently. The baseline the other two must beat.

A fourth is worth adding when the problem has a real axis the three above miss —
swappability of a vendor, testability without a live dependency, throughput.
Name the axis rather than adding a generic option.

Each agent returns:

- The layout: files, modules, what owns what, where the seams are.
- The one thing this design makes easy that the others don't.
- The one thing it makes hard, stated plainly. An agent reporting no downside
  has not found it yet — send it back.
- What a developer has to hold in their head to work on it (cognitive load).
- How many places a change to the core behavior would touch (change
  amplification).

### 3. Write the comparison to a file, then ask

The comparison does not go in chat. It is too long to read in a scrollback and
the user has to be able to sit with it, so write it to
`docs/design/<slug>-options.md` and give them the path. Chat gets one line: what
the three are, in three noun phrases, and the path.

**Normalise the shape before you write.** Sub-agents will come back in three
different formats at three different lengths, and the longest one will read as
the most considered when it is only the most verbose. Rewrite all three into the
same sections, the same order, the same length — differences in the *design*
should be the only differences on the page.

The file:

````markdown
# <What is being designed> — design options

**Decided during grilling:** <the constraints that are fixed, 3-5 bullets.
This is what every candidate below has to satisfy, so a candidate that
violates one is disqualified, not an option.>

## At a glance

| | A: <name> | B: <name> | C: <name> |
|---|---|---|---|
| **In one line** | | | |
| **New files / modules** | | | |
| **Cognitive load** | <what someone has to hold in their head> | | |
| **Change amplification** | <places a core change touches> | | |
| **Makes easy** | | | |
| **Makes hard** | | | |
| **If its assumption is wrong** | | | |
| **Cost to back out later** | | | |

## A: <name>

**Optimizes for:** <the constraint this agent was given>

<Three or four sentences on how it works. Not a feature list — the mechanism.>

```
<directory/file layout, or the key signature or schema — whatever makes
the shape concrete. Same kind of sketch for all three.>
```

**The one thing it makes easy:** <...>

**The one thing it makes hard:** <...>

## B: <name>
<same sections, same order, same length>

## C: <name>
<same sections, same order, same length>

## My read

<Two or three sentences. Which one, and the single fact that decides it —
not a summary of the table above. Say plainly if two are close enough that
the choice is taste.>
````

Rules for that file:

- **The table is for scanning, the sections are for reading.** No cell longer
  than a short phrase; if it needs a sentence, it belongs in the section.
- **Every row filled for every candidate.** A blank cell reads as "no downside"
  and the comparison stops being one. "Same as A" is a legitimate entry and
  worth saying out loud.
- **Keep the three the same length.** If one candidate's section runs twice as
  long, cut it rather than padding the others.
- **Concrete over abstract.** Real file paths, real function names, real column
  names from this codebase. "A service layer" is not a design.
- **Where two candidates differ only cosmetically, say so and collapse them**
  rather than padding back out to three.

### 3a. Put the choice through AskUserQuestion

After the file is written, ask with the **AskUserQuestion** tool — one
single-select question, one option per candidate, your recommendation first with
`(Recommended)` appended.

- `preview` carries that candidate's layout sketch, so the shapes sit side by
  side while the user decides. This is exactly what previews are for.
- `description` is the tradeoff in one clause — the thing that would make
  someone pick it — never a restatement of the label.
- Never `multiSelect`. One design gets built.

Recommend; do not decide. A recommendation presented as a conclusion wastes the
other two agents' work.

### 4. Route the chosen design into a spec

Once the user has picked, **hand off to the `superpowers:writing-plans` skill.**
Do not start writing code off the back of the comparison — the comparison is a
design decision, not an implementation plan, and skipping the spec is itself the
tactical move this skill exists to prevent.

What writing-plans gets as its input is the chosen architecture from step 2 —
its file structure, its seams, its named downside — plus the constraints settled
during grilling. It assumes an engineer with zero context, so the spec has to
carry the *why* behind the layout, not just the layout.

The options file from step 3 stays where it is — it is the record of why the
other two lost, which is the valuable half. It stops the same three designs
being re-derived in six months and tells the next reader whether the constraint
that drove the choice still holds. Link it from the spec, and from the feature
log if the repo keeps one (`feature-log` skill).

Execution is a separate decision after the spec exists —
`superpowers:subagent-driven-development` for a fresh agent per task, or
`superpowers:executing-plans` to implement it inline.

## When this is the wrong skill

Skip it for a one-line fix, a bug with a named cause, or a change that follows a
pattern already used at every call site — `essential-changes-only` covers those,
and running a three-agent fan-out on them is its own kind of waste.

The test: would this decision constrain code that doesn't exist yet? If no, just
make the change.
