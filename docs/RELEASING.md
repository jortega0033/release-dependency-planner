# Releasing

A release here is a Git tag on `main`. The project has no package, no installer and no version string in code, so there is nothing to publish. Only the owner releases.

## Before tagging

1. `main` is green in CI on both platforms (the `test` job).
2. `python -m unittest discover -s tests -v` passes locally; note the test count.
3. The browser flow in PRD section 10 was run once on the commit to be tagged, with external requests blocked (the release gate ticket, issue #7, owns the written script).
4. `CHANGELOG.md`: rename `Unreleased` to the version and date, and add a fresh empty `Unreleased` section.
5. `README.md` and the PRD match the behaviour on `main`.

## Tagging

The owner creates an annotated tag on the release commit, for example `git tag -a v0.2.0 -m "v0.2.0"`, and pushes the tag. Agents do not tag, push tags or create GitHub releases.

## After tagging

Check that the tagged commit has the expected CHANGELOG section and that CI is green on it.
