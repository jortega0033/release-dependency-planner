# Architecture, baseline status and PRD drift

This file records how the baseline is built, what was checked against the source, and where [PRD.md](PRD.md) and the code differ. It was written during backlog preparation on 2026-11-22 against commit `876a6b8` (the only commit on `main`). Line numbers refer to that commit. Update this file in the same pull request as any change that makes a row untrue.

How to read the evidence marks:

- **[RUN]**: the command was run during preparation and the result was seen (Windows 11, Python 3.13.14).
- **[READ]**: established by reading the source only.
- **[NOT VERIFIED]**: a claim in the README or the PRD that was not reproduced.

## 1. Pattern

A single-process, layered application on the Python standard library. No framework, no router library, no build step, no third-party package.

| Layer | File | Responsibility |
|---|---|---|
| Entry point | `release_planner/__main__.py` | Parses `--data-dir` and `--port`, calls `make_server`, prints the listening URL, serves until Ctrl-C (`main`, lines 7-22). |
| Transport | `release_planner/server.py` | `Handler` on `ThreadingHTTPServer`: request guards, hand-written routing, JSON error envelope, three allowlisted static files. |
| Domain validation | `release_planner/validation.py` | Pure functions over the submitted payload: field rules, id uniqueness, predecessor rules, cycle detection. No I/O. Called only from `server.py`. |
| Persistence | `release_planner/store.py` | One SQLite connection shared by all threads behind an `RLock`. One `BEGIN IMMEDIATE` transaction per write. No domain rules. |
| UI | `release_planner/static/index.html`, `tokens.css`, `app.css`, `app.js` | Native HTML, CSS and JavaScript in one IIFE. No modules, no bundler. |

Tests: `tests/test_api.py` drives a real server on an ephemeral loopback port with a temporary data directory (24 tests). `tests/test_reference_schedule.py` is a test-only calculator for the future scheduling rules (5 tests). It imports nothing from the application.

## 2. Traced workflow: save a plan, including a rejected cycle

