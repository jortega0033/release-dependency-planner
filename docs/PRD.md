# Release Dependency Planner: PRD and Technical Specification

Package: `release_planner`. Status: baseline implemented locally (milestone M1); the epic below is future work. All names, dates and records in this document are fictional.

How the baseline is built, what was re-checked against the source, and where this document and the code differ is recorded in [architecture.md](architecture.md).

Labels used throughout: **[Baseline]** is built in M1. **[Future]** is planned and not built. **[Default]** is a proposed choice that can be changed. **[Open]** is an unresolved decision.

## 1. Product definition

### 1.1 User and problem
A release coordinator on a small team tracks a release as a set of tickets (freeze the branch, build, run regression, write notes, ship). Tickets have a duration in working days and depend on other tickets. Today this lives in a spreadsheet where dependencies are implied by row order, cycles and dangling references go unnoticed, and "what if the build takes a day longer?" means copying the sheet.

The tool models a **release board**: a plan with a title and start date, tasks with positive integer working-day durations, and directed predecessor links. It is about release tickets, not staffing, people, or shifts. There are no assignees or capacity.

### 1.2 End-to-end outcome
- **Baseline outcome [Baseline]:** open the app on the local machine, create a plan, add tasks, set durations, choose predecessors, save, stop the server, start it again on the same data directory, and see the identical plan. Invalid graphs (self links, links to missing tasks, cycles, including a reversed dependency) are refused with a clear message and nothing is changed.
- **Epic outcome [Future]:** from the same board, see the dated schedule, slack and the critical path, compare what-if versions side by side, and export a verifiable plan file.

### 1.3 Scope boundaries
In scope for the product: single local user, one browser profile, fictional or non-sensitive data, loopback only.
Out of scope: accounts, sharing, real ticket-tracker integrations, resource levelling, partial-day durations, time zones, cloud sync, mobile layouts below 800x600.

### 1.4 Workflow states
A plan is in one of these editing states in the UI:
1. `empty` (no plans saved), 2. `clean` (matches stored version), 3. `dirty` (local edits), 4. `saving`, 5. `saved` (clean, shows `version N`), 6. `rejected` (server validation error shown, local edits kept), 7. `conflict` (stored version moved; local edits kept until the user reloads).

### 1.5 Accessibility and design
Workboard with paper panels and blue-green accents. Task rows are easy to read. Dependencies are shown as text (`After: Build, Regression`) as well as visually (a dependency chip). Requirements: visible focus ring, all actions via keyboard, move up/down buttons instead of drag, labelled fields, status in an `aria-live` region and errors in a `role="alert"` region, contrast of at least 4.5:1, reduced-motion respected, usable at 800x600 without horizontal page scroll.

### 1.6 Smallest durable milestone (M1)
The editable, persisted, validated board described in section 1.2 with the baseline checks in section 7.

## 2. Epic and stories [Future]

**EPIC-1: Schedule, analyse and compare release plans.** Turn the saved board into a dated schedule with critical-path insight, what-if comparison, and a verifiable export.

| ID | Story | Depends on | Observable outcome |
|---|---|---|---|
| RP-1 | Cycle path diagnostics | M1 | A rejected cycle names the tasks in order, e.g. `Build -> Test -> Build`, and the UI highlights them. |
| RP-2 | Calendar and holiday-aware scheduling | M1 | Each task shows start and exclusive end dates; weekends and listed holidays are skipped. |
| RP-3 | Slack and critical path | RP-2 | Each task shows total slack in working days; zero-slack tasks form the critical path. |
| RP-4 | Versioned what-if comparison | RP-2, RP-3 | A named scenario copies a plan; a diff shows changed finish date and critical path. |
| RP-5 | Export and verification | RP-2..RP-4 | A plan exports to a JSON file with a checksum; import verifies it and rejects tampering. |
| RP-6 | Release integration gate | RP-1..RP-5 | The full check suite and the browser flow pass on a clean data directory. |

Ordering: RP-1 and RP-2 are independent and can start right after M1. RP-3 needs RP-2. RP-4 needs RP-3. RP-5 needs RP-4. RP-6 is last.

## 3. Milestones

