# micro1 Frontier Engineering Challenge 2026 requirements

Research date: 2026-08-29. Local timezone: Africa/Lagos. Statuses in this
document are Confirmed, Inferred, or Unknown. The HackerEarth challenge page is
the primary source. The linked instruction PDF remains inaccessible in this
environment, but the director independently verified the official scoring rubric
and supplied the weights recorded below. Other requirements that depend on the
PDF remain Unknown.

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
| Coding-agent use is required | Challenge page, Overview and FAQ | Phase 1.5 uses the same real `gpt-5.6-luna` Codex runtime for baseline and BreakFix reasoning, with captured replay traces | evidence/phase1.5-20260829T120133Z; integrity.real_model_responses_used=true | Confirmed requirement, captured run complete |
| Disclose tools used | Challenge page, Overview and FAQ | README and docs name the local prototype and limitations | README; docs | Confirmed |
| Submit representative trajectories for every agent used | Challenge page, Submission Package and FAQ | Baseline and BreakFix trajectories capture instructions by prompt reference, context, tool actions, outputs, retries, validation, and the no-ground-truth boundary | trajectories/phase1.5/*/case_*/replay.json; evidence/phase1.5-20260829T120133Z/*/trajectory.json | Confirmed requirement, Phase 1.5 captured |
| Complete solution code | Challenge page, Submission Package | Source, benchmark, tests, and runner are present | canonical project directory | Confirmed for Phase 1 |
| Improvement changelog with evidence-linked iterations | Challenge page, Submission Package | Changelog records the baseline, matrix, planner miss, timeout fix, and final rerun | docs/improvement-changelog.md | Confirmed for this checkpoint |
| Clean-environment reproduction guide | Challenge page, Submission Package | README gives local commands; clean-machine validation is not complete | README; build plan | Inferred implementation, not submission-complete |
| Exact commands for solution, baseline, and evaluation | Challenge page, Submission Package | `python scripts/run_phase15.py` replays the captured baseline, fixed matrix, and BreakFix evaluation; direct live-provider capture is still external to the script | README; scripts/run_phase15.py; docs/phase1.5-prompts.md | Partially confirmed |
| Versions, approximate runtime, and cost | Challenge page, Submission Package | Python version, provider, model, reasoning setting, model-call count, and per-process durations are recorded; token usage, latency, and cost were unavailable | evidence execution results; Phase 1.5 comparison model block | Partially confirmed |
| Solution video up to 5 minutes | Challenge page, Submission Package | No video produced in Phase 1 | Video remains future work | Confirmed requirement, not started |
| Video begins with problem and simple baseline | Challenge page, Submission Package | Not started | Video remains future work | Confirmed requirement, not started |
| Video shows realistic execution, comparison, changelog, strongest change, and removed experiment | Challenge page, Submission Package | Evidence and changelog exist for a future recording | docs/improvement-changelog.md; evidence | Confirmed requirement, not started |
| Correct, reproducible, testable, clearly explained solution | Challenge page, Overview | Standard-library runner, unit tests, five controlled cases, evidence, and docs | test run; evidence bundle | Confirmed objective, provisional evidence |
| Baseline plus advanced solution with meaningful improvement | Challenge page, Theme | Phase 1.5 compares a same-model live baseline, fixed matrix, and BreakFix targeted reasoning; BreakFix preserved efficiency but did not beat discovery | evidence/phase1.5-20260829T120133Z/comparison.json | Confirmed requirement, MIXED result |
| Allowed languages include Python, TypeScript, Java, C++, Go, Rust | Challenge page, Theme and FAQ | Python 3.14 prototype | pyproject.toml; environment check | Confirmed |
| Final problem PDF may prescribe runtime, dependency, API, and acceptance-test constraints | Challenge page, Theme | No PDF constraints could be read in this environment | blocked PDF URL | Unknown |
| Valid submission must be timely, complete, original, policy compliant, reproducible, and include repository/archive, tests, README, agent evidence, and video | Challenge page, FAQ | Repository, tests, README, evidence, and traces exist; archive, final form, and video do not | current tree | Partially confirmed |
| Consequential actions controlled by sandbox or simulation, with human approval | Challenge page, Rule Book | Phase 1 only runs synthetic sample code locally; it has no write-back or merge action and documents local execution limits | docs/assumptions-and-risks.md | Confirmed requirement, Phase 1 boundary |
| Qualified human reviewer for significant effects | Challenge page, Rule Book | No consequential action exists in Phase 1 | build plan; non-goals | Confirmed requirement, not yet applicable |
| Use legal, ethical, permitted data and keep credentials outside submission | Challenge page, Rule Book | Synthetic benchmark and secret-free source; .env is ignored | .gitignore; benchmark | Confirmed for Phase 1 |
| Every result claim connected to evidence | Challenge page, Rule Book | Comparison metrics point to per-lane evidence directories | evidence/phase1-20260829T104633Z/comparison.json | Confirmed for Phase 1 |
| Judges must be able to run and reproduce the main result | Challenge page, Rule Book | Local commands and offline fixtures are provided; fresh-machine validation remains open | README; build plan | Partially confirmed |
| micro1 may own submissions and use them for AI training and evaluation | Challenge page, Rule Book | No code action; recorded as an ownership consideration before public submission | this matrix | Confirmed |
| Scoring criteria and weights | Director-verified official instruction PDF | Rubric recorded below and used for prioritization | This document, director review | Confirmed |
| Tie-break order: Agent Solution and Engineering, Reproducibility, Measured Improvement, End to End Quality, final evidence review | Challenge page, Evaluation Criteria | Build plan prioritizes these gates | docs/build-plan.md | Confirmed |
| Prize amounts by award | Challenge page, Prizes & Awards | Total cash pool is recorded; individual award split is not encoded | page content inspected on 2026-08-29 | Unknown |
| API keys or model credits supplied by organizer | Challenge page, FAQ | Prototype uses no external model; future live baseline must use participant-owned setup | README | Confirmed: organizer says no |
| Registration/submission intake fields, archive format, exact acceptance tests, and final PDF constraints | Official instruction PDF link | Not implemented until the PDF can be read and the final form is rechecked | blocked URL and open verification queue | Unknown |

## Official scoring rubric

The official rubric is scored out of 100 points:

| Criterion | Points | What a strong entry demonstrates |
| --- | ---: | --- |
| Problem & User Value | 15 | A meaningful problem for a clearly defined user |
| Agent Solution & Engineering | 30 | Purposeful, technically sound use of context, tools, memory, verification, skills, or orchestration |
| End to End Quality | 20 | A realistic, self-contained execution producing a result an intended user can use |
| Measured Improvement | 15 | Fair-baseline gains connected to evidence through the improvement changelog |
| Reproducibility | 15 | A clear clean-environment path for baseline, final solution, and main evaluation |
| Hot Take / Insights | 5 | A practical lesson extracted from an observed agent failure mode |
| **Total** | **100** | |

The official tie-break priority from the HackerEarth challenge page is:

1. Agent Solution & Engineering
2. Reproducibility
3. Measured Improvement
4. End to End Quality
5. Final documented-evidence review

## Official facts used for this checkpoint

The challenge is online and individual-only. Coding-agent use is required.
The entry must contain a baseline and an advanced solution with meaningful
improvement, complete code, a changelog, a reproduction guide, a video of no
more than five minutes, and representative agent trajectories. The rule book
requires evidence-backed claims, safe handling of consequential actions, human
review where effects are significant, permitted data, and credentials kept
outside the submission.

The scoring weights above were independently verified by the director from the
official instruction PDF. The PDF itself and the final submission form still
must be rechecked before a final submission for constraints, starter material,
acceptance tests, archive format, and intake fields.

## Open verification queue

1. Obtain and read the official instruction PDF, including starter materials,
   constraints, and acceptance tests.
2. Recheck the final submission form fields and archive limits.
3. Add a direct provider path so the captured live coding-agent review and
   BreakFix reasoning can be regenerated outside the Codex runtime.
4. Verify whether any policy requires a public repository, and record the exact
   archive format.
