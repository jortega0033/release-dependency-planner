# Owner decisions

Decisions the owner made for this repository, so the rules do not depend on anyone's memory of a conversation. Changing any entry needs the owner. An agent that finds a decision blocking a ticket stops and says so.

All entries are dated 2026-11-22, except where an entry gives its own date.

1. **The instructions, tooling and playbook live on the default branch.** Date: 2026-11-22. Implemented in: `CLAUDE.md`, `.claude/`.
2. **Persona agents run automatically during ticket work and carry instructions tailored to this project.** Date: 2026-11-22. Implemented in: `.claude/agents/` ("In this repository" sections and "Use proactively" descriptions), `.claude/agency-agents/README.md`, `.claude/skills/implement-ticket/SKILL.md`.
3. **Every open ticket is about app implementation; tooling is installed, not ticketed.** Date: 2026-11-22. Implemented in: `.claude/skills/next-ticket/SKILL.md`, `.github/ISSUE_TEMPLATE/implementation-ticket.md`.
4. **Agents may take a ticket up to a ready pull request. Only the owner merges and releases.** Date: 2026-11-22. Implemented in: `CLAUDE.md` ("Git workflow", "Delivery workflow"), `.claude/skills/next-ticket/SKILL.md`, `.claude/settings.json` (deny rules), `docs/RELEASING.md`.
5. **No scheduler. Ticket work starts only on the owner's go signal (`/next-ticket`), because the repository is used to train AI models.** Date: 2026-11-22. Implemented in: `.claude/skills/next-ticket/SKILL.md` (`disable-model-invocation: true`), `LOOP.md`.
6. **A review gate hook blocks opening or readying a pull request until the gate roles have run after the last code edit.** Date: 2026-11-22. Implemented in: `.claude/hooks/role_gate.py`, `.claude/settings.json` (`hooks`).
7. **Loop Engineering stays at L1, report-only and unscheduled.** Date: 2026-11-22. Implemented in: `LOOP.md`.
8. **Continuous integration runs on Linux and Windows; the default branch requires a pull request and green checks.** Date: 2026-11-22. Implemented in: `.github/workflows/ci.yml` (the `test` job). Branch protection is set by the orchestrator on GitHub, not in a file.
9. **Permission rules: documented commands are allowed; force pushes, pushes to the default branch, merges, releases and reads of secrets are denied; edits to CI, agent configuration and Loop files ask first.** Date: 2026-11-22. Implemented in: `.claude/settings.json` (`permissions`).
10. **Open decisions on tickets are settled with the ticket's stated default.** Date: 2026-11-22. Implemented in: the issues listed below. Where a ticket states no default, the conservative option is taken and flagged in the issue.
    - #1 (epic): holidays are per plan; at most 20 scenarios per plan and no scenarios of scenarios; dates, slack and critical path are computed on read, never stored; new request fields are optional with a documented default; an export carries one plan's inputs and no scenarios; no new dependency, build step or external request.
    - #3: holidays are per plan; an absent `holidays` field on `PUT` means an empty list.
    - #5: scenario limit is 20 per plan and scenarios cannot have scenarios; "immutable copy" means independent of later plan edits; data model is a row in `plans` with a nullable parent plan id and base version (schema migration 3).
    - #6: done after #5 (PRD section 2 order).
    - #8: list ordering keeps the stored timestamp format; plans updated in the same second are listed with the higher id first, and PRD 5.2 states this. A finer timestamp is not adopted (stated default).
11. **Rust verified in CI only.** Not applicable: this repository has no Rust.
12. **The ten UI rules in `docs/ui-quality.md` are binding, and the `ui-ux-pro-max` and `unslop` skills are installed in the repository and used for UI work and for copy.** Date: 2026-11-22. Implemented in: `docs/ui-quality.md`, `.claude/skills/ui-ux-pro-max/`, `.claude/skills/unslop/`, `.claude/skills/implement-ticket/SKILL.md`.
13. **Visual system: Pipenzo Flow look tokens (docs/design-tokens.md). SDLC kit version: jortega0033/sdlc-kit v1.0.0.** Date: 2026-11-23. Implemented in: `release_planner/static/tokens.css`, `release_planner/static/app.css`, `docs/design-tokens.md`.
14. **Accent on the current selection; focus ring, themes, linking and one primary button.** Date: 2026-11-23. Implemented in: `docs/design-tokens.md` ("Accent and selection rules"); the page follows in ticket work (not done yet). Sources, as given:
    - D1 Current selection: the yellow accent is used for the primary action, the current-step marker and the current selection (UI rule 8). Decided by the owner on 2026-11-23. How (recommended by the orchestrator, adopted under the owner's delegation of the same day): a selection uses a solid --primary fill with --on-primary text (not only a yellow border, which has about 1.5:1 against white on light), plus a second sign that is not colour (weight, icon or text) and the existing aria attribute. Never a tint with a same-hue border and never a thick one-sided border.
    - D2 Focus ring: --focus is a focus indicator, exempt from the accent limit, including where it is yellow in dark. A ticket that says the focus style stays unchanged means the rule on main after the token pull request. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
    - D3 Themes: contrast and no-colour-alone checks cover both the light and the dark block of tokens.css. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
    - D4 Linking: a ticket that creates a page or its static allowlist links tokens.css before any other stylesheet and serves it (allowlist and its test). Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
    - D5 release-dependency-planner: while a plan is open only one yellow primary button shows; "New plan" (#new-plan) becomes neutral, in ticket #11. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
