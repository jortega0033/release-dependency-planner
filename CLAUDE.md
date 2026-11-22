# CLAUDE.md

Release Dependency Planner is a local release board: plans, tasks with working-day durations, and predecessor links, saved in SQLite and served to one browser on the loopback interface. The baseline (milestone M1) is built. The scheduling epic (issue #1) is not.

## Commands

Both commands were run on 2026-11-22 on Windows 11 with Python 3.13.14, from the repository root.

| Purpose | Command | Observed |
|---|---|---|
| Test | `python -m unittest discover -s tests -v` | `Ran 29 tests`, `OK`, about 13 seconds |
| Run | `python -m release_planner --data-dir ./data --port 8765` | Observed with a scratch data directory and another port (`--port 8793`): it printed `Listening on http://127.0.0.1:8793`. The command as shown, with `./data` and port 8765, is the README form and was not run in that exact form. Open the URL it prints. |

- There is no install step. Python 3.12 or newer is the only requirement.
- `--port 0` picks a free port and prints it. Use it for scratch runs so that you do not collide with a server someone left on 8765.
- There is no lint, format, type-check or build command. CI (`.github/workflows/ci.yml`) runs the test command and the gate self-test; see Delivery workflow. Do not claim that a lint, format, type-check or build step passed.
- On Linux the README says to use `python3` if `python` is missing. That was not re-run during preparation.
- Stop every server you start. `data/` and `*.sqlite*` are ignored by Git; use a scratch `--data-dir` for experiments.

## Hard constraints

These come from [docs/PRD.md](docs/PRD.md) sections 1.3 and 4, and some are enforced by tests.

- Python standard library only. No pip or npm dependency, no package manifest, no build step, for the app and for the tests.
- No external request of any kind: no CDN, web font, remote URL or telemetry. `tests/test_api.py` (`StaticSource`) fails on an `http(s)://` reference in the static files.
- The server binds `127.0.0.1` only. Keep the Host and Origin checks, the body cap and the security headers on every new route.
- The Content-Security-Policy is `default-src 'self'` with no inline script or style. UI code stays in `release_planner/static/`. A new static file must be added to the `STATIC` allowlist in `release_planner/server.py`, or it is not served.
- `app.js` must not use `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` or `eval` (checked by the same test class). Render text with `textContent`.
- All sample data is fictional.

## Sources of truth

| Question | Where to look |
|---|---|
| What the product is, the API, the scheduling conventions (6.2), fixtures (8), acceptance checks (9), demo flow (10) | [docs/PRD.md](docs/PRD.md) |
| How the code is layered, the traced save workflow, invariants, what is implemented or planned, and where the PRD and the code differ | [docs/architecture.md](docs/architecture.md) |
| What to build next and in which order | Epic issue #1 on GitHub and its sub-issues. Dependency order: #8, #2, #9, #3, #4, #5, #6, #7 |
| What was observed to work at baseline, and on which platforms | [README.md](README.md), "Baseline verification" |

Code and tests show what the product does. The PRD says what it should do. When they disagree, do not pick one silently: add a row to the drift table in `docs/architecture.md` and raise it in the ticket.

## Architecture boundaries

Details and source citations are in [docs/architecture.md](docs/architecture.md). The rules that a change must keep:

- `release_planner/validation.py` is pure: no I/O, no SQLite, no HTTP. Graph and payload rules live here. New pure logic (scheduling, slack, diff, export checksum) belongs in pure modules next to it, each testable without a server.
- `release_planner/store.py` owns SQLite and holds no domain rules. Each write is one `BEGIN IMMEDIATE` transaction. It trusts that validation already ran.
- `release_planner/server.py` owns HTTP: guards, routing, the error envelope and static files. It calls validation first and the store second. Do computation outside the store lock.
- `release_planner/static/` is the whole UI. The server owns all saved state; the browser owns only the unsaved edit buffer.
- The schema is at `PRAGMA user_version = 1` and there is no migration path yet. Any schema change needs one first (issue #9).
- `tests/test_reference_schedule.py` is a test-only oracle for PRD 6.2. Keep it independent of application code so that it stays a second opinion.

## Git workflow

Observed state at preparation time: `main` is the default branch with one commit, it is not protected, there was no CI before the SDLC kit, which added `.github/workflows/ci.yml` (see Delivery workflow) and there are no contribution rules in the repository. The rules below are the working defaults until the owner replaces them.

- Never commit to `main` directly. Branch from the tip of `origin/main`, one branch per ticket, named `<type>/<issue-number>-<short-slug>` (for example `feat/2-cycle-path`).
- Keep commits small and use the existing subject style (`feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `chore: ...`).
- Do not push or open a pull request unless the owner asked for it in the current session. Starting `/next-ticket` counts as that request for the run. The pull request names the issue (`Part of epic #1`, `Closes #N`). It is opened as a draft (`gh pr create --draft`) only after both gates passed on the current diff, and marked ready (`gh pr ready`) only when CI is green and both gates still hold; never leave a gate open. The owner reviews and merges. Do not merge, force-push or rewrite published history.
- Do not commit a data directory, a SQLite file, `__pycache__` or a browser report folder. `.gitignore` already covers them.
- A change to behaviour updates the matching PRD section, the check table in PRD section 9 and `docs/architecture.md` in the same pull request.

## Evidence before claiming a ticket done

Report only what you ran and saw. For each ticket, capture:

1. The full-suite command and its last lines: `python -m unittest discover -s tests -v`, with the test count and `OK`. The count must not go down.
2. The names of the new tests and the check ids the ticket names that they cover (`CHK-Bnn` or `CHK-Fnn`; a ticket without a check id, such as #9, needs tests that map to its acceptance criteria), and the PRD section 9 rows that were added or changed.
3. For API changes: one request and response for the main case and one for a rejected case, taken from a real server on a scratch data directory, including the status code.
4. For UI changes: the browser and its version, the steps performed, and what the page showed. Say plainly if no browser run was done. Text labels, keyboard operation and the alert or status region are part of the acceptance criteria (PRD 1.5), not polish.
5. For schema changes: a run that opens a database created by the previous schema version and shows the data intact.
6. CI: the workflow is configured to run the documented checks. Green CI on the draft pull request (`gh pr checks`) comes after both gates and is checked by the driver before `gh pr ready`, not by Reality Checker. If CI did not run, say so and do not mark the pull request ready.
7. `git status --short` showing no stray files, and confirmation that every server started for the check was stopped.

Order: local checks (items 1 to 5 and 7), Code Reviewer, Reality Checker, draft pull request, CI, then ready only on green CI. The gates judge local evidence and never a CI result that does not exist yet.

State what was not verified. A README or PRD claim that you did not reproduce is a claim, not evidence.

## Project agents and ticket work

`.claude/agents/` holds the project roles: eight roles copied from Agency Agents at a pinned revision, plus the Loop verifier, which belongs to [Loop](#loop) and has no part in ticket work. Each Agency Agents role file starts with an "In this repository" section written for this project: the stack and constraints that bind the role, the files it owns or reviews, its commands or the output it must be given, its checklist and what it hands back. That section and this file override the generic upstream text below it. Source paths, licence, local changes, the name collision with a user-level install and the loading check are in [.claude/agency-agents/README.md](.claude/agency-agents/README.md).

When asked to implement, continue or finish a GitHub issue, follow the playbook [`.claude/skills/implement-ticket/SKILL.md`](.claude/skills/implement-ticket/SKILL.md). Claude Code loads it on its own for ticket work; `/implement-ticket <issue number>` starts it by hand. Delegate to the roles without waiting to be asked: each role's `description` ends with a "Use proactively ..." sentence that makes Claude Code do so.

| When | Role | Access | Runs |
|---|---|---|---|
| Before coding | Codebase Onboarding Engineer | read-only | At the start of a ticket in an unfamiliar area, to trace the code paths |
| Before coding | Software Architect | read-only | When a ticket adds or changes a module boundary, data model, schema, public API or dependency |
| While coding | Backend Architect | can edit | When a ticket changes server-side code, HTTP routes, validation, persistence or data migrations (`release_planner/*.py`) |
| While coding | Frontend Developer | can edit | When a ticket changes browser-side code such as pages, components, client state, styling or keyboard interaction (`release_planner/static/`) |
| After coding | Accessibility Auditor | read-only | When UI, keyboard handling, focus order or markup changes |
| After coding | API Tester | can edit | When an endpoint, status code or request and response contract changes (`tests/`) |
| Gate, every ticket | Code Reviewer | read-only | On the full diff; material findings are fixed and reviewed again |
| Gate, every ticket | Reality Checker | read-only | Last, to check each acceptance criterion against the evidence produced |

- The review gate and the acceptance gate run on every ticket, whatever its size. The session or role that wrote a change does not count as its reviewer.
- Read-only roles have `tools: Read, Grep, Glob` and cannot run commands. Give them the diff, the acceptance criteria and the recorded command output.
- List the roles that ran and their verdicts in the pull request description under "Agent roles run".

## Loop

Loop Engineering is set up with the `issue-triage` pattern at L1: report-only and started by hand. It has no scheduler and makes no GitHub writes. See [LOOP.md](LOOP.md) and [loop-constraints.md](loop-constraints.md).

## Delivery workflow

- Start: the owner runs `/next-ticket` ([`.claude/skills/next-ticket/SKILL.md`](.claude/skills/next-ticket/SKILL.md)). It runs one ticket through the [`implement-ticket` playbook](.claude/skills/implement-ticket/SKILL.md) and never merges.
- Gate hook: [`.claude/hooks/role_gate.py`](.claude/hooks/role_gate.py) blocks `gh pr create` and `gh pr ready` until Code Reviewer and Reality Checker ran after the last code edit. `ROLE_GATE=off` in the environment Claude Code is started from switches it off for that session; do not use it to skip a gate.
- Permissions: [`.claude/settings.json`](.claude/settings.json). Edits to CI, agent configuration and Loop files ask first; force pushes, pushes to `main`, `gh pr merge`, releases and reads of `.env` are denied.
- CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml), the `test` job on Linux and Windows. It runs on the draft pull request, after the local checks and both gates, and must be green before the pull request is marked ready.
- Pull request: [`.github/pull_request_template.md`](.github/pull_request_template.md). Labels: `status:ready`, `status:blocked`, `status:in-progress`, `needs-decision`.
- Changelog: every ticket pull request adds one line to [`CHANGELOG.md`](CHANGELOG.md). Releases follow [`docs/RELEASING.md`](docs/RELEASING.md).
- UI and writing: [`docs/ui-quality.md`](docs/ui-quality.md) (ten binding rules) with the `ui-ux-pro-max` and `unslop` skills in `.claude/skills/`.
- Decisions: [`docs/owner-decisions.md`](docs/owner-decisions.md) records the owner's decisions. Changing one needs the owner; if one blocks a ticket, stop and say so.
- Only the owner merges and releases.
