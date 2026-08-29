# Video shot list, target 4:50

The recording must use actual terminal output, saved evidence, and the local
review page. It must not type or display a result that was not produced by the
product or the recorded evaluation.

| Duration | Screen/application | Exact action | Expected output | Narration | Evidence source |
| --- | --- | --- | --- | --- | --- |
| 0:00-0:25 | Editor and terminal | Show the before/after change, then run its visible tests | Visible tests pass | “Your tests check what you expected. BreakFix tests what you forgot to expect.” | `evidence/canonical-demo-20260829T223714Z/` |
| 0:25-0:45 | Terminal or evidence viewer | Display the generic comparator prompt and saved JSON response | A reasoning-only recommendation, with no hidden probe execution | “The baseline can name a risk, but it does not execute hidden probes.” | `evidence/final-eval-20260829T212423Z/trajectories/baseline/` |
| 0:45-1:15 | Terminal and local evidence page | Run `python scripts/run_canonical_demo.py`; open the indexed local review page | Canonical run appears with visible tests passing | “This is the selected change and the real saved run.” | `scripts/run_canonical_demo.py`; `docs/canonical-demo.md` |
| 1:15-1:45 | Terminal or evidence viewer | Open planner output and selected experiment record | Ranked `input_empty` assumption and one supported perturbation | “The planner proposes what to attack. The engine decides.” | `evidence/canonical-demo-20260829T223714Z/analysis.json` |
| 1:45-2:30 | Terminal and evidence viewer | Open execution and replay records | Command, payload, stdout, stderr, timing, `CONFIRMED BREAK`, replay, regression | “The break is a deterministic mismatch or process failure, not a model assertion.” | `evidence/canonical-demo-20260829T223714Z/` |
| 2:30-3:25 | Terminal and evidence viewer | Open proposal, approval, application, and verification records | Approval required, approved application, after-fix pass, `VERIFIED` | “Candidate fixes cross an explicit human approval boundary.” | `evidence/canonical-demo-20260829T223714Z/fix/` |
| 3:25-4:10 | Local evidence page and JSON viewer | Open the final summary and trajectory index | PASS, 8/8 faults, 0/8 safe false confirmations, 38 versus 128, 32 calls | “The final holdout supports a 70.3% targeted-execution reduction.” | `evidence/final-eval-20260829T212423Z/final-summary.json`; `docs/trajectory-index.md` |
| 4:10-4:35 | Editor | Open the improvement changelog at Attempt 1, recovery, and final evaluation | Historical FAIL and recovery are both visible | “The failed provider run remains preserved; the frozen evaluation rules did not change.” | `docs/improvement-changelog.md` |
| 4:35-4:50 | Editor and terminal | Open `REPRODUCE.md`, then show the oracle-free final evidence directory | Scope and clean-environment commands are visible | “Stop guessing what might break. Prove what actually does.” | `REPRODUCE.md`; final evidence bundle |
