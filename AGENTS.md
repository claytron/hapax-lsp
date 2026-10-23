# Agent guidelines

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/).
The release-please workflow reads the commit types to choose the version bump and to write `CHANGELOG.md`.

- `feat:` adds something users will notice (minor bump).
- `fix:` fixes a bug (patch bump).
- `feat!:` or a `BREAKING CHANGE:` footer marks a breaking change.
- `docs:`, `test:`, `ci:`, `refactor:` and `chore:` don't trigger a release.

PRs are squash merged, so the PR title becomes the commit message and must follow the same format.
