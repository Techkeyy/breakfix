# micro1 Frontier Engineering Challenge 2026 requirements

Research date: 2026-08-29. Local timezone: Africa/Lagos. Matrix statuses are
limited to PASS, FAIL, or N/A. N/A is used when a requirement is a participant
obligation, outside the software scope, or not determinable because the official
instruction PDF or final intake form remains inaccessible. The HackerEarth
challenge page is the primary source. The director independently verified the
official scoring rubric and supplied the weights recorded below.

Primary source:
https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/

Official instruction link exposed on that page:
https://uc.hackerearth.com/he-public-ap-south-1/micro1%20-%20First%20Hackathon97ce7c5.pdf

## Requirement matrix

| REQUIREMENT | SOURCE | IMPLEMENTATION | EVIDENCE | STATUS |
| --- | --- | --- | --- | --- |
| Online challenge | HackerEarth challenge page, Overview | Local-first CLI and evidence bundle; no deployment claimed | README and run output | PASS |
| Individual entry, team size 1 | Challenge page, header and FAQ | Participant obligation, not a software gate | Final form must be completed by entrant | N/A |
| Challenge window Aug 28 to Aug 31, 2026 | Challenge page, header | Work is timestamped in evidence run IDs | evidence/phase1-20260829T104633Z | PASS |
| Kickoff at Aug 28, 15:00 UTC | Challenge page, Overview | Not encoded as a product deadline | This document | PASS |
| End at Aug 31, 18:00 UTC | Challenge page, Overview | Not encoded as a product deadline | This document | PASS |
| Free and global, subject to legal restrictions | Challenge page, Overview and Eligibility | No paid service or restricted data required for the product | Standard-library prototype | PASS |
| At least 18 years old | Challenge page, Eligibility | Participant responsibility, not a software gate | Final form must be completed by entrant | N/A |
| Six months practical software-building experience or equivalent | Challenge page, Eligibility | Participant responsibility, not a software gate | Final form must be completed by entrant | N/A |
| One registration and one final submission | Challenge page, Eligibility | No submission automation built | Final form and submission remain manual | N/A |
| Coding-agent use is required | Challenge page, Overview and FAQ | Phase 1.5 and final evaluation use real model lanes with captured replay traces | evidence/final-eval-20260829T212423Z/trajectories/; integrity metadata | PASS |
| Disclose tools used | Challenge page, Overview and FAQ | README and docs name the local prototype and limitations | README; docs | PASS |
| Simple baseline | Challenge page, Theme and Submission Package | Same-case generic comparator receives only public context and visible tests | evidence/final-eval-20260829T212423Z/trajectories/baseline/; docs/final-evaluation-protocol.md | PASS |
| Advanced solution | Challenge page, Theme and Submission Package | BreakFix planner, bounded targeted execution, evidence, replay, regression, approval, and verification | breakfix/; docs/canonical-demo.md; final evidence | PASS |
| Fair same-case evaluation | Challenge page, Evaluation Criteria | Generic, fixed, and BreakFix lanes use the same fresh opaque 16-case holdout and visible context | docs/final-evaluation-protocol.md; final summary | PASS |
| Frozen primary metric | Director-verified protocol | Count executable experiments needed for complete seeded-fault recall with zero safe false confirmed breaks | docs/final-evaluation-protocol.md; final summary | PASS |
| Defined success criteria | Director-verified protocol | Every faulty case must confirm a break, every safe control must avoid a confirmed break, and both eligible lanes must beat the fixed count | docs/final-evaluation-protocol.md; final summary | PASS |
| Submit representative trajectories for every agent used | Challenge page, Submission Package and FAQ | Baseline and BreakFix trajectories capture prompt hashes, context, tool actions, outputs, retries, validation, telemetry, and the no-ground-truth boundary | evidence/final-eval-20260829T212423Z/trajectories/; docs/trajectory-index.md | PASS |
| Complete solution code | Challenge page, Submission Package | Source, benchmark, tests, and runner are present | canonical project directory | PASS |
| Improvement changelog with evidence-linked iterations | Challenge page, Submission Package | Changelog records baseline, matrix, planner miss, timeout fix, provider recovery, and final rerun | docs/improvement-changelog.md | PASS |
| Clean-environment reproduction guide | Challenge page, Submission Package | Python setup, offline acceptance, CLI, UI, replay, and authorized final-evaluation commands are documented | REPRODUCE.md; clean Temp clone | PASS |
| Exact commands for solution, baseline, and evaluation | Challenge page, Submission Package | README and REPRODUCE.md document offline product checks, local UI, final fixed matrix, and the authorized live provider runner | README; REPRODUCE.md; scripts/run_final_evaluation.py | PASS |
| Versions, approximate runtime, and cost | Challenge page, Submission Package | Python version, provider, model, reasoning setting, model-call count, token totals, retries, latency, subprocess durations, and approximate cost are recorded | evidence/final-eval-20260829T212423Z/final-summary.json | PASS |
| Solution video up to 5 minutes | Challenge page, Submission Package | Recording script and shot list are prepared; a video file is not yet recorded | docs/video-script.md; docs/video-shot-list.md | FAIL |
| Video begins with problem and simple baseline | Challenge page, Submission Package | Recording sequence specifies the problem and generic comparator first | docs/video-script.md; docs/video-shot-list.md | FAIL |
| Video shows realistic execution, comparison, changelog, strongest change, and removed experiment | Challenge page, Submission Package | Evidence, script, and shot list specify the required sequence; recording remains manual | docs/improvement-changelog.md; docs/video-shot-list.md | FAIL |
| Correct, reproducible, testable, clearly explained solution | Challenge page, Overview | Standard-library runner, unit tests, independent sample, final holdout, evidence, and docs pass clean reproduction | 38-test run; clean Temp clone; final evidence | PASS |
| Baseline plus advanced solution with meaningful improvement | Challenge page, Theme | Final same-model generic baseline, fixed matrix, and BreakFix targeted lanes show 7/8, 8/8, and 8/8 fault recall respectively; BreakFix uses 38 versus 128 experiments with 0 safe false confirmations | evidence/final-eval-20260829T212423Z/final-summary.json; docs/final-evaluation-report.md | PASS |
| Allowed languages include Python, TypeScript, Java, C++, Go, Rust | Challenge page, Theme and FAQ | Python 3.14 prototype | pyproject.toml; clean environment check | PASS |
| Final problem PDF may prescribe runtime, dependency, API, and acceptance-test constraints | Challenge page, Theme | No PDF constraints could be read in this environment | blocked PDF URL; open verification queue | N/A |
| Valid submission must be timely, complete, original, policy compliant, reproducible, and include repository/archive, tests, README, agent evidence, and video | Challenge page, FAQ | Repository, tests, README, evidence, traces, and package docs exist; archive, final form, and video remain manual | current tree; open verification queue | FAIL |
| Consequential actions controlled by sandbox or simulation, with human approval | Challenge page, Rule Book | Product runs synthetic sample code locally; candidate fixes require explicit approval and there is no merge or push action | docs/assumptions-and-risks.md; docs/canonical-demo.md | PASS |
| Qualified human reviewer for significant effects | Challenge page, Rule Book | No consequential external action exists; the candidate-fix path has an explicit approval checkpoint | docs/canonical-demo.md; non-goals | N/A |
| Use legal, ethical, permitted data and keep credentials outside submission | Challenge page, Rule Book | Synthetic benchmark, secret-free source, ignored .env, and external evaluator truth | .gitignore; docs/security-audit.md | PASS |
| Every result claim connected to evidence | Challenge page, Rule Book | Final comparison metrics point to per-lane evidence and the public summary | evidence/final-eval-20260829T212423Z/final-summary.json; docs/claims.md | PASS |
| Judges must be able to run and reproduce the main result | Challenge page, Rule Book | Fresh Git clone, fresh venv, editable install, 38 tests, canonical flow, doctor, and UI/API checks pass | REPRODUCE.md; clean Temp clone | PASS |
| micro1 may own submissions and use them for AI training and evaluation | Challenge page, Rule Book | No code action; ownership consideration is recorded before public submission | this matrix | PASS |
| Scoring criteria and weights | Director-verified official instruction PDF | Rubric recorded below and used for prioritization | This document, director review | PASS |
| Tie-break order: Agent Solution and Engineering, Reproducibility, Measured Improvement, End to End Quality, final evidence review | Challenge page, Evaluation Criteria | Build plan prioritizes these gates | docs/build-plan.md | PASS |
| Prize amounts by award | Challenge page, Prizes & Awards | Award split is not needed to operate the product and was not independently encoded | page content inspected on 2026-08-29 | N/A |
| API keys or model credits supplied by organizer | Challenge page, FAQ | Final live lanes use an explicitly authorized participant-configured DeepSeek credential; no organizer credential is assumed | README; final run metadata records presence only | PASS |
| Registration/submission intake fields, archive format, exact acceptance tests, and final PDF constraints | Official instruction PDF link | Not determinable until the PDF can be read and the final form is rechecked | blocked URL and open verification queue | N/A |

## Final evaluation status

The final protocol is frozen in `docs/final-evaluation-protocol.md`, with the
public holdout committed separately from the external evaluator truth. The
final run `final-eval-20260829T212423Z` used 32 live DeepSeek calls, complete
provider telemetry, 128 fixed executions, and 38 targeted executions. The
primary gate passed. Phase 2B Attempt 1 remains a separate historical FAIL and
is not overwritten by this result.

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
3. Record the final video file and any required public repository or archive
   format after the submission form is rechecked.
