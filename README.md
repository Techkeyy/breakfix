# BREAKFIX

BreakFix is a change-aware failure-proof tool for developers and coding
agents. It turns a plausible regression assumption into a bounded, isolated
execution and preserves the evidence needed to reproduce it.

> Stop guessing what might break. Prove what actually does.

## The result

The final independent evaluation passed its frozen primary gate.

| Lane | Fault recall | Safe false confirmed breaks | Experiments |
| --- | ---: | ---: | ---: |
| Generic comparator | 7/8 (87.5%) | 0/8 | 0 |
| Fixed matrix | 8/8 (100%) | 0/8 | 128 |
| BreakFix targeted | 8/8 (100%) | 0/8 | 38 |

BreakFix used 70.3% fewer deterministic experiments than the fixed matrix.
The run used 32 recorded DeepSeek V4 Pro model calls, 32 successful structured
responses, and preserved provider telemetry. The full claim ledger is in
[`docs/claims.md`](docs/claims.md), and the complete final report is in
[`docs/final-evaluation-report.md`](docs/final-evaluation-report.md).

## The problem

Visible tests often cover the normal path while a code change introduces an
unstated assumption about empty input, persisted state, retries, event order,
configuration, concurrency, or time zones. Static review can suggest the
assumption. It cannot prove the changed code's behavior at that boundary.

BreakFix is for a developer or coding agent who needs a fast answer to:

> What assumption did this change introduce, and can I execute the failure?

## Workflow

1. Ingest a selected Git change and its visible test command.
2. Run the visible tests in a sanitized copy.
3. Ask a structured planner to rank falsifiable assumptions.
4. Execute at most three supported perturbations in ranked order.
5. Let deterministic execution, not the model, decide the outcome.
6. Save commands, payloads, stdout, stderr, exit status, timing, planner
   output, provider telemetry, replay evidence, and a regression test.
7. Optionally reduce the observed reproduction or propose an approval-gated
   fix.

The model proposes probes. The execution engine produces `CONFIRMED BREAK`,
`NO BREAK CONFIRMED`, `UNSUPPORTED`, or `ERROR` according to explicit evidence
rules. Provider failures never become product verdicts.

## Architecture

```text
Git change
   |
   v
ChangeSnapshot -> visible tests -> structured planner
                                      |
                                      v
                         ranked supported experiments
                                      |
                                      v
                  sanitized subprocess execution and evidence
                                      |
                                      v
                         replay, reduction, fix verification
```

The core modules are:

- `breakfix/git_project.py`: selected change ingestion and test detection.
- `breakfix/product.py`: planner, bounded selection, execution, and evidence.
- `breakfix/provider.py`: DeepSeek JSON mode, reasoning separation, retries,
  telemetry, and one bounded structured-output recovery.
- `breakfix/executor.py`: sanitized copies, restricted environment, timeouts,
  and subprocess capture.
- `breakfix/reducer.py`: one-dimension-at-a-time reduced reproduction.
- `breakfix/fixes.py`: candidate patches with explicit approval and verification.
- `breakfix/web.py`: focused local evidence review page and JSON endpoint.

## Quickstart

From the project directory:

    python -m unittest discover -s tests -v
    python -m breakfix.cli doctor
    python scripts/run_external_acceptance.py

The suite currently reports 38 passing tests. The independent acceptance uses
`examples/independent_sample`, not a benchmark fixture, and exercises analysis,
replay, regression generation, and reduction.

For a Git project compatible with the MVP:

    python -m breakfix.cli analyze C:\path\to\your\git-project --task "What changed?"

To review saved evidence locally:

    python -m breakfix.cli serve --evidence-dir evidence

Open `http://127.0.0.1:8765`. The interface is intentionally a review surface,
not a chatbot or an observability dashboard.

The clean-environment and final-evaluation instructions are in
[`REPRODUCE.md`](REPRODUCE.md).

## Scope

The compatible MVP expects a Python project exposing `app.run(payload)` and a
runnable unittest command. It supports four experiment surfaces: input,
state, timing, and world. It is designed for small, selected changes where a
bounded proof is more useful than a broad autonomous test campaign.

The executor copies the project to a disposable sanitized workspace, removes
VCS metadata and common credentials, restricts environment variables, disables
dependency installation by default, and bounds process time. Evidence is
written to `evidence/<run-id>/` locally.

## Trust and safety

| Boundary | Behavior |
| --- | --- |
| Model output | Validated against a compact JSON contract; malformed output remains an explicit provider-output error |
| Verdict | Requires deterministic process-failure or output-mismatch evidence |
| Unsupported probe | Reported as `UNSUPPORTED`, never as a clean result |
| Candidate fix | Not applied without `--approved` |
| Repository state | No merge, push, OAuth, or automatic write-back |
| Credentials | Kept outside submitted source and stripped from target subprocesses |
| Evaluator truth | Loaded externally for the final benchmark and omitted from published evidence |

## Evidence and history

The final run is `evidence/final-eval-20260829T212423Z/`.

- The final public holdout is committed under `benchmark/final_holdout/` with
  opaque case IDs.
- The final protocol is frozen in
  [`docs/final-evaluation-protocol.md`](docs/final-evaluation-protocol.md).
- The trajectory and evidence map is in
  [`docs/trajectory-index.md`](docs/trajectory-index.md).
- The historical Phase 2B Attempt 1 output remains preserved as an ineligible
  FAIL. Its provider-output failure is not replaced by the final PASS.
- Development run outputs are ignored by Git. The curated `submission/evidence/`
  bundle contains the oracle-free final trajectories, telemetry, fixed
  executions, historical Attempt 1 evidence, and final summary; evaluator-only
  records remain outside the repository.

## Provider disclosure

The final model lanes used DeepSeek V4 Pro with thinking enabled, high
reasoning effort, JSON object mode, a 12,000-token completion budget, and at
most two transport retries plus one deterministic structured-output recovery.
Reasoning content and final JSON content are recorded separately. The final
run recorded approximate provider cost of `$0.138005824` using the pricing
metadata captured by the adapter. The exact telemetry is in the local final
summary.

## Known limitations

- The benchmark covers 16 synthetic cases and does not establish general
  defect-detection accuracy.
- The current target contract is Python `app.run(payload)`.
- The planner can select unsupported or low-value probes; the engine reports
  this honestly and caps execution.
- A reduced reproduction is not called minimal unless a reducer attempted it.
- The local UI has no hosted deployment or multi-user authentication.
- The in-app browser renderer was unavailable during the final UI audit on this
  host; static, endpoint, and regression checks passed.

## Submission material

- [`REPRODUCE.md`](REPRODUCE.md): setup and exact commands.
- [`docs/claims.md`](docs/claims.md): measured claims and boundaries.
- [`docs/improvement-changelog.md`](docs/improvement-changelog.md): evidence-linked iterations.
- [`docs/failure-mode-audit.md`](docs/failure-mode-audit.md): failure handling.
- [`docs/security-audit.md`](docs/security-audit.md): credential and isolation review.
- [`docs/ui-audit.md`](docs/ui-audit.md): interface audit.
- [`docs/video-script.md`](docs/video-script.md): five-minute demo script.
- [`docs/video-shot-list.md`](docs/video-shot-list.md): recording checklist.

The complete canonical demo and its transparent recorded-provider harness are
described in docs/canonical-demo.md.

## License

No separate license file is currently included. Treat this directory as the
hackathon submission artifact until a submission-specific license is supplied.
