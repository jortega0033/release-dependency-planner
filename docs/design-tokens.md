# Design tokens

The UI uses the Pipenzo "Flow look" tokens: black page, Flow-style alpha layers, one accent (Pipenzo yellow `#FECE02`), red only for danger.

- Source: `jortega0033/clip-to-reel-studio`, `extension/sidepanel/tokens.css`, commit `a13378ce73e5b27213c9a200fc960ec93afef054` (2026-11-21).
- Copy here: `release_planner/static/tokens.css`, served at `/static/tokens.css` and linked before `app.css`. Do not edit it.
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

Yellow is for the primary action and the current-step marker only. Text never sits on a bare alpha layer.

## Light and dark

Dark is the primary design. `tokens.css` defines the matching light theme in `:root` and switches to dark inside the `prefers-color-scheme: dark` media query, so the operating system colour scheme decides. There is no manual switch.