1. **Start.** `python -m release_planner --data-dir D --port P` calls `make_server` (`server.py:262-272`), which creates the directory, binds `127.0.0.1`, and opens `Store(D/release_planner.sqlite3)`. [RUN]
2. **Store open.** `Store.__init__` (`store.py:39-56`) sets `busy_timeout=5000`, WAL and `foreign_keys=ON`, then reads `PRAGMA user_version`: `0` creates the three tables and sets the version to 1, `1` is accepted, anything else raises `RuntimeError`. [READ]
3. **Page load.** `GET /` serves `index.html` from the `STATIC` allowlist (`server.py:15-19`, `_static` at `183-189`). `init()` (`app.js:595-600`) loads the plan list and opens the first plan. [RUN for the HTTP part, READ for the script]
4. **Edit.** Edits change only the in-memory `plan` object and call `markDirty()` (`app.js:123-127`). Nothing is sent until Save. [READ]
5. **Save request.** `savePlan()` (`app.js:510-541`) sends `PUT /api/v1/projects/{id}` with the body from `buildPayload()` (`app.js:492-508`): `version`, `title`, `start_date` and the full task list. [READ]
6. **Guards.** `_dispatch` (`server.py:153-178`) checks, in this order: the `Host` header against `127.0.0.1:<port>` and `localhost:<port>` (403 `forbidden_host`); the route (404); the method (405 with `Allow`); for every method except GET, `Origin == http://<Host>` (403 `forbidden_origin`). [RUN: `HEAD /` returned 405 with `Allow: GET`; the Host and Origin refusals are covered by the suite (CHK-B10, CHK-B11); the order is READ]
7. **Body.** `_body` (`server.py:87-115`) refuses chunked bodies and a missing or malformed `Content-Length` (411), a declared length over 262144 bytes (413), a content type other than `application/json` with an optional UTF-8 charset (415), and anything that is not a JSON object (400). [RUN for 411; the 413, 415 and 400 cases are covered by the suite]
8. **Validation.** `validate_plan_payload` (`validation.py:111-148`) checks shape and field rules and then `_check_tasks` (`151-212`): duplicate ids, non-string, self, duplicate and unknown predecessors, and finally `_has_cycle` (`92-108`, Kahn's algorithm over the valid edges). Errors are collected, not raised one at a time. Any error raises `ValidationError`, which `_put` (`server.py:217-229`) turns into 422 `validation_failed` with a `details` list. Nothing has been written at this point. [RUN: a reversed dependency returned 422 with `{"field":"tasks","code":"cycle","message":"Dependencies form a cycle"}`]
9. **Write.** `Store.replace_plan` (`store.py:132-148`) opens the transaction, compares the stored version (`_locked_version`, `125-130`; mismatch raises `VersionConflict`, returned as 409 with `current_version`), updates the plan row with `version+1`, deletes the plan's tasks (edges go with them through the foreign-key cascade), inserts tasks and edges again, and returns the reloaded plan. [RUN: saving fixture F-LAUNCH returned 200 and version 2]
10. **Result in the UI.** On success the UI adopts the response, or only its version if the user typed during the save (`app.js:521-533`). On 422 it shows the message and the details in the `role="alert"` region and next to the fields, and keeps the edits (`app.js:535-537`, `applyFieldErrors` at `190-212`). On 409 it shows the conflict text and the `Reload plan` button (`showApiError`, `156-162`). [READ]
11. **Restart.** The server holds no state. After stopping and starting it on the same data directory, `GET /api/v1/projects/1` returned a byte-identical body. [RUN]

## 3. Data ownership

- The server and SQLite own every saved plan. The schema is in `store.py:7-21`: `plans`, `tasks` keyed by `(plan_id, task_id)`, `edges` keyed by `(plan_id, task_id, pred_id)`.
- The browser owns only the unsaved edit buffer: `plan`, `dirty`, `saving`, `editSeq` (`app.js:33-37`). A `beforeunload` handler warns when it is dirty (`app.js:588-593`).
- Task ids are generated by the client (`newTaskId`, `app.js:94-101`) and are stable across saves. Position is the array order of the submitted task list.
- The store has no validation of its own beyond the schema constraints. It relies on `server.py` calling `validation.py` first.

## 4. Invariants

| Invariant | Enforced by |
|---|---|
| Every edge joins two tasks of the same plan | Composite foreign keys on `edges` (`store.py:19-20`); `unknown_predecessor` in `validation.py:204-205` |
| No task precedes itself | `CHECK(task_id <> pred_id)` (`store.py:18`); `self_dependency` in `validation.py:200-201` |
| The graph is acyclic | `_has_cycle` (`validation.py:92-108`), called at `211`. The database does not enforce this. |
| Task ids are unique in a plan | Primary key on `tasks` (`store.py:15`); `duplicate_task_id` in `validation.py:167-168` |
| Durations are integers from 1 to 365 | `validation.py:179-182`. The database enforces only `>= 1` (`store.py:14`). |
| The version rises by exactly 1 per successful write | `store.py:136` |
| A write is all or nothing | `_tx` (`store.py:58-68`) |
| A stale write changes nothing | `_locked_version` inside the same transaction (`store.py:125-130`, `134`, `152`) |
| Only loopback, same-host, same-origin clients are served | Bind address (`server.py:265`); Host and Origin checks (`server.py:158-166`) |
| Nothing outside three static files is served from disk | `STATIC` allowlist (`server.py:15-19`) |

## 5. Status against the PRD

Planned work is tracked in epic #1. Its tickets, in dependency order: #8, #2, #9, #3, #4, #5, #6, #7. Each planned row below names its ticket.

| PRD item | Status | Evidence |
|---|---|---|
| M1 plan create, read, replace, delete, list (5.2) | Implemented | Routes at `server.py:118-134`. [RUN] suite, 29 tests `OK`; [RUN] create, save and read over HTTP. |
| Field rules and limits (5.2) | Implemented | `validation.py:7-11`, `32-59`, `151-190`. Covered by CHK-B05 to CHK-B08 in the suite. |
| Version guard, 409 with `current_version` | Implemented | `store.py:125-130`, `server.py:231-233`. CHK-B09, CHK-B14 in the suite. |
| Host, Origin, body cap, security headers | Implemented | `server.py:20-28`, `87-115`, `153-166`. [RUN] headers seen on `GET /api/v1/health`. |
| Persistence across restart (CHK-B04) | Implemented | [RUN] in the suite and by hand with two server starts. |
| UI editing states (1.4) | Implemented, needs verification | `app.js` has status text, dirty tracking, saving, rejection and conflict handling [READ]. No browser was run during preparation. |
| Accessibility requirements (1.5) | Needs verification | `:focus-visible` and a `prefers-reduced-motion` rule exist in `app.css:221-226`; labels, `role="status"` and `role="alert"` exist in `index.html` [READ]. Contrast, keyboard-only operation and the 800x600 layout were not checked. |
| Browser flow CHK-B17 | Needs verification | The README reports a run in Chrome 157 on Windows. [NOT VERIFIED] |
| Suite on Ubuntu 24.04 with Python 3.12 | Needs verification | README claim. [NOT VERIFIED]; only Python 3.13 on Windows was run. |
| RP-1 cycle path (#2) | Planned | `_has_cycle` returns a boolean; the error carries no path. |
| RP-2 holidays and dated schedule (#3) | Planned | No schedule code in `release_planner/`. No holiday column or table. The oracle exists only in `tests/`. |
| RP-3 slack and critical path (#4) | Planned | None. |
| RP-4 scenarios and comparison (#5) | Planned | None. |
| RP-5 export and verified import (#6) | Planned | None. |
| RP-6 release gate (#7) | Planned | None. |
| Schema migrations and a one-line refusal for an unsupported database (7), ticket #9 | Planned | `store.py:52-53` raises `RuntimeError`, which `__main__.py` does not catch, so the user sees a traceback. |

## 6. PRD drift and open points

"Material" means that an implementer who follows only the PRD would build or test the wrong thing.

| # | Finding | Evidence | Material | Handling |
|---|---|---|---|---|
| D1 | `GET /api/v1/projects` is "newest update first" only to the second. `updated_at` has one-second resolution and ties fall back to the higher id, so a plan updated last can be listed second. | `store.py:34-35`, `79`. [RUN]: two plans created and the first one saved within one second listed as `[2, 1]`. | Yes | Decide and test in the baseline-contract ticket (#8): either state the one-second tie rule in PRD 5.2 or store a finer timestamp. |
| D2 | The health body hard-codes `"schema_version": 1`, and CHK-B01 asserts the whole body. The first schema migration makes both wrong. | `server.py:191-192`, `tests/test_api.py:94`. [READ] | Yes | The migration ticket (#9) makes health report the real version. After that, every ticket that adds a schema migration (holidays in #3, then scenarios in #5) changes the value health returns, and updates the literal in CHK-B01 and PRD 5.1 and 5.2 in the same change. |
| D3 | Unknown fields are rejected with `unknown_field` at the plan and the task level. PRD 5.2 does not mention this. A new request field therefore needs a validation change before any client can send it. | `validation.py:62-65`, `116`, `159`; test `test_unknown_field_rejected`. [READ] | Yes | The baseline-contract ticket (#8) adds the rule to PRD 5.2, before the first new field (`holidays`, #3) is added. |
| D4 | `POST /api/v1/projects` accepts a missing or null `start_date` and uses today's date in UTC. The UI depends on it. PRD 5.2 lists `start_date` as a field rule only, and PRD 6.2 says the product uses no time zones. | `validation.py:83-86`, `app.js:484`. [READ] | Minor | Record in PRD 5.2 (part of #8). Not a scheduling input problem, because the user can change the date before saving. |
| D5 | The duration upper bound 365 is a literal, not a named constant like the other limits. | `validation.py:181`. [READ] | Minor | Mention when touching validation; the stage-one trace listed it among the constants. |
| D6 | The PRD lists seven editing states. The UI shows the same status text, `Saved (version N)`, for `clean` and `saved`. | `app.js:115-121`. [READ] | Minor | No action needed unless a ticket depends on telling them apart. |
| D7 | `send_error` also maps 414, 431 and 501 into the JSON envelope. PRD 5.2 does not list them. | `server.py:31-33`, `75-82`. [READ] | Minor | None. |
| D8 | PRD 2 orders RP-5 after RP-4. In code terms an export of one plan's inputs needs holidays (RP-2) but not scenarios. | PRD section 2; issue #6. | Planning | The batch plan treats #5 before #6 as the default order and names the real dependency, so the two can run in parallel if needed. |
| D9 | Issue #5 says a scenario is "an immutable copy of a plan at a version" and also that it is edited independently. | Issue #5 body. | Yes | The updated ticket (#5) defines it: a scenario is copied once, records the plan version it came from, and then has its own version guard. |
| D10 | PRD 5.2's list of untested contract points is accurate: no test covers 411, the `Location` header, list ordering, Origin on PUT and DELETE, a missing DELETE `version`, or the 500 envelope. | `tests/test_api.py` [READ]; [RUN] by hand: `Location: /api/v1/projects/1`, 411 without `Content-Length`, 422 `required` for DELETE without `version`. | Yes | Covered by the baseline-contract ticket (#8) before new routes are added. |
| D11 | The PRD baseline claims for schema (5.1), the first save reaching version 2 (10, step 4) and tasks having no dates (11) match the code. | `store.py:7-21`, `120`, `136`. [RUN] version 2 after the first save. | No | None. |
| D12 | A title that contains a lone UTF-16 surrogate (JSON `"\ud800"`) passes validation and then fails inside SQLite, so the client gets 500 `internal_error` instead of 422. Nothing is stored. PRD 7 says invalid input gives 422. | `validation.py:41` rejects only category `Cc`; `server.py:173-176`. [RUN]: `POST /api/v1/projects` with such a title returned 500 and the plan list stayed empty. | Yes | Fix and test in the baseline-contract ticket (#8). The same input must be refused by every later route that takes text (scenario names, import files). |
| D13 | Any real date up to `9999-12-31` is accepted as `start_date`. Date arithmetic near that limit overflows, as the test oracle shows. | `validation.py:48-59`. [RUN]: `POST` with `9999-12-31` returned 201; the oracle raised `OverflowError` for a start of `9999-12-30`. | Yes, for RP-2 | The schedule ticket (#3) must return a documented 4xx error, never 500, and the comparison in #5 maps the same case the same way. |

Open decisions in the PRD that the backlog now fixes as defaults (each ticket repeats its own):

- Holidays are per plan (PRD 11, [Open]).
- A plan has at most 20 scenarios (PRD 11, [Open]).

## 7. Things an implementer will trip over

1. **No migration path.** `store.py:46-53` knows versions 0 and 1 only. Holidays and scenarios both need schema changes, so the migration runner (#9) comes first.
2. **Whole-plan replace.** `replace_plan` deletes and reinserts every task (`store.py:139-147`). Anything stored per task is lost on each save unless the save rewrites it. Derived values (dates, slack) should be computed on read, not stored.
3. **One connection, one lock.** Every read and write is serialised by `Store._lock`. Compute schedules and diffs in the handler after the store call returns, never inside `_tx`.
4. **Strict payloads.** See D3. Baseline tests send bodies without the future fields, so new fields must be optional with a documented default.
5. **Cycle reporting crosses three places.** The path has to be produced in `validation.py`, survive the `details` list untouched in `server.py:197-200`, and be mapped by `applyFieldErrors` (`app.js:190-212`), which today sends any field that is not `title`, `start_date` or `tasks[i]...` to the general task error area.
6. **Static allowlist and CSP.** A new script or stylesheet is not served until it is in `STATIC` (`server.py:15-19`). Inline script and style are blocked by the CSP. Downloads and file reads in the UI must work under `default-src 'self'`.
7. **Dates in the browser.** `new Date('2026-11-23')` is UTC midnight. Formatting it with local-time getters shows the previous day in time zones behind UTC. Either print the server's strings or use the UTC getters.
8. **Scripted clients need `Origin`.** Every non-GET request without `Origin: http://<host>:<port>` gets 403. Test helpers already send it (`tests/test_api.py:38-41`).
9. **Limits live in two places.** 200 tasks, 50 predecessors, 120 characters, 1 to 365 days, 262144 bytes: `validation.py:7-9`, `181`, `server.py:13` and PRD 5.2. Change them together.
10. **The oracle is a second opinion.** `tests/test_reference_schedule.py` already encodes CHK-F02 to CHK-F04. Application scheduling code should be written separately and tested against it, not imported from it.
