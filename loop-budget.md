# Loop Budget: release-dependency-planner

> Primary loop: **Issue Triage** (scaffolded by loop-init). Manual runs only; no scheduler is configured.

## Daily limits

| Loop | Max runs/day | Max tokens/day | Max sub-agent spawns/run |
|------|--------------|----------------|--------------------------|
| Issue Triage | 2 (manual) | 80k | 0 (L1) |

## On budget exceed

1. Stop. There is no scheduler to pause; do not start another run that day.
2. Append the event to `loop-run-log.md`.
3. Tell the human in the run output and under "Needs human" in `issue-triage-state.md`.

## Kill switch

- Flag: a line reading `loop-pause-all` under "Alerts This Period" below. When present, every loop skill exits immediately.
- Only a human removes the flag.

## Alerts This Period

- (none)

## Estimate spend

```bash
npx @cobusgreyling/loop-cost --pattern issue-triage
```