| Milestone | Content | Gate |
|---|---|---|
| M1 [Baseline] | Board editor, SQLite persistence, validation, loopback server | CHK-B01..CHK-B17 |
| M2 [Future] | RP-1, RP-2 | CHK-F01..CHK-F04 |
| M3 [Future] | RP-3, RP-4 | CHK-F05..CHK-F08 |
| M4 [Future] | RP-5, RP-6 | CHK-F09..CHK-F11 |

## 4. Architecture [Baseline]

- Python 3.12+ standard library only. `http.server.ThreadingHTTPServer`, `sqlite3`, `json`. No third-party packages for the app or tests.
- Front end: static HTML, CSS and native JavaScript served from the package. No build step, no CDN, no web fonts.
- Entry point: `python -m release_planner --data-dir <directory> --port <port>`. Binds only to `127.0.0.1`. Port `0` picks a free port and the chosen port is printed.
- Test entry point: `python -m unittest discover -s tests -v`. Tests start the real server on an ephemeral loopback port with a disposable data directory.
- Module layout: `store.py` (SQLite access and transactions), `validation.py` (pure payload and graph validation), `server.py` (HTTP, guards, static files), `static/` (UI).
- Request guards: the `Host` header must be `127.0.0.1:<port>` or `localhost:<port>` (guards against DNS rebinding). Writes require `Origin` equal to `http://<Host>`. JSON bodies are capped at 262144 bytes. Responses carry a strict Content-Security-Policy, `nosniff`, `no-store` and no CORS headers.

## 5. Data schema and API [Baseline]

### 5.1 Schema (SQLite, `PRAGMA user_version = 1`)
- `plans(id, title, start_date, version, created_at, updated_at)`
- `tasks(plan_id, task_id, position, title, duration_days)` with primary key `(plan_id, task_id)` and `duration_days >= 1`.
- `edges(plan_id, task_id, pred_id)` meaning `pred_id` must finish before `task_id` starts. A check forbids `task_id = pred_id`; foreign keys tie both ends to existing tasks with cascading delete.
- Write mode: WAL, foreign keys on, one `BEGIN IMMEDIATE` transaction per write.

### 5.2 API (JSON)
| Method and path | Result |
|---|---|
| `GET /api/v1/health` | `200 {"status":"ok","api_version":1,"schema_version":1}` |
| `GET /api/v1/projects` | Plan summaries, newest update first |
| `POST /api/v1/projects` | Create (`201`), version 1, no tasks |
| `GET /api/v1/projects/{id}` | Full plan with tasks and predecessor ids |
| `PUT /api/v1/projects/{id}` | Atomic full replace guarded by `version`; returns version + 1 |
| `DELETE /api/v1/projects/{id}?version=N` | `204`, or `409` if stale |

Errors use `{"error":{"code","message","details":[{"field","code","message"}]}}`. Statuses: 400 bad JSON, 403 host or origin, 404, 405, 409 version conflict, 411, 413, 415, 422 validation, 500.

Field rules: titles are trimmed, 1..120 characters, no control characters. Task ids match `^[A-Za-z0-9_-]{1,32}$`. Durations are JSON integers from 1 to 365. At most 200 tasks and 50 predecessors per task. `start_date` is a real `YYYY-MM-DD` date.

The tests in `tests/test_api.py` cover part of this contract (CHK-B01..CHK-B16). Not yet covered: 411 responses, the `Location` header, list ordering, Origin checks on PUT and DELETE, a missing DELETE `version`, and the 500 envelope.

## 6. Algorithm and invariants

### 6.1 Baseline: graph validation [Baseline]
Invariants after every successful write: every edge joins two tasks of the same plan; no task precedes itself; the graph is acyclic; ids are unique within a plan; the plan version increases by exactly one.

Validation runs on the submitted payload before any write: shape and field rules, then duplicate ids, unknown predecessors and self links, then cycle detection with Kahn's algorithm (repeatedly remove tasks with no remaining predecessors; if tasks remain, a cycle exists). Only then is the write transaction opened and the version compared inside it. A reversed dependency (A before C stored, A after C submitted) is a cycle and is refused with the stored plan and version unchanged.

