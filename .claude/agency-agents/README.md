# Agency Agents roles used in this repository

The Markdown files in `.claude/agents/` whose names start with `engineering-` or `testing-` are copies of role definitions from Agency Agents. They are project-local Claude Code subagents. The file `loop-verifier.md` in the same folder is not from Agency Agents; it belongs to the Loop Engineering setup described in [`LOOP.md`](../../LOOP.md).

## Source and licence

- Upstream: https://github.com/msitarzewski/agency-agents
- Pinned revision: `8ae6164602c95ca78828b148b9052460ee426885` (upstream `main`, committed 2026-11-09)
- Licence: MIT, "Copyright (c) 2025 AgentLand Contributors". The upstream licence text at the pinned revision is kept unchanged in [`LICENSE`](LICENSE) next to this file (SHA-256 `9a45258434d5cedf0af73c9ad4771373701225038d246c49219026c33677f66f`). It covers only the copied role files, not the rest of this repository.
- Fetched with `gh api -H "Accept: application/vnd.github.raw" "repos/msitarzewski/agency-agents/contents/<path>?ref=<revision>"`.

## Installed roles

"Upstream SHA-256" is the hash of the file as fetched at the pinned revision. Reviewer roles have one added frontmatter line, `tools: Read, Grep, Glob`, so they cannot edit files or run commands. Every role also has a "Use proactively" sentence appended to its `description:` and an inserted "In this repository" section, both described under "Local change: automatic delegation" below. The rest of each file is the upstream text, unchanged.

| File in `.claude/agents/` | `name:` | Upstream path | Upstream SHA-256 | Local change |
|---|---|---|---|---|
| `engineering-software-architect.md` | Software Architect | `engineering/engineering-software-architect.md` | `b85121691776147bacde26673e68fbbacd6a7f0816d1ca8e203c264d25ce1d30` | added `tools: Read, Grep, Glob`; "Use proactively" sentence; "In this repository" section |
| `engineering-code-reviewer.md` | Code Reviewer | `engineering/engineering-code-reviewer.md` | `7509fcc3ea1dda46511b2801996305bf3d4a125576f9655ff0b63df25602f446` | added `tools: Read, Grep, Glob`; "Use proactively" sentence; "In this repository" section |
| `engineering-codebase-onboarding-engineer.md` | Codebase Onboarding Engineer | `engineering/engineering-codebase-onboarding-engineer.md` | `07aa548b45887c3ad768efad5fdbf6e57bea639df4f1b74c7e383142f454e2a1` | added `tools: Read, Grep, Glob`; "Use proactively" sentence; "In this repository" section |
| `testing-accessibility-auditor.md` | Accessibility Auditor | `testing/testing-accessibility-auditor.md` | `362935907af23839775b9c6162f38c0c5a740542ab4350cb5c5b5a0d9f9a4268` | added `tools: Read, Grep, Glob`; "Use proactively" sentence; "In this repository" section |
| `testing-reality-checker.md` | Reality Checker | `testing/testing-reality-checker.md` | `6d32fcdb114233e13902ec6372d50293b120e85d490b5e81d372c29808f988a1` | added `tools: Read, Grep, Glob`; "Use proactively" sentence; "In this repository" section |
| `engineering-backend-architect.md` | Backend Architect | `engineering/engineering-backend-architect.md` | `ac717bde4848d7663fff8a3c7edc711fd119256de6a7ce38c036619372f42c99` | "Use proactively" sentence; "In this repository" section |
| `engineering-frontend-developer.md` | Frontend Developer | `engineering/engineering-frontend-developer.md` | `1ae4cc10b2e0163bd3ed921ad54080b865cd02e591becd8919b64b73fab06dad` | "Use proactively" sentence; "In this repository" section |
| `testing-api-tester.md` | API Tester | `testing/testing-api-tester.md` | `ab91de9188d48bd9c417282c33673a37b066215e90e08c0f1b270d036084e3bb` | "Use proactively" sentence; "In this repository" section |

## Why these roles

| Role | Use in this repository |
|---|---|
| Software Architect (read-only) | Review a ticket's design against the layering in [`docs/architecture.md`](../../docs/architecture.md) before code is written: the migration runner, where schedule and diff code lives, the scenario data model, the export format. |
| Code Reviewer (read-only) | Review a diff for correctness, missed edge cases and broken invariants (version guard, validation before write, request guards on new routes). |
| Codebase Onboarding Engineer (read-only) | Trace a code path and report facts with file and line citations. |
| Accessibility Auditor (read-only) | Review keyboard operation, focus handling, labels, text alternatives to colour, and the status and alert regions. PRD section 1.5 makes these requirements, and several tickets carry them as acceptance criteria. |
| Reality Checker (read-only) | Compare claimed evidence with what was actually run before a ticket or the release gate is called done. |
| Backend Architect | Implement work in `release_planner/*.py` (HTTP layer, storage and migrations, validation, scheduling). |
| Frontend Developer | Implement work in `release_planner/static/`. |
| API Tester | Write the HTTP-level `unittest` cases in `tests/` for new and existing routes. |

The three implementing roles are written for larger stacks (frameworks, cloud services, Postman, k6, Playwright). In this repository the rules in [`CLAUDE.md`](../../CLAUDE.md) win: Python standard library only, native HTML, CSS and JavaScript, `unittest`, no pip or npm dependencies, no external requests.

Roles that were considered and left out: Test Automation Engineer and Evidence Collector (browser automation needs a dependency this repository does not allow; the release gate ticket uses a written browser script instead), Database Optimizer (one small SQLite file, no query tuning in the backlog).

