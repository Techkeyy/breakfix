# Security audit

Audit date: 2026-08-29

## Credential and repository checks

- Required DeepSeek credential presence was confirmed without printing its
  value.
- No tracked `.env`, private-key, certificate, or credential files were found.
- A tracked-file scan found no bearer-token, private-key, or API-key value
  patterns.
- `.env` and common key/certificate suffixes are ignored by Git.
- Runtime subprocesses receive a restricted environment. Provider credentials
  are not passed to the target project process.

## Evaluation isolation

- The final evaluation copied the current `breakfix` source and public holdout
  into a `.git`-free Temp workspace.
- The truth file was loaded from outside both the workspace and published
  evidence roots.
- Public holdout labels and truth-file references passed the pre-run leakage
  audit.
- The first publication pass was corrected after audit found evaluator-only
  files in the public BreakFix copy. Those 16 files were removed from the
  published bundle; the raw evaluator copies remain in Temp. The publisher is
  now patched to exclude `evaluation.json` automatically.
- A post-cleanup scan found no `expected_outputs`, oracle, truth, or evaluator
  fields in the published final evidence.
- The curated `submission/evidence/` copy was scanned with the same oracle-field
  checks and is clean. The historical Phase 1 and Phase 2A truth files were
  removed from the release tree and rewritten history; private backup copies
  remain outside the repository for authorized historical replay.

## Product mutation boundaries

- Analysis runs in sanitized copies and writes evidence under a selected output
  directory.
- Candidate fixes are not applied unless the user supplies `--approved`.
- Verification uses a separate approved snapshot and never merges or pushes.
- Dependency installation, GitHub integration, OAuth, and automatic write-back
  are outside the product scope.
