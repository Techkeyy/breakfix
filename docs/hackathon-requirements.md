# micro1 Frontier Engineering Challenge 2026 requirements

Research date: 2026-08-29. Local timezone: Africa/Lagos. Statuses in this
document are Confirmed, Inferred, or Unknown. The HackerEarth challenge page is
the primary source. The page links an official instruction PDF, but the PDF
request was blocked by the browser and network layer in this environment, so
requirements that depend on that PDF remain Unknown.

Primary source:
https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/

Official instruction link exposed on that page:
https://uc.hackerearth.com/he-public-ap-south-1/micro1%20-%20First%20Hackathon97ce7c5.pdf

## Requirement matrix

| Official requirement | Source | BreakFix implementation | Evidence | Status |
| --- | --- | --- | --- | --- |
| Online challenge | HackerEarth challenge page, Overview | Local-first CLI and evidence bundle; no deployment claimed | README and run output | Confirmed |
| Individual entry, team size 1 | Challenge page, header and FAQ | Project scope is one participant and one canonical directory | This checkpoint | Confirmed |
| Challenge window Aug 28 to Aug 31, 2026 | Challenge page, header | Work is timestamped in evidence run IDs | evidence/phase1-20260829T104633Z | Confirmed |
| Kickoff at Aug 28, 15:00 UTC | Challenge page, Overview | Not encoded as a product deadline | This document | Confirmed |
| End at Aug 31, 18:00 UTC | Challenge page, Overview | Not encoded as a product deadline | This document | Confirmed |
| Free and global, subject to legal restrictions | Challenge page, Overview and Eligibility | No paid service or restricted data required for Phase 1 | Standard-library prototype | Confirmed |
| At least 18 years old | Challenge page, Eligibility | Participant responsibility, not a software gate | Submission checklist still needed | Confirmed |
| Six months practical software-building experience or equivalent | Challenge page, Eligibility | Participant responsibility, not a software gate | Submission checklist still needed | Confirmed |
| One registration and one final submission | Challenge page, Eligibility | No submission automation built | Submission work remains | Confirmed |
| Coding-agent use is required | Challenge page, Overview and FAQ | Agent-shaped baseline and BreakFix traces are instrumented, but the baseline is offline and not a live coding model | evidence/.../trajectory.json; integrity.live_model_used=false | Confirmed requirement, implementation incomplete |
| Disclose tools used | Challenge page, Overview and FAQ | README and docs name the local prototype and limitations | README; docs | Confirmed |
| Submit representative trajectories for every agent used | Challenge page, Submission Package and FAQ | Baseline and BreakFix trajectory.json files capture instructions, context, tool calls, outputs, and the no-ground-truth boundary | evidence/.../baseline/*/trajectory.json; evidence/.../breakfix/*/trajectory.json | Confirmed requirement, Phase 1 instrumented |
| Complete solution code | Challenge page, Submission Package | Source, benchmark, tests, and runner are present | canonical project directory | Confirmed for Phase 1 |
| Improvement changelog with evidence-linked iterations | Challenge page, Submission Package | Changelog records the baseline, matrix, planner miss, timeout fix, and final rerun | docs/improvement-changelog.md | Confirmed for this checkpoint |
| Clean-environment reproduction guide | Challenge page, Submission Package | README gives local commands; clean-machine validation is not complete | README; build plan | Inferred implementation, not submission-complete |
| Exact commands for solution, baseline, and evaluation | Challenge page, Submission Package | One Phase 1 command runs all three lanes; live model baseline command does not exist yet | README; scripts/run_phase1.py | Partially confirmed |
| Versions, approximate runtime, and cost | Challenge page, Submission Package | Python version and per-process durations are recorded; model cost is not applicable because no model was called | evidence execution results; cost field absent | Partially confirmed |
| Solution video up to 5 minutes | Challenge page, Submission Package | No video produced in Phase 1 | Video remains future work | Confirmed requirement, not started |
| Video begins with problem and simple baseline | Challenge page, Submission Package | Not started | Video remains future work | Confirmed requirement, not started |
| Video shows realistic execution, comparison, changelog, strongest change, and removed experiment | Challenge page, Submission Package | Evidence and changelog exist for a future recording | docs/improvement-changelog.md; evidence | Confirmed requirement, not started |
| Correct, reproducible, testable, clearly explained solution | Challenge page, Overview | Standard-library runner, unit tests, five controlled cases, evidence, and docs | test run; evidence bundle | Confirmed objective, provisional evidence |
| Baseline plus advanced solution with meaningful improvement | Challenge page, Theme | Fixed matrix and targeted BreakFix are implemented; baseline is an offline surrogate, not a comparable live agent | evidence comparison.json | Confirmed requirement, not fully satisfied |
| Allowed languages include Python, TypeScript, Java, C++, Go, Rust | Challenge page, Theme and FAQ | Python 3.14 prototype | pyproject.toml; environment check | Confirmed |
| Final problem PDF may prescribe runtime, dependency, API, and acceptance-test constraints | Challenge page, Theme | No PDF constraints could be read in this environment | blocked PDF URL | Unknown |
| Valid submission must be timely, complete, original, policy compliant, reproducible, and include repository/archive, tests, README, agent evidence, and video | Challenge page, FAQ | Repository, tests, README, evidence, and traces exist; archive, final form, and video do not | current tree | Partially confirmed |
| Consequential actions controlled by sandbox or simulation, with human approval | Challenge page, Rule Book | Phase 1 only runs synthetic sample code locally; it has no write-back or merge action and documents local execution limits | docs/assumptions-and-risks.md | Confirmed requirement, Phase 1 boundary |
| Qualified human reviewer for significant effects | Challenge page, Rule Book | No consequential action exists in Phase 1 | build plan; non-goals | Confirmed requirement, not yet applicable |
| Use legal, ethical, permitted data and keep credentials outside submission | Challenge page, Rule Book | Synthetic benchmark and secret-free source; .env is ignored | .gitignore; benchmark | Confirmed for Phase 1 |
| Every result claim connected to evidence | Challenge page, Rule Book | Comparison metrics point to per-lane evidence directories | evidence/phase1-20260829T104633Z/comparison.json | Confirmed for Phase 1 |
| Judges must be able to run and reproduce the main result | Challenge page, Rule Book | Local commands and offline fixtures are provided; fresh-machine validation remains open | README; build plan | Partially confirmed |
| micro1 may own submissions and use them for AI training and evaluation | Challenge page, Rule Book | No code action; recorded as an ownership consideration before public submission | this matrix | Confirmed |
| Scoring criteria and weights | Challenge page, Evaluation Criteria | Tie-break order is recorded below; no percentage weights were visible in the authoritative page snapshot | page content inspected on 2026-08-29 | Unknown |
| Tie-break order: Agent Solution and Engineering, Reproducibility, Measured Improvement, End to End Quality, final evidence review | Challenge page, Evaluation Criteria | Build plan prioritizes these gates | docs/build-plan.md | Confirmed |
| Prize amounts by award | Challenge page, Prizes & Awards | Total cash pool is recorded; individual award split is not encoded | page content inspected on 2026-08-29 | Unknown |
| API keys or model credits supplied by organizer | Challenge page, FAQ | Prototype uses no external model; future live baseline must use participant-owned setup | README | Confirmed: organizer says no |
| Registration/submission intake fields, archive format, exact acceptance tests, and final PDF constraints | Official instruction PDF link | Not implemented until the PDF can be read and the final form is rechecked | blocked URL and open verification queue | Unknown |

## Official facts used for this checkpoint

The challenge is online and individual-only. Coding-agent use is required.
The entry must contain a baseline and an advanced solution with meaningful
improvement, complete code, a changelog, a reproduction guide, a video of no
more than five minutes, and representative agent trajectories. The rule book
requires evidence-backed claims, safe handling of consequential actions, human
review where effects are significant, permitted data, and credentials kept
outside the submission.

No percentage scoring weights are asserted here because none were visible in
the authoritative page content that was inspected. The PDF and submission form
must be rechecked before a final submission.

## Open verification queue

1. Obtain and read the official instruction PDF, including starter materials,
   constraints, and acceptance tests.
2. Recheck the live Evaluation Criteria tab for weights or a later rubric.
3. Recheck the final submission form fields and archive limits.
4. Replace the offline baseline surrogate with a comparable live coding-agent
   review and preserve its prompt, model, tool list, runtime, and cost.
5. Verify whether any policy requires a public repository, and record the exact
   archive format.

