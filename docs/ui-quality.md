# UI quality rules

These ten rules are binding for every screen and every piece of user-facing text in this repository. The owner approved them on 2026-11-22 (see [owner-decisions.md](owner-decisions.md)). They apply to `release_planner/static/` (HTML, CSS and JavaScript).

1. No thick accent border on one side of a card, callout, alert, list item or quote (for example `border-left: 4px solid <accent>`). Use spacing, type weight, an icon or a full hairline border instead.
2. No soft tinted background with a thin border of the same hue as the default way to mark a status, tag, callout or card. One neutral surface and one clear signal (text, icon or a solid chip) is enough.
3. No gradient text and no purple-to-blue gradient as a default accent.
4. No blur or glass panels, and no drop shadow plus large radius on every card.
5. No emoji used as icons or bullets, and no sparkle marks.
6. No pill or badge on things that are not states. No all-caps, letter-spaced micro labels as section decoration.
7. No centred hero with a slogan in an application screen. Screens open on the user's task.
8. One accent colour, used for the primary action and the current selection. Status colours only for status.
9. Dense, aligned layouts on a consistent spacing scale. No card grid where a table or a list is the right form.
10. User-facing copy is plain and specific: no filler, no exclamation marks, and the same word for the same thing everywhere.

## How the rules are applied

- A UI ticket starts with the `ui-ux-pro-max` skill (`.claude/skills/ui-ux-pro-max/`): a design-system search for the product type before any markup or CSS is written.
- A UI ticket ends with a check of every changed screen against this file. The result goes in the pull request under Evidence.
- User-facing copy, documentation and pull request text go through the `unslop` skill (`.claude/skills/unslop/`) before the pull request is opened.
- Enforcement is by the review gate: Code Reviewer checks every ticket against this file. No script enforces it. Rule 1 can be linted; rule 2 cannot be detected reliably from CSS.
- These rules sit next to the accessibility requirements in PRD section 1.5 and the hard constraints in `CLAUDE.md` (no external requests, no inline style or script, no `innerHTML` family). They do not replace them.
- Colours, radii, spacing and motion come from `release_planner/static/tokens.css`; see [design-tokens.md](design-tokens.md). New UI uses those tokens and adds no colour literal.
