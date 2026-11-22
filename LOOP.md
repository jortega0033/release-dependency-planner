# Loop Configuration: Issue Triage

Scaffolded with `npx --yes @cobusgreyling/loop@0.2.0 init . --pattern issue-triage --tool claude` ([Loop Engineering](https://github.com/cobusgreyling/loop-engineering), MIT). The generated `.grok/` and `.codex/` variants were removed; this repository uses the Claude Code files only. The scaffold generated no workflow file, and none was added.

## Active Loops

| Pattern | Cadence | Status | Command |
|---------|---------|--------|---------|
| Issue Triage | Manual, on request | L1 report-only | `/issue-triage` in a Claude Code session at the repository root |

## Operating level: L1 report-only

- The loop reads open issues with `gh issue list` and `gh issue view` and rewrites `issue-triage-state.md`. That file and `loop-run-log.md` are the only files it may change.
- It never applies labels, comments, closes or edits issues, edits source or tests, commits, pushes, opens pull requests or merges.
- No scheduler is configured. Do not wrap the skill in `/loop`, a cron entry, a scheduled task or a GitHub workflow. The "2h" cadence in the generated skill text describes the upstream pattern, not this repository.
- `loop doctor` prints its own readiness score. That score describes the scaffold, not the operating level. The operating level here stays L1 until the owner changes this file.

## Ticket work is not a loop run

Implementing tickets is not a Loop run. The owner starts it with `/next-ticket`, and it is governed by `CLAUDE.md`, the `implement-ticket` playbook, the review gate hook, CI and branch protection. The loop stays at L1: report-only and unscheduled.

## Next manual triage run

From the repository root, in a new Claude Code session:

```text
/loop-constraints
/issue-triage
```

Headless equivalent:

```text
claude -p "Run the loop-constraints skill, then the issue-triage skill in L1 report-only mode. Update issue-triage-state.md and append one entry to loop-run-log.md. Make no GitHub writes and change no other file."
```

Review the diff of `issue-triage-state.md` afterwards. Committing it is a human decision.

## Health checks

```text
npx --yes @cobusgreyling/loop@0.2.0 doctor .
npx --yes @cobusgreyling/loop@0.2.0 status .
```

Doctor exit codes: 0 healthy, 1 warnings, 2 blocked.

## Human Gates

- Priority assignment (P0, P1): human only.
- Anything touching the request guards in `release_planner/server.py` (Host, Origin, body cap, security headers), the SQLite schema or its migrations, or the public JSON API: always escalate.
- Duplicate closure: human confirms.
- Stale issue closure: human confirms.
- Any change to this file, `loop-budget.md` or `loop-constraints.md`: human only.

## Verifier

`.claude/agents/loop-verifier.md` is the checker for a later maker/checker level. It is limited to `Read, Grep, Glob`, so it cannot run the tests itself and must answer `ESCALATE_HUMAN` when a verdict depends on a test run. It has no role at L1 because the loop proposes no changes.

## Budget

- Sub-agent spawns per run: 0 at L1.
- See `loop-budget.md`.

## MCP

MCP is not required for this pattern. The triage skill reads issues through the `gh` command line.

## Doctor suggestions that were not adopted

`loop doctor` also suggests a `docs/safety.md`, issue and pull request templates, and workflows. They were left out of the loop setup on purpose: the denylists and merge policy are in `loop-constraints.md`, and a scheduled workflow would be the scheduler that L1 excludes. The templates and the CI workflow were added later by the delivery tooling (see "Ticket work is not a loop run"); none of them schedules a loop run.

## Links

- Pattern: https://github.com/cobusgreyling/loop-engineering/blob/main/patterns/issue-triage.md
- Repository instructions: [CLAUDE.md](CLAUDE.md)
- Backlog source of truth: [docs/PRD.md](docs/PRD.md) and the epic issue (#1)
