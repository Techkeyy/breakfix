# Reproduce BreakFix

BreakFix is a Python 3.11 or newer, standard-library prototype. The shipped
package has no runtime dependency installation step.

## Offline product checks

From `C:\Users\HomePC\Desktop\BreakFix`:

    python -m unittest discover -s tests -v
    python -m breakfix.cli doctor
    python scripts/run_external_acceptance.py

The test suite should report 38 passing tests. The independent acceptance
script uses `examples/independent_sample` and records a confirmed process
failure, a generated regression, and a bounded reduction without benchmark
fixture mappings.

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

The preserved final run used 32 model completion calls and 128 deterministic
fixed-matrix experiments. Its oracle-free evidence is under
`evidence/final-eval-20260829T212423Z/`; its full evaluator workspace is kept
outside the repository under the local Temp directory named in the run log.

## Scope and safety

The compatible MVP expects a Git project with a Python `app.run(payload)`
entrypoint and a runnable unittest command. Execution occurs in sanitized
temporary copies with common credentials, VCS metadata, caches, and dependency
directories excluded. Candidate fixes require explicit `--approved` before
application and are verified on a separate snapshot. No merge, push, GitHub
OAuth, dependency installation, or automatic write-back is performed.
