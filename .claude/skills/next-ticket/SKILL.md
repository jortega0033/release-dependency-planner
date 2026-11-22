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

1. **Refresh the queue.** `gh issue list --state open --limit 100` and `gh issue view` on the epic (#1) and its children. A ticket labelled `status:blocked` whose blockers are all closed becomes `status:ready` (swap the labels). Also check parents: a ticket whose sub-issues (`gh api repos/jortega0033/release-dependency-planner/issues/<n>/sub_issues`) are all closed is closed with a comment.
2. **Pick the ticket.** Only leaf tickets are work. A ticket labelled `tracking`, or with open sub-issues, is a container and is never picked. If an issue number was given and it is a `tracking` parent, refuse it and list its open sub-issues. Otherwise check that it is open, not `status:in-progress` and not `needs-decision`. With no number, take the first `status:ready` leaf ticket in the epic's order: the parents in the epic's dependency table (#8, #2, #9, #3, #4, #5, #6, #7, #11), then the sub-issues inside each parent in their listed order. If none qualifies, say why and stop.
3. **Claim it.** Label the issue `status:in-progress`.
4. **Branch in a fresh worktree.** `git fetch origin`, then `git worktree add <path outside this checkout> -b <type>/<issue-number>-<short-slug> origin/main`, as the Git workflow in `CLAUDE.md` says. Work only in that worktree.
5. **Run the `implement-ticket` playbook** for the ticket: implement and run the local checks, then, before any gate, write the review material to `.claude/state/review/` in the worktree (`git diff --stat origin/main...HEAD`, `git diff origin/main...HEAD`, the recorded check outputs) and name those files when you call Code Reviewer and then Reality Checker, which have no shell. Include the `docs/ui-quality.md` check for UI tickets, `unslop` on copy and PR text, and the `CHANGELOG.md` line.
6. **Push and open a draft pull request.** Only after both gates passed on the current diff: push the ticket branch (never `main`) and open a draft pull request (`gh pr create --draft`) from `.github/pull_request_template.md` with `Closes #N` and `Part of epic #1`. If the ticket is the last open sub-issue of a parent, the pull request also says `Closes #<parent>`. The review gate hook blocks `gh pr create` and `gh pr ready` until the gate roles have run after the last code edit.
7. **Wait for CI without polling.** After the push and the draft pull request, bind the pull request to the session when the app offers it, then end the turn with the line "Draft pull request #N is waiting for CI". Do not loop, sleep or watch. When the session is woken (a CI event, or the owner says "continue"), read `gh pr checks <n>` once: green, then run `gh pr ready` (the hook checks the gates again; green CI is checked by you, not by Reality Checker); red, then fix, re-run the local checks and both gates on the new diff, and push; still running, then end the turn again with the same line.
8. **Report.** Comment on the issue with the pull request link, the CI run link, the evidence and the gate verdicts. Leave the issue open.

## Never

- Merge, enable auto-merge, tag or release. Only the owner merges and releases.
- Force-push, push to `main`, or rewrite published history.
- Start a second ticket in the same run.
- Settle a `needs-decision` ticket yourself. Stop and say what is open.
- Change a decision in `docs/owner-decisions.md`. If one blocks the ticket, stop and say so.
