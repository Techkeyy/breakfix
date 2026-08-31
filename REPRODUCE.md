# Reproduce BreakFix

BreakFix is a Python 3.11 or newer, standard-library prototype. The shipped
package has no runtime dependency installation step.

## Fresh setup

On a clean machine:

    git clone <repository-or-archive>
    cd BreakFix
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e .

The editable install has no runtime dependencies. If the environment already
runs source checkouts directly, the install can be omitted; all commands below
are still source-based and use only the standard library.

For a live final evaluation, configure the provider without committing the
credential:

    $env:BREAKFIX_PROVIDER = "deepseek"
    $env:BREAKFIX_DEEPSEEK_API_KEY = "<your-key>"
    $env:BREAKFIX_MODEL = "deepseek-v4-pro"
    $env:BREAKFIX_REASONING_EFFORT = "high"
    $env:BREAKFIX_MAX_OUTPUT_TOKENS = "12000"

## Offline product checks

From `C:\Users\HomePC\Desktop\BreakFix`:

    python -m unittest discover -s tests -v
    python -m breakfix.cli doctor
    python scripts/run_external_acceptance.py

The test suite should report 44 passing tests. The independent acceptance
script uses `examples/independent_sample` and records a confirmed process
failure, a generated regression, and a bounded reduction without benchmark
fixture mappings.

For the complete canonical demo, including the fix loop:

    python scripts/run_canonical_demo.py

The expected terminal result ends with VERIFIED. The command uses transparent
recorded provider doubles for deterministic recording; it does not alter the
product or spend a live-provider call. Typical runtime is under one minute.

To replay the final run's first confirmed trajectory when the local evidence
bundle and evaluator workspace are present:

    python -m breakfix.cli reproduce evidence/final-eval-20260829T212423Z/trajectories/breakfix/q1a
    python -m breakfix.cli reduce evidence/final-eval-20260829T212423Z/trajectories/breakfix/q1a

To inspect the local evidence page:

    python -m breakfix.cli serve --evidence-dir evidence

Open `http://127.0.0.1:8765`. The page is a focused evidence review surface,
not a chatbot or dashboard.

## Final evaluation rerun

The final holdout is public, but the evaluator truth file is intentionally
external. A rerun requires an explicitly authorized DeepSeek credential and
the exact external truth file supplied to the evaluator:

    $env:BREAKFIX_PROVIDER = "deepseek"
    $env:BREAKFIX_MODEL = "deepseek-v4-pro"
    $env:BREAKFIX_REASONING_EFFORT = "high"
    $env:BREAKFIX_MAX_OUTPUT_TOKENS = "12000"
    python scripts/run_final_evaluation.py --truth-path C:\path\outside\workspace\final-truth.json

The runner enforces the frozen provider configuration, creates a `.git`-free
evaluation copy, executes the generic and BreakFix live lanes, runs the fixed
8-experiment matrix, and writes raw oracle-bearing records outside the
published evidence directory. It must not be used to tune prompts or rerun
individual cases after the holdout is opened.

The preserved historical pre-hardening valid run used 32 model completion calls
and 128 deterministic fixed-matrix experiments. Its oracle-free evidence is under
`evidence/final-eval-20260829T212423Z/`; its full evaluator workspace is kept
outside the repository under the local Temp directory named in the run log.

The later hardened final-fresh evaluation was permanently failed before a
valid gate. The latest definitive attempt preserved 32 logical requests: 16
successful model responses and 16 HTTP 402 `Insufficient Balance`
transport/provider failures. BreakFix and the generic comparator were
ineligible, so its apparent BreakFix 2/8 is not a product-performance result.

The live baseline is the generic comparator lane inside the same frozen runner.
It receives the same public case context, has no hidden probes, and is scored
against the external evaluator truth only after its output is recorded.

Historical Phase 1 and Phase 2A research replays are optional and are not part
of the public benchmark path. If authorized private evaluator files are
available, set `BREAKFIX_GROUND_TRUTH_PATH` for Phase 1/1.5 and
`BREAKFIX_PHASE2A_TRUTH_PATH` for Phase 2A. The files must remain outside the
repository and published evidence.

## Expected runtime and cost

- Offline test suite: about 65 seconds, 93 tests on the recorded host.
- Canonical demo: under one minute.
- Final live evaluation: about 25 minutes on the recorded host, depending on
  provider latency.
- Final recorded provider cost: approximately $0.138 for 32 model calls.
- The fixed matrix itself is local deterministic execution and has no provider
  cost.

## Scope and safety

The compatible MVP expects a Git project with a Python `app.run(payload)`
entrypoint and a runnable unittest command. Execution occurs in sanitized
temporary copies with common credentials, VCS metadata, caches, and dependency
directories excluded. Candidate fixes require explicit `--approved` before
application and are verified on a separate snapshot. No merge, push, GitHub
OAuth, dependency installation, or automatic write-back is performed.

## Troubleshooting

- If the doctor reports a missing provider credential, set the environment
  variable in the current shell and do not put it in a tracked file.
- If the final runner rejects configuration, use DeepSeek, model
  deepseek-v4-pro, high reasoning effort, and a 12,000-token output budget.
- If port 8765 is busy, pass another port to the breakfix serve command.
- If replay cannot find the evaluator workspace, keep the matching local Temp
  directory beside the published evidence bundle; replay is intentionally
  evidence-based.
- Do not place the external evaluator truth file under the repository, the
  history-free evaluation workspace, or the published evidence directory.