### 6.2 Scheduling conventions [Future, fixed here so tests can be written now]
All arithmetic uses calendar dates only (`YYYY-MM-DD`), with no clock times and no time zones.
- **Working day:** Monday to Friday that is not in the plan's holiday list. [Default] The weekend is fixed to Saturday and Sunday.
- **Start:** a task starts on the later of the plan's start date and the latest predecessor end, moved forward to the next working day if it falls on a non-working day.
- **End is exclusive:** the end of a task is the next working day after its last occupied working day. A task of `d` days occupies `d` working days starting at its start. A successor can start on its predecessor's exclusive end.
- **Ties:** when two predecessors end on the same date, either can drive the start; both are on a critical path if the successor is. Equal slack is reported equal. Display order follows plan position.
- **Slack:** total slack in working days equals latest allowed finish minus earliest finish, from a backward pass anchored on the project end (the latest exclusive end). Critical means slack of 0.
- **Duration** counts working days. [Open] Whether a holiday inside a task extends it is answered by the rule above: yes, because holidays are not working days.

### 6.3 Toughest interaction [Future]
Version comparison (RP-4) must show a stable diff when a scenario adds, removes or reorders tasks, matching tasks by id and not by position. Multi-tab editing relies on the `version` guard from M1: a stale save returns `409`, the UI keeps the user's edits and offers a reload.

## 7. Errors, retry and restart

- Validation failure: `422`, no write, UI shows messages near the fields and in the alert region; edits stay.
- Stale version: `409`, UI shows conflict state with `Reload plan`; edits are kept until the user chooses.
- Network failure or `500`: UI shows an error and returns to `dirty`; Save can be retried. A retry is safe: a save that did commit before the connection dropped makes the retry return `409`, which the user resolves by reloading.
- Restart: all state lives in SQLite; the server holds none. After restart the plan list and each plan are identical (CHK-B04).
- Cancel: closing the tab while dirty triggers a browser warning; unsaved edits are not stored.
- Multi-tab: two tabs editing the same plan are serialized by the version guard; the second save gets `409`.
- Unsupported database: [Baseline] the server refuses to start when `user_version` is not 1. [Future] Print a one-line message instead of a traceback, and add migrations (RP-2).

## 8. Deterministic fixtures

Fixture **F-LAUNCH** (fictional): plan "Launch week", start `2026-11-23` (Monday).

| Task | Title | Days | After |
|---|---|---|---|
| a | Freeze branch | 2 | none |
| b | Draft notes | 1 | none |
| c | Ship build | 2 | a, b |

Calculated expectations [Future, calculated by hand and by the reference calculator in `tests/test_reference_schedule.py`]:

| Variant | a | b | c | Critical |
|---|---|---|---|---|
| Base | starts Mon 11-23, ends Wed 11-25 (exclusive) | Mon 11-23, ends Tue 11-24 | starts Wed 11-25, ends Fri 11-27 | a, c; b slack 1 |
| a = 3 days | Mon 11-23, ends Thu 11-26 | unchanged | starts Thu 11-26, ends Mon 11-30 | a, c |

In the second variant c occupies Thu 11-26 and Fri 11-27, so its exclusive end skips the weekend to Monday 11-30.

Cycle fixture: tasks a, b, c with `a -> b -> c`; submitting `a` after `c` is rejected at baseline and must report the path `a -> b -> c -> a` once RP-1 ships.

## 9. Acceptance checks

