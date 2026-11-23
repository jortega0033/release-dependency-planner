# Design tokens

The UI uses the Pipenzo "Flow look" tokens: black page, Flow-style alpha layers, one accent (Pipenzo yellow `#FECE02`), red only for danger.

- Source: `jortega0033/clip-to-reel-studio`, `extension/sidepanel/tokens.css`, commit `a13378ce73e5b27213c9a200fc960ec93afef054` (2026-11-21).
- Copy here: `release_planner/static/tokens.css`, served at `/static/tokens.css` and linked before `app.css`. A ticket that creates a page or its static allowlist links `tokens.css` before any other stylesheet and serves it (allowlist and its test) (D4). Do not edit it.
- Resync: copy the source file over `release_planner/static/tokens.css`. Nothing else.
- Rule: new UI uses these tokens; no new colour literals in `app.css` or `app.js`.

## Token names by role

| Role | Tokens |
|---|---|
| Surfaces | `--bg`, `--bg-raised`, `--surface`, `--bg-sunken` |
| Text | `--fg`, `--muted`, `--faint` |
| Lines | `--border`, `--hairline`, `--control-border`, `--input-border` |
| Accent | `--primary`, `--primary-press`, `--primary-edge`, `--on-primary` |
| Status | `--danger`, `--danger-bg`, `--success`, `--ok`, `--ok-bg`, `--warn-fg`, `--warn-bg`, `--info` |
| Focus | `--focus` |
| Hero and dark block | `--hero-*`, `--on-hero*`, `--ink`, `--on-ink*`, `--ink-border` |
| Layers and shadows | `--glass*`, `--scrim`, `--state-hover`, `--state-selected`, `--btn-secondary*`, `--shadow-*` |
| Type, space, shape, motion | `--font`, `--font-display`, `--mono`, `--space-1..7`, `--radius-*`, `--dur-*`, `--ease-*` |

Text never sits on a bare alpha layer.

## Accent and selection rules

These rules take precedence over the header comment of `tokens.css`. That comment is narrower: it lists yellow only for the primary button, the current-step node, the "your turn" chip and two dots, and does not mention selection. The copy of `tokens.css` must stay identical to the source, so the comment is not edited here.

- **Current selection (D1).** The yellow accent is used for the primary action, the current-step marker and the current selection (UI rule 8). The owner decided this on 2026-11-23. How a selection is drawn is a recommendation by the orchestrator, adopted under the owner's delegation of the same day: a solid `--primary` fill with `--on-primary` text, not only a yellow border (a yellow border has about 1.5:1 against white on light). A second sign that is not colour is required (weight, icon or text), together with the existing aria attribute. Never a tint with a same-hue border, and never a thick one-sided border.
- **Focus ring (D2).** `--focus` is a focus indicator and is exempt from the accent limit, including where it is yellow in the dark block. A ticket that says the focus style stays unchanged means the rule on main after the token pull request. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
- **Both themes (D3).** Contrast and no-colour-alone checks cover both the light and the dark block of `tokens.css`. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.

Status of the page: where `app.css` still marks a selection in a neutral colour, the page follows in ticket work. That change is not done yet.

## Light and dark

Dark is the primary design. `tokens.css` defines the matching light theme in `:root` and switches to dark inside the `prefers-color-scheme: dark` media query, so the operating system colour scheme decides. There is no manual switch. Checks run against both blocks (D3).

## Known deviation (ticket #11)

While a plan is open, `#new-plan` (sidebar) and `#save-plan` (editor) both carry `.btn-primary`, so two yellow fills show together. Only one yellow primary button may show per screen. Decided (D5, recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23): while a plan is open only one yellow primary button shows, and `#new-plan` becomes neutral. This needs a markup or class change, which is outside this colour-only chore. Not done yet; it is made in ticket #11.
