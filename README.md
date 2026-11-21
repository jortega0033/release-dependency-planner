# Release Dependency Planner

A local release board for planning release tickets. Each plan has a title, tasks with positive integer working-day durations, and directed predecessor links. Plans are saved in SQLite and survive restarts. Cycles, self links and links to missing tasks are rejected before anything is saved.

Python 3.12+ standard library only. No npm or pip dependencies. Everything is fictional sample data.

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

## Baseline verification

- The unit suite passed on Windows with Python 3.13 and on Ubuntu 24.04 in WSL2 with Python 3.12 (29 tests on Ubuntu). On Linux, use `python3` in the launch and test commands if `python` is unavailable.
- Windows Chrome 157 ran the workflow with external browser requests blocked. Created two tasks with a predecessor link, then saved and reopened the plan with its link intact after a server restart. The browser reported no uncaught page errors.