Status key: **Automated** (runs in `python -m unittest discover -s tests -v`), **Browser** (manual or scripted demo, section 10), **Planned** (future, not yet runnable). See the [baseline verification](../README.md#baseline-verification) for observed results.

### 9.1 Baseline (M1)
| ID | Check | Type |
|---|---|---|
| CHK-B01 | `GET /api/v1/health` returns the documented body | Automated |
| CHK-B02 | Create then get a plan round-trips title, start date, version 1 | Automated |
| CHK-B03 | F-LAUNCH saves via PUT; predecessors returned; version becomes 2 | Automated |
| CHK-B04 | After stopping and restarting the server on the same directory, the plan is identical | Automated |
| CHK-B05 | Self dependency returns 422 `self_dependency`; stored plan unchanged | Automated |
| CHK-B06 | Unknown predecessor returns 422 `unknown_predecessor` | Automated |
| CHK-B07 | 2-task and 3-task cycles and reversed dependency return 422 `cycle`; stored plan and version unchanged | Automated |
| CHK-B08 | Durations 0, -1, 1.5, "2", true, 366 are rejected; 1 and 365 accepted | Automated |
| CHK-B09 | Stale version returns 409 with `current_version` | Automated |
| CHK-B10 | Wrong `Host` returns 403 `forbidden_host` | Automated |
| CHK-B11 | Missing or cross-origin `Origin` on writes returns 403 `forbidden_origin` | Automated |
| CHK-B12 | Oversized body 413, invalid JSON 400, wrong content type 415 | Automated |
| CHK-B13 | Markup in titles is stored and returned verbatim; static JS does not use `innerHTML`; CSP header present | Automated |
| CHK-B14 | Delete with right version returns 204 then 404; stale delete 409 | Automated |
| CHK-B15 | Static page, CSS and JS served; required labels present in the page or script | Automated |
| CHK-B16 | Server socket is bound to `127.0.0.1` | Automated |
| CHK-B17 | Browser flow in section 10 completes, including restart and blocked external requests | Browser |

### 9.2 Future
| ID | Story | Check | Type |
|---|---|---|---|
| CHK-F01 | RP-1 | Cycle error includes ordered path `a -> b -> c -> a` for the cycle fixture | Planned |
| CHK-F02 | RP-2 | F-LAUNCH base dates match section 8 | Planned |
| CHK-F03 | RP-2 | F-LAUNCH with a = 3 matches section 8 | Planned |
| CHK-F04 | RP-2 | A holiday on Tue 2026-11-24 moves a's exclusive end to Thu 11-26 | Planned |
| CHK-F05 | RP-3 | Base: b slack 1, a and c slack 0 | Planned |
| CHK-F06 | RP-3 | Two equal-length parallel chains are both critical | Planned |
| CHK-F07 | RP-4 | Scenario with a = 3 shows finish moving from Fri 11-27 to Mon 11-30 | Planned |
| CHK-F08 | RP-4 | Reordering tasks produces no spurious diff | Planned |
| CHK-F09 | RP-5 | Export then import reproduces the plan; edited export fails verification | Planned |
| CHK-F10 | RP-6 | Full unit suite passes on a clean directory | Planned |
| CHK-F11 | RP-6 | Browser flow covers schedule, compare and export with external requests blocked | Planned |

## 10. Demo flow and commands

Scripted API demo (PowerShell on a machine with Python 3.12+; replace the directory as needed):

```
python -m release_planner --data-dir .\demo-data --port 8765
```
Open `http://127.0.0.1:8765/` in Chrome, then:
1. `New plan`, set `Plan title` to "Launch week" and `Start date` to 2026-11-23.
2. `Add task` three times: "Freeze branch" 2 days, "Draft notes" 1 day, "Ship build" 2 days.
3. On "Ship build" tick predecessors "Freeze branch" and "Draft notes". The row reads `After: Freeze branch, Draft notes`.
4. `Save plan`; status reads `Saved (version 2)` [the first save after creation].
5. Make "Freeze branch" depend on "Ship build" and `Save plan`; an alert reports a cycle and stored data is unchanged.
6. Stop the server (Ctrl-C), start it again with the same command, reload the page: the plan is identical.
7. Block external requests (DevTools Network request blocking, or disconnect the network): the board still works because nothing is fetched from outside `127.0.0.1`.

Tests: `python -m unittest discover -s tests -v`.

## 11. Assumptions and limitations

- [Default] Single-user, single-machine. Not hardened for untrusted networks beyond the loopback, Host and Origin checks.
- [Default] Tasks have no dates at baseline. The schedule, slack and critical path are future work, and the conventions in 6.2 are not enforced by M1 code.
- [Default] Plan start date may be any weekday; scheduling will roll it forward.
- [Default] Whole-plan replace on save (simple, atomic) rather than per-task patches.
- [Default] Task ids are client-generated and stable; new tasks use `t1`, `t2`, ...
- [Open] Holiday list is per plan or global? Proposed: per plan.
- [Open] Maximum scenarios per plan for RP-4.
- See the [baseline verification](../README.md#baseline-verification) for observed platform and browser results. The planned checks remain milestone gates.

## 12. Baseline versus work ahead

| Built in M1 | Still ahead |
|---|---|
| Plan CRUD, tasks, durations, predecessors | Cycle path diagnostics (RP-1) |
| Reject dangling, self and cyclic links before mutation | Calendar, holidays, dated schedule (RP-2) |
| SQLite persistence, restart | Slack and critical path (RP-3) |
| Version guard and conflict UI | What-if scenarios and comparison (RP-4) |
| Loopback, Host and Origin checks, body cap, CSP | Export and verification (RP-5) |
| Accessible editor UI | Release integration gate (RP-6) |
