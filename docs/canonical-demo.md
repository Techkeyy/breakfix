# Canonical end-to-end demo

The canonical demo is the independent sample under
examples/independent_sample/. It is not part of any benchmark holdout.

Run it with:

    python scripts/run_canonical_demo.py

The script uses transparent recorded provider doubles so recording is reliable
without spending another live-provider call. The product itself performs the
analysis, isolated execution, evidence capture, replay, regression generation,
fix proposal, explicit approval, patch application, and verification. The
sample is not recognized by any product branch.

The timestamped successful run is written under evidence/ and its result must
show:

- visible tests pass before analysis;
- input_empty is selected and reaches CONFIRMED BREAK;
- replay reproduces the failure;
- a candidate patch is proposed and marked as requiring human approval;
- application records explicit approval;
- the exact failing scenario passes after the patch;
- generated regression and original visible tests pass;
- final status is VERIFIED.

The run output and evidence are the source of truth. Use the path printed by
the command for a new run.
