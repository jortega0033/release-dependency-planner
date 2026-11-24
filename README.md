# Release Dependency Planner

A local release board for planning release tickets. Each plan has a title, tasks with positive integer working-day durations, and directed predecessor links. Plans are saved in SQLite and survive restarts. Cycles, self links and links to missing tasks are rejected before anything is saved.

Python 3.12+ standard library only. No npm or pip dependencies. Everything is fictional sample data.

## Program goal

Build a planning engine for large, uncertain programs: thousands of linked tasks with calendars, people, skills and risk, schedules with proven quality, probabilistic dates, live replanning and an explanation for every date, with no solver library.

The program is planned ([#36](https://github.com/jortega0033/release-dependency-planner/issues/36)). Phase 1 is the current epic [#1](https://github.com/jortega0033/release-dependency-planner/issues/1) and the only phase with tickets.

**Score.** Average gap to the best published results on a pinned set of project scheduling benchmark instances, with the share solved to proven optimality.

| Phase | Content | Hours (rough) | Issue |
|---|---|---|---|
| 1 | The current epic and its tickets | 73 to 122 | [#1](https://github.com/jortega0033/release-dependency-planner/issues/1) |
| 2 | Full scheduling model | 110 to 190 | [#37](https://github.com/jortega0033/release-dependency-planner/issues/37) |
| 3 | Resource solver | 180 to 310 | [#38](https://github.com/jortega0033/release-dependency-planner/issues/38) |
| 4 | Uncertainty | 100 to 170 | [#39](https://github.com/jortega0033/release-dependency-planner/issues/39) |
| 5 | Replanning and explanation | 120 to 200 | [#40](https://github.com/jortega0033/release-dependency-planner/issues/40) |
| 6 | Workbench and exchange | 130 to 220 | [#41](https://github.com/jortega0033/release-dependency-planner/issues/41) |

About 710 to 1210 engineer hours in total: rough estimates, not measurements. The numbers in the score and the finish lines are targets until a run shows them. Only phase 1 has tickets to work; the sub-issues of a later phase are written when it starts. No single session is expected to reach the end.

## Run

```
python -m release_planner --data-dir ./data --port 8765
```

Open http://127.0.0.1:8765/. The server binds to 127.0.0.1 only.

## Test

```
python -m unittest discover -s tests -v
```

## Docs

See [docs/PRD.md](docs/PRD.md) for the product definition, API, checks, demo flow and planned work (cycle paths, calendar-aware scheduling, slack and critical path, what-if comparison, export).

See [docs/architecture.md](docs/architecture.md) for the code layout, the traced save workflow, invariants, and the differences between the PRD and the code. Instructions for coding agents are in [CLAUDE.md](CLAUDE.md).

## Baseline verification

- The unit suite passed on Windows with Python 3.13 and on Ubuntu 24.04 in WSL2 with Python 3.12 (29 tests on Ubuntu). On Linux, use `python3` in the launch and test commands if `python` is unavailable.
- Windows Chrome 157 ran the workflow with external browser requests blocked. Created two tasks with a predecessor link, then saved and reopened the plan with its link intact after a server restart. The browser reported no uncaught page errors.
