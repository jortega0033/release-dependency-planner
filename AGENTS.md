# AGENTS.md

The full repository instructions are in [CLAUDE.md](CLAUDE.md). This file repeats only what an agent needs before it reads that.

## Test commands

```
python -m unittest discover -s tests -v
```

Python 3.12 or newer, standard library only. There is no lint step, no build step and no package manifest. Do not add pip or npm dependencies.

## Run

```
python -m release_planner --data-dir ./data --port 8765
```

## Ticket work

To implement a GitHub issue, follow [.claude/skills/implement-ticket/SKILL.md](.claude/skills/implement-ticket/SKILL.md). The role instructions it names are in `.claude/agents/`; each starts with an "In this repository" section. If your tool cannot run those roles as subagents, do each step yourself as the playbook says and state that in the pull request.

## Loop conventions

- The loop runs at L1: report-only, started by hand. It proposes; it does not label, comment, close, edit source, push or merge.
- No loop scheduler or loop workflow is installed. The CI workflow (`.github/workflows/ci.yml`) is not a loop run and schedules nothing. Do not add a scheduled workflow without the owner's approval.
- See [LOOP.md](LOOP.md) for the manual command and the human gates.
