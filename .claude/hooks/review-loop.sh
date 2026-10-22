#!/usr/bin/env bash
# Stop-hook review loop: review this branch's own commits once, as they land.
# "Reviewable" = commits on HEAD not yet on the BASE branch — so merged, pulled and
# rebased-in work is never reviewed, only what this branch adds. Converges by sha;
# MAX_ROUNDS bounds a review->fix->review cycle: it blocks at most that many rounds in
# a row, then hands control back. At the default of 1 that means one review per burst —
# you commit, you get a review, and the NEXT tip to appear is not reviewed, because
# normally that tip is the commit applying the review's own findings. The hook cannot
# tell that commit apart from fresh work, so if a review finds nothing and commits
# nothing, the next real commit is the one that gets skipped: it is named in the
# allowing-stop message so it can be reviewed by hand. It does NOT stop asking for good:
# the budget clears on the way out, so the work after that gets its own review. Going
# permanently silent on a live branch is the failure this hook exists to prevent.
#
# Raise it (`REVIEW_LOOP_MAX_ROUNDS=3`) to keep reviewing the fixes themselves. Worth
# doing on security-shaped changes — three rounds on #1574 each found a real defect in
# the previous round's fix — but not the default, because on ordinary work it spends a
# whole review per round polishing prose.
#
# It used to gate on `--not --remotes=origin`, i.e. UNPUSHED commits, which made it
# silent for the workflow it exists to cover: /ship (and any commit-then-push turn)
# pushes before Stop fires, so the set was already empty and the hook exited without
# asking. Four PRs reached merge unreviewed that way. Pushed-but-unmerged is exactly
# when a review is still worth something.
set -euo pipefail

MAX_ROUNDS="${REVIEW_LOOP_MAX_ROUNDS:-1}"
BASE="${REVIEW_LOOP_BASE:-origin/develop origin/main}"
STATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$STATE_DIR/.review-loop-state"     # one line: <last_reviewed_head> <round> <branch>

git rev-parse --git-dir >/dev/null 2>&1 || exit 0
HEAD="$(git rev-parse HEAD 2>/dev/null)" || exit 0

# This branch's own commits (newest first) = everything not already reachable from an
# integration branch. BASE is a list because both matter: branches get cut from
# origin/main as often as origin/develop, and gating on develop alone counts main's
# develop->main release merges as "ours" (~1300 files) on any branch cut from main.
# Fall back to the unpushed set when no base ref resolves (fresh clone with no fetch)
# rather than going silent.
EXCLUDE=""
for ref in $BASE; do
  git rev-parse --verify --quiet "$ref" >/dev/null 2>&1 && EXCLUDE="$EXCLUDE $ref"
done
if [ -n "$EXCLUDE" ]; then
  NEW="$(git rev-list HEAD --not $EXCLUDE 2>/dev/null || true)"   # unquoted: word-split the ref list
else
  NEW="$(git rev-list HEAD --not --remotes=origin 2>/dev/null || true)"
fi
# Empty => sitting on the base branch, or everything here is already merged.
if [ -z "$NEW" ]; then
  rm -f "$STATE"; exit 0
fi

LAST=""; ROUND=0; LAST_BRANCH=""
[ -f "$STATE" ] && { read -r LAST ROUND LAST_BRANCH < "$STATE" || true; }
ROUND="${ROUND:-0}"
BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo '(detached)')"

# Already reviewed this exact tip -> converged, let Claude finish. Leave the state
# file alone so the round budget CARRIES rather than being zeroed: /code-review runs
# as a background agent, so every round ends the turn twice — once launching the
# review (tip unchanged, lands here) and once after committing its fixes. Zeroing here
# reset the counter on every one of those first stops, so ROUND went 0 -> 1 -> 0 -> 1
# and MAX_ROUNDS was unreachable. One docs-only branch took 7 rounds under a cap of 3.
# The budget is cleared only where it should be: when NEW is empty (merged / on the
# base branch) above, when HEAD moves to a different branch, and when the cap trips.
if [ "$HEAD" = "$LAST" ]; then
  exit 0
fi

# A different branch is a new line of work (one shared state file, not one per branch),
# so it gets its own budget instead of inheriting the rounds another branch spent — a
# branch switch mid-burst would otherwise trip the cap on commit one. Keyed on the branch
# name, NOT on "the sha isn't an ancestor": an amend/rebase/squash in the review->fix
# cycle also breaks ancestry, and zeroing there made MAX_ROUNDS unreachable again (ROUND
# stuck at 1 through any number of amends). Checked here rather than inside the range
# split below, because a branch stacked on another branch's tip DOES descend from the
# last-reviewed sha: an ancestry-gated reset never fired for it, so it inherited the
# parent branch's spent rounds and hit the cap within a commit or two.
[ "$BRANCH" = "$LAST_BRANCH" ] || ROUND=0

# Review range: from the last-reviewed sha if it's still an ancestor, else from
# the parent of this branch's oldest commit, up to HEAD.
OLDEST="$(printf '%s\n' "$NEW" | tail -1)"
if [ -n "$LAST" ] && git merge-base --is-ancestor "$LAST" "$HEAD" 2>/dev/null; then
  RANGE="$LAST..HEAD"
else
  # HEAD doesn't descend from the last-reviewed sha: a different branch or rewritten
  # history. Either way, review this branch's whole set.
  RANGE="${OLDEST}^..HEAD"
fi

# Budget spent -> hand control back WITHOUT reviewing $RANGE. At the default of 1 this is
# the NORMAL path, not a failure: the review ran, its fixes landed, and re-reviewing them
# is opt-in. Name the range that went unreviewed, because marking HEAD below keeps it out
# of every later range too. Clear the budget on the way out — the cap's job is to end THIS
# turn, not to stay quiet for the rest of the branch. Writing a maxed-out counter back
# would trip the cap again on every later commit, so nothing else on the branch would ever
# be reviewed.
if [ "$ROUND" -ge "$MAX_ROUNDS" ]; then
  printf '{"systemMessage":"review-loop: %s review round(s) already spent on this branch; allowing stop without reviewing %s. Raise REVIEW_LOOP_MAX_ROUNDS to review the fixes too, or run /code-review on that range manually."}\n' "$MAX_ROUNDS" "$RANGE"
  printf '%s 0 %s\n' "$HEAD" "$BRANCH" > "$STATE"
  exit 0
fi

# Record the sha we're about to review, then block and request review.
printf '%s %s %s\n' "$HEAD" "$((ROUND+1))" "$BRANCH" > "$STATE"
REASON="New commit(s) in $RANGE haven't passed the review loop. Run /code-review --fix on $RANGE, using .claude/clanker-constitution/clanker-constitution.md as the rubric and honoring the CLAUDE.md invariants (tenancy, vault, HITL, audit, durable resume). Apply and commit fixes for confirmed findings; if there are none, just finish. If HEAD is already pushed, push the fix commits too (git push) — the PR merges the pushed tip, so a committed-but-unpushed fix merges as if it never happened."

python3 -c 'import json,sys; print(json.dumps({"decision":"block","reason":sys.argv[1]}))' "$REASON"