## Name collision with user-level agents

A developer who has installed Agency Agents in `~/.claude/agents/` already has agents with the same `name:` values. Claude Code gives the project-level definition precedence, so inside this repository the copies here are used, including the read-only tool limits. The upstream names were kept on purpose so that the roles stay recognisable and can be compared with upstream.

A Claude Code session that was already running when these files were added keeps the definitions it loaded at start. Start a new session to pick up the project copies.

## Check that the roles load

From the repository root, in a new session:

```text
claude -p "List the project-level subagents defined in .claude/agents with the tools each one may use. Then run the Reality Checker subagent and ask it which tools it has."
```

The five reviewer roles and `loop-verifier` must report exactly `Read, Grep, Glob`.

### What was observed, and what was not

Observed on 2026-11-22 with Claude Code 2.1.323, headless (`claude -p`, no MCP servers), from the repository root, on a machine that also has a user-level Agency Agents install:

- All nine names were listed. Software Architect, Code Reviewer, Codebase Onboarding Engineer, Accessibility Auditor, Reality Checker and `loop-verifier` were listed with `Read, Grep, Glob`. Backend Architect, Frontend Developer and API Tester were listed with all tools.
- A launched Reality Checker reported exactly `Read`, `Grep`, `Glob`. The user-level copies have no `tools:` line, so the project copies were the ones loaded.
- At the time of this check the three implementing roles were unchanged from the pinned upstream, but the user-level install on that machine is an older upstream revision with different example code. Each role was launched and asked to quote its own instructions, and each quoted text that exists only in the project copy: Backend Architect listed the tables `users`, `categories`, `products` (the user-level copy has no `categories` table), Frontend Developer quoted the comment "Renderable cell values and stable IDs keep the example self-contained.", and API Tester quoted `import { randomUUID } from 'node:crypto';`. This shows project precedence for these three on that machine.
- **Not shown:** behaviour in an interactive session, and behaviour on a machine without a user-level install (there the nine names must simply be listed).
- The listing gives names and tools only, not the file a definition comes from. The statements above about which copy was loaded rest on the tool limits and the quoted text.

## Updating

Fetch the same paths at a newer revision, re-apply the local changes listed in the table above (see "Local change: automatic delegation" below), and update the revision and hashes in this file in the same commit.

## Local change: automatic delegation (2026-11-22)

One sentence beginning "Use proactively" was appended to the `description:` line of every Agency Agents role in `.claude/agents/` (not to `loop-verifier`). Claude Code uses that field to decide when to delegate, so the roles now run during ticket work without being named.

A section headed `## In this repository` was also inserted in every Agency Agents role file, directly after the closing `---` of the frontmatter and before the upstream text (not in `loop-verifier`). It is project-specific text written for this repository: the stack and constraints that bind the role, the files it owns or reviews, its commands or the command output it must be given, a checklist that names its source documents, the parts of the upstream text that do not apply here, and what the role hands back. It is not upstream text, and the upstream text below it is unchanged.

This supersedes any statement above that a role file is unmodified or unchanged, or that the `tools:` line is the only local change. To compare a role with the pinned upstream file, first remove the "In this repository" section (from its heading to the line before the upstream `# ...` title), the "Use proactively" sentence, and the `tools:` line where one was added. After an update from upstream, insert the section again and check that it is still true of the repository.

The steps at which each role runs are in `.claude/skills/implement-ticket/SKILL.md`.

Verification, 2026-11-22: after the sections were inserted, `claude -p "List every project subagent defined in .claude/agents with its exact name and tools, say for each whether its instructions begin with a section titled In this repository, and say whether a skill named implement-ticket is available. Plain list, no commentary." --model haiku` was run once from the repository root with Claude Code 2.1.323. It listed all nine names. Software Architect, Code Reviewer, Codebase Onboarding Engineer, Accessibility Auditor, Reality Checker and `loop-verifier` were listed with `Read, Grep, Glob`; Backend Architect, Frontend Developer and API Tester were listed as having no `tools` line. It answered "yes" for the "In this repository" section on the eight Agency Agents roles and "no" on `loop-verifier`, and reported the skill `implement-ticket` as available. Not shown: the answer may come from reading the files, so it does not prove what a launched subagent receives as its instructions; no role was launched in this check, and no interactive session was tried.

## Local change: SDLC kit (2026-11-22)

This pass added delivery tooling around the roles. No role text other than the checklist lines below changed.

- Review gate hook `.claude/hooks/role_gate.py` (gate roles: Code Reviewer, Reality Checker) and `.claude/settings.json` with the hook registration and permission rules.
- `.claude/skills/next-ticket/SKILL.md`, and `implement-ticket` extended with the UI skill, UI check, `unslop`, CI and changelog steps.
- Skills `ui-ux-pro-max` and `unslop` under `.claude/skills/`, each with its own `PROVENANCE.md`.
- One checklist line naming `docs/ui-quality.md` was added to the "In this repository" section of Frontend Developer, Accessibility Auditor and Code Reviewer. UI Designer and UX Architect are not installed here.
- Reality Checker was already installed; nothing was added for it.
- Also added: `.github/` (CI workflow, pull request template, CODEOWNERS, issue template, Dependabot), `SECURITY.md`, `CHANGELOG.md`, `docs/RELEASING.md`, `docs/ui-quality.md`, `docs/owner-decisions.md`, a note in `LOOP.md`, and a "Delivery workflow" part in `CLAUDE.md`.
