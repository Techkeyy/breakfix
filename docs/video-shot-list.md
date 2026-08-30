# BreakFix video shot list

Target length: 4:45

Hard maximum: 5:00

The main demo uses the live application at
https://breakfix.vercel.app. All result screens must be produced by the live
product during the recording. The local canonical demo is a recording fallback,
not a pre-rendered replacement.

| Time | Surface | Exact action | Expected live output | Narration or note |
| --- | --- | --- | --- | --- |
| 0:00-0:20 | BreakFix homepage | Open `https://breakfix.vercel.app` in a clean browser window | Hero, product explanation, and frozen evaluation strip | “A warning is still only a hypothesis.” |
| 0:20-0:42 | BreakFix homepage | Hold on the hero, then point to the primary action | `Analyze a change` is visible | “BreakFix reads the actual change, finds the assumptions worth attacking, and executes targeted experiments.” |
| 0:42-1:20 | Live analysis | Click `Analyze a change`, choose `Use canonical demo`, and submit | Real repository input; `QUEUED`, then `RUNNING` | Do not type or display a result that was not returned by the API. |
| 1:20-1:55 | Live evidence | Wait for the run and show assumptions and targeted evidence | Ranked `input_empty`, one supported experiment, expected behavior, actual process, evidence state, and returned output | “The planner proposes what to attack. The engine decides.” |
| 1:55-2:35 | Live evidence | Hold on the result summary and evidence details | `CONFIRMED BREAK`, provider status, experiment count, regression status, expected versus actual | The result must be the current run, not a saved mock. |
| 2:35-3:25 | Live fix loop | Click `Propose fix`, wait for the proposal, show the patch and tests, then click `Approve & verify` at the explicit checkpoint | Fix proposal, human approval notice, `APPROVED`, then `Run verification` and final `VERIFIED` | Approval is a visible human decision. Never auto-approve. |
| 3:25-3:48 | Evaluation visual | Show a clean card titled `FINAL FROZEN HOLDOUT` | 8/8 faults confirmed; 0/8 safe false confirmations; 38 versus 128; 70.3% fewer; approximate cost `$0.138` | Keep this shot sparse. Do not show oracle files. |
| 3:48-4:12 | Improvement changelog | Open the Attempt 1 failure, provider recovery, and final evaluation entries | Failed experiment and measured recovery remain visible | Mention the 2,000-token truncation and preserved failure in one short passage. |
| 4:12-4:45 | Repository and reproduction | Show `REPRODUCE.md`, the public GitHub URL, then return to the live URL | Public scope, clean-environment commands, and final product close | End with “Stop guessing what might break. Prove what actually does.” |

## Recording checklist

- [ ] Clean browser window with personal tabs and bookmarks hidden.
- [ ] No API keys, provider credentials, VPS credentials, DuckDNS token, `.env`
      files, private paths, or evaluator oracle visible.
- [ ] Browser notifications disabled or hidden.
- [ ] Live homepage loads before recording.
- [ ] The live canonical demo reaches `COMPLETED` with `CONFIRMED BREAK`.
- [ ] Assumptions, targeted experiment, expected and actual evidence, and
      regression status are visible.
- [ ] The real fix proposal is visible before the approval click.
- [ ] Approval is an explicit human action.
- [ ] The live verification result reaches `VERIFIED`.
- [ ] The evaluation visual is separate from the product result and does not
      overcrowd the screen.
- [ ] Total recording remains between 4:30 and 4:50, never over 5:00.

## Evidence references

- Live product: `https://breakfix.vercel.app`
- Public source: `https://github.com/Techkeyy/breakfix`
- Local fallback: `scripts/run_canonical_demo.py`
- Final public evaluation evidence: `submission/evidence/final-eval-20260829T212423Z/`
- Canonical local fix evidence: `submission/evidence/canonical-demo-20260829T223714Z/`
- Improvement history: `docs/improvement-changelog.md`

## Live rehearsal timing

Rehearsed against the live application on 2026-08-30 in a clean 1440px browser
viewport. The actual technical path took approximately 2:06:

- 0:00 homepage and product explanation.
- 0:06 analysis submitted from the canonical demo.
- 0:53 `COMPLETED` with `CONFIRMED BREAK`, assumptions, targeted evidence, and
  valid regression status.
- 1:41 real fix proposal displayed with the approval gate.
- 1:59 explicit approval completed with `APPROVED` and `Run verification` shown.
- 2:06 verification completed with `VERIFIED`, visible tests passed, and
  regression passed.

The recording edit uses the 4:30 to 4:50 narrative timing above, with the live
wait states shortened only by cutting between real completed states.
