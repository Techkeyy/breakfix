# Five-minute solution video script

## 0:00 to 0:35: problem

Show a small code change whose visible tests pass. Explain that ordinary review
can identify a plausible assumption but cannot prove what happens at the
boundary the change introduces.

## 0:35 to 1:20: baseline

Show the generic comparator prompt and its recommendation. Make clear that it
is reasoning only and does not get hidden probes.

## 1:20 to 2:20: BreakFix workflow

Open the local evidence page. Show the selected change, visible test result,
ranked assumptions, and the supported perturbation catalogue. Run an analysis
on the independent sample and show the isolated command, payload, stdout,
stderr, and process-failure result.

## 2:20 to 3:15: proof and regression

Show the generated regression test, replay, and bounded reduced reproduction.
Explain that the model proposes a probe but deterministic execution decides the
verdict.

## 3:15 to 4:15: measured improvement

Show the final frozen comparison: 8 of 8 faulty cases and 0 of 8 safe false
confirmations for BreakFix, 38 targeted experiments versus 128 fixed, and a
70.3125% reduction. Show the generic comparator's 7 of 8 fault recall as an
honest secondary result.

## 4:15 to 5:00: trust boundary and close

Show the approval gate for candidate fixes, the sanitized execution boundary,
provider recovery telemetry, and the oracle-free published evidence. Close
with the scope: Python `app.run(payload)`, four supported surfaces, no merge or
push, and reproducibility commands in `REPRODUCE.md`.
