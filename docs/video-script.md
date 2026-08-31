# BreakFix solution video script

Target length: 4:45

Hard maximum: 5:00

## Recording surface

Use the live application for the main demo:

https://breakfix.vercel.app

Use a clean browser window with bookmarks, personal tabs, credentials,
notifications, and developer tools hidden. Keep the local canonical demo ready
as a fallback only. Do not type or display a result that the product did not
produce.

## 0:00 to 0:20, problem

Show the live BreakFix homepage.

Say: “AI coding agents are already good at imagining what might go wrong. But a
warning is still only a hypothesis.”

## 0:20 to 0:42, product

Keep the hero and frozen evaluation strip visible.

Say: “BreakFix reads the actual change, finds the assumptions worth attacking,
and executes targeted experiments against them.”

Click **Analyze a change**.

## 0:42 to 1:20, start a real run

Use the canonical demo option and submit the public BreakFix repository. Show
the real job transition from `QUEUED` to `RUNNING`.

Say: “The model proposes probes. Deterministic execution decides what actually
happened.”

## 1:20 to 1:55, assumptions and experiment

When the real result loads, show the ranked `input_empty` assumption and the
targeted experiment. Point out the expected behavior, actual process result,
evidence state, and returned output.

Say: “This is not a generic warning. It is a specific assumption tied to a
specific execution.”

## 1:55 to 2:35, confirmed break

Show `CONFIRMED BREAK`, the provider status, experiment count, regression status,
and the expected versus actual evidence. Show the real reproduction and
regression evidence available in the result.

Say: “When an assumption fails, BreakFix does not just tell you something might
break. It gives you the reproduction, regression test, and evidence.”

## 2:35 to 3:25, fix and approval

Select **Propose fix** in the live result. Wait for the real proposal to load.
Show the patch, changed files, tests to run, and the human approval notice.

Say: “It proposes a fix, but waits for human approval before applying it.”

Select **Approve & verify** only at the explicit recording checkpoint. Show the
job's approved state. Then select **Run verification** and show the real
verification result.

Say: “Then it replays the exact failure and original tests before marking the
fix verified.”

## 3:25 to 3:48, evaluation shot

Switch to a clean, uncluttered evaluation visual titled `PRE-HARDENING FROZEN EVALUATION`.
Show only:

```text
8/8       seeded faults confirmed
0/8       safe false confirmations
38        targeted experiments
128       matrix experiments
70.3%     fewer experiments
```

Say: “On the frozen pre-hardening holdout, the then-current BreakFix confirmed
8/8 seeded faults with 0/8 safe false confirmations, using 38 targeted
experiments versus 128 fixed-matrix experiments.”

## 3:48 to 4:12, measured iteration

Show the improvement changelog briefly.

Say: “The strong coding agent already found the raw faults. A broad
safety-certification framing failed. The first Phase 2B run failed because our
2,000-token adapter truncated every advanced planner output. We preserved those
failures. The final thesis became targeted, evidence-efficient falsification,
and the historical pre-hardening independent holdout passed. The later
hardened evaluation attempts were preserved as ineligible, including a
definitive provider run with HTTP 402 insufficient-balance failures.”

Do not open private evaluator truth, API keys, or raw credentials.

## 4:12 to 4:45, close

Show `REPRODUCE.md` and the public repository link.

Say: “As coding agents get better at imagining failures, generating more
suspicions stops being the hard part. The bottleneck becomes deciding which
suspicions are worth executing and proving which failures are real.”

End on the live URL and say: “Stop guessing what might break. Prove what
actually does.”

## Rehearsal record

Before recording, run this exact sequence once against the live app and record
the approximate times in `docs/video-shot-list.md`. The rehearsal must use the
real API and real evidence. The local canonical demo is the deterministic
fallback when a live provider or network failure makes the hosted run
unavailable.

The final rehearsal reached `CONFIRMED BREAK` at about 0:53, showed the real
proposal at about 1:41, reached `APPROVED` at about 1:59, and reached `VERIFIED`
at about 2:06. The final recording should use cuts and narration to stay within
4:30 to 4:50.
