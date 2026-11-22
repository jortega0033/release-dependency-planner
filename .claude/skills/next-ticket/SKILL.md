---
name: next-ticket
description: Take one ticket of epic #1 up to a ready pull request. Started only by the owner with /next-ticket; starting it is the owner's go signal for that run.
argument-hint: "[issue number]"
disable-model-invocation: true
---

# Next ticket

The owner starts this skill by hand. Starting it is the go signal for one run and counts as the owner's request, for this run, to push the ticket branch and open the pull request. It handles one ticket, then stops. It never merges and never starts another run.

The work itself follows the playbook [`../implement-ticket/SKILL.md`](../implement-ticket/SKILL.md). `CLAUDE.md` wins where the two differ.

## Steps

1. **Refresh the queue.** `gh issue list --state open --limit 100` and `gh issue view` on the epic (#1) and its children. A ticket labelled `status:blocked` whose blockers are all closed becomes `status:ready` (swap the labels).
2. **Pick the ticket.** If an issue number was given, use it, after checking that it is open, not `status:in-progress` and not `needs-decision`. Otherwise take the first `status:ready` ticket in the epic's dependency order (#8, #2, #9, #3, #4, #5, #6, #7) that is not `status:in-progress` and not `needs-decision`. If none qualifies, say why and stop.
3. **Claim it.** Label the issue `status:in-progress`.
4. **Branch in a fresh worktree.** `git fetch origin`, then `git worktree add <path outside this checkout> -b <type>/<issue-number>-<short-slug> origin/main`, as the Git workflow in `CLAUDE.md` says. Work only in that worktree.
5. **Run the `implement-ticket` playbook** for the ticket, including both gates (Code Reviewer, Reality Checker), the `docs/ui-quality.md` check for UI tickets, `unslop` on copy and PR text, and the `CHANGELOG.md` line.
6. **Push and open a draft pull request.** Only after both gates passed on the current diff: push the ticket branch (never `main`) and open a draft pull request (`gh pr create --draft`) from `.github/pull_request_template.md` with `Closes #N` and `Part of epic #1`. The review gate hook blocks `gh pr create` and `gh pr ready` until the gate roles have run after the last code edit.
7. **Wait for CI.** `gh pr checks` on the draft pull request. On failure, fix, re-run the local checks and both gates on the new diff, and push. When CI is green and both gates passed on the current diff, run `gh pr ready` (the hook checks the gates again). Green CI is checked by you, not by Reality Checker.
8. **Report.** Comment on the issue with the pull request link, the CI run link, the evidence and the gate verdicts. Leave the issue open.

## Never

- Merge, enable auto-merge, tag or release. Only the owner merges and releases.
- Force-push, push to `main`, or rewrite published history.
- Start a second ticket in the same run.
- Settle a `needs-decision` ticket yourself. Stop and say what is open.
- Change a decision in `docs/owner-decisions.md`. If one blocks the ticket, stop and say so.
