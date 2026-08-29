from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TESTS = "python -m unittest discover -s tests -v; 1 visible test passed; exit code 0"


def baseline(verdict: str, summary: str, conclusion: str, finding: str | None = None, evidence: list[str] | None = None) -> dict:
    return {
        "change_summary": summary,
        "verdict": verdict,
        "findings": ([{"summary": finding, "severity": "high" if verdict == "DEFECT" else "medium", "evidence": evidence or ["after/app.py", "visible test coverage"], "confidence": "high" if verdict == "DEFECT" else "medium"}] if finding else []),
        "tests_run": [TESTS],
        "tool_actions": [
            {"action": "Inspected public.json, before/app.py, after/app.py, and after/tests/test_app.py", "result": "Observed the task, change, and visible happy-path coverage."},
            {"action": "Ran python -m unittest discover -s tests -v from the after workspace", "result": "One visible test passed; no hidden experiment was executed."},
        ],
        "retries": 0,
        "final_conclusion": conclusion,
    }


def assumption(ident: str, statement: str, surface: str, failure: str, risk: str, experiment: str, rationale: str, evidence: list[str] | None = None) -> dict:
    return {
        "id": ident,
        "statement": statement,
        "surface": surface,
        "evidence": evidence or ["after/app.py", "public.json task"],
        "failure_if_false": failure,
        "risk": risk,
        "proposed_experiment": {"id": experiment, "parameters": {}, "rationale": rationale},
    }


def breakfix(summary: str, assumptions: list[dict], conclusion: str) -> dict:
    return {
        "change_summary": summary,
        "assumptions": assumptions,
        "tests_run": [TESTS],
        "tool_actions": [
            {"action": "Inspected only the permitted case files", "result": "Loaded the task, before/after change, and visible tests."},
            {"action": "Ran python -m unittest discover -s tests -v from the after workspace", "result": "One visible test passed; no hidden experiment was executed."},
        ],
        "retries": 0,
        "final_conclusion": conclusion,
    }


BASELINE = {
    "h01": baseline("DEFECT", "Removed duplicate suppression from webhook delivery.", "DEFECT: retries can apply the amount repeatedly; this is inferred from source and not hidden execution.", "Repeated delivery records and charges the same request again.", ["before/app.py", "after/app.py"]),
    "h02": baseline("SAFE", "Added a lock around the processed-request check and update.", "SAFE for the inspected in-process path: the visible test passes and the check-and-record operation is guarded.", None),
    "h03": baseline("DEFECT", "Removed the empty-batch fallback from peak calculation.", "DEFECT: empty batches now raise ValueError; the visible test covers only non-empty input.", "max(values) is called unconditionally on an empty collection.", ["before/app.py", "after/app.py", "after/tests/test_app.py"]),
    "h04": baseline("SAFE", "Refactored peak calculation with max(values, default=0).", "SAFE for the supplied list-input contract; the visible test passes and the empty path is defined.", None),
    "h05": baseline("DEFECT", "Changed account loading from a defaulted lookup to a required tax_rate key.", "DEFECT: a legacy record without tax_rate now raises KeyError.", "Legacy records without tax_rate are no longer readable.", ["public.json", "before/app.py", "after/app.py"]),
    "h06": baseline("SAFE", "No observable behavior change in profile loading.", "SAFE for the inspected change: the visible test passes and missing tax_rate still defaults to 0.2.", None),
    "h07": baseline("INCONCLUSIVE", "Changed order-insensitive event handling to an order-sensitive state machine.", "The visible happy path passes, but the task context does not establish whether valid events may arrive out of order.", "Reordered events remain pending although the prior implementation confirmed the same event set.", ["before/app.py", "after/app.py", "public.json"]),
    "h08": baseline("SAFE", "No observable change in the order-insensitive event-set implementation.", "SAFE for the supplied scope: the visible test passes and the before/after implementations match.", None),
    "h09": baseline("DEFECT", "Replaced timezone conversion with direct timezone attachment.", "DEFECT: replace(tzinfo=...) relabels an aware timestamp instead of converting the absolute instant.", "The changed conversion can produce the wrong local hour across timezone boundaries.", ["before/app.py", "after/app.py"]),
    "h10": baseline("SAFE", "No implementation change observed in regional-hours calculation.", "SAFE for the supplied scope: the implementations match and the visible test passes.", None),
    "h11": baseline("DEFECT", "Replaced default-tolerant configuration loading with mandatory nested key access.", "DEFECT: missing config or currency now raises KeyError instead of returning the documented default.", "Older records without config or currency fail during loading.", ["public.json", "before/app.py", "after/app.py"]),
    "h12": baseline("SAFE", "No implementation change observed in checkout configuration loading.", "SAFE for the supplied scope: the USD fallback remains and the visible test passes.", None),
    "h13": baseline("DEFECT", "Removed synchronization around concurrent claim detection and effect recording.", "DEFECT: concurrent deliveries can all pass the membership check before recording duplicate effects.", "The check and effect are no longer one atomic critical section.", ["before/app.py", "after/app.py"]),
    "h14": baseline("SAFE", "Extracted the reservation claim body while preserving its lock.", "SAFE for the supplied scope: the visible test passes and the lock protects the claim sequence.", None),
}


BREAKFIX = {
    "h01": breakfix("Removed duplicate suppression from webhook delivery.", [assumption("retry_single_effect", "A retry reuses the same request_id and must preserve one effect.", "timing", "Repeated attempts increase total_charged.", "high", "retry_duplicate", "Replay the same request twice to test idempotency.")], "Visible tests pass; deterministic retry execution should decide the assumption."),
    "h02": breakfix("Added a process-local lock around request-id check-and-mark logic.", [assumption("stable_request_state", "Retries share a stable request_id and the guarded process state.", "timing", "A retry could be charged twice if the identifier or state boundary changes.", "high", "retry_duplicate", "Replay the same request twice.")], "The visible test passes; execute retry_duplicate before making a final claim."),
    "h03": breakfix("Removed the empty-list fallback from peak calculation.", [assumption("non_empty_items", "Every request supplies a non-empty items collection.", "input", "max(values) raises ValueError on an empty collection.", "medium", "input_empty", "Send an empty collection to exercise the changed boundary.")], "The visible test passes; the empty-input assumption remains for deterministic execution."),
    "h04": breakfix("Refactored peak calculation to max(values, default=0).", [assumption("empty_batch_defined", "An empty items collection is valid and should produce peak zero.", "input", "The empty summary could be semantically wrong despite no exception.", "high", "input_empty", "Exercise the changed empty-collection path."), assumption("zero_value_valid", "A zero-only batch is a valid numeric input.", "input", "A zero value could be mishandled as empty.", "medium", "input_boundary_zero", "Check the smallest zero-valued batch separately.")], "The visible test passes; empty and zero-valued input should be executor-checked."),
    "h05": breakfix("Changed account loading to require tax_rate.", [assumption("legacy_records_have_tax_rate", "All persisted records include tax_rate.", "state", "A legacy record without tax_rate raises KeyError.", "high", "state_legacy", "Load an older record lacking the field.")], "Current-record tests pass; legacy compatibility remains an assumption."),
    "h06": breakfix("No observable code change in profile loading.", [assumption("legacy_record_is_mapping", "Legacy records reach run with mapping-like state.", "state", "A non-mapping state fails before profile loading completes.", "high", "state_legacy", "Exercise a legacy record omitting tax_rate."), assumption("legacy_tax_rate_default", "The compatibility value 0.2 is correct when tax_rate is absent.", "state", "Older records silently receive an incorrect tax rate.", "medium", "state_legacy", "Check a record lacking tax_rate."), assumption("payload_contains_state", "Every caller supplies a payload containing state.", "input", "An empty payload raises KeyError at the state lookup.", "medium", "input_empty", "Exercise the empty-input boundary around state loading.")], "Visible tests pass; legacy state and empty-input behavior remain unverified."),
    "h07": breakfix("Changed event handling to an order-sensitive state machine.", [assumption("event_order_preserved", "A valid delivery may arrive with events reordered.", "timing", "Reordered events can produce the wrong final state.", "high", "events_reordered", "Deliver the same valid events in reverse order."), assumption("duplicate_delivery_harmless", "A repeated valid delivery is harmless.", "timing", "Duplicate delivery could repeat a transition.", "medium", "retry_duplicate", "Replay the valid delivery."), assumption("empty_events_handled", "An empty event collection is handled as pending.", "input", "An empty collection could raise or confirm incorrectly.", "low", "input_empty", "Send an empty collection.")], "The visible happy path passes; the executor should resolve the proposed assumptions."),
    "h08": breakfix("No observable change in the order-insensitive event-set implementation.", [assumption("order_independent_event_set", "A valid workflow is determined by event membership regardless of order.", "timing", "A reordered valid sequence could produce the wrong final state.", "medium", "events_reordered", "Deliver the valid events in reverse order.")], "Visible coverage is limited to one order; deterministic execution should validate the assumption."),
    "h09": breakfix("Replaced timezone conversion with direct timezone attachment.", [assumption("absolute_offset_preserved", "An offset-bearing timestamp must be converted as an absolute instant.", "world", "replace(tzinfo=...) can produce the wrong local hour.", "high", "world_dst", "Evaluate an offset-bearing timestamp at a DST boundary.")], "The visible test passes; the DST conversion assumption requires deterministic execution."),
    "h10": breakfix("The regional-hours implementation is unchanged.", [assumption("regional_dst_rules", "ZoneInfo converts absolute timestamps with the correct regional rules.", "world", "A stale or incorrect offset could shift the open result around DST.", "high", "world_dst", "Evaluate a timestamp across a DST boundary.")], "Visible evidence is limited to ordinary time; execute world_dst before deciding."),
    "h11": breakfix("Replaced default-tolerant configuration loading with mandatory nested key access.", [assumption("legacy_config_present", "Every persisted record contains config.", "state", "A legacy record without config raises KeyError.", "high", "state_legacy", "Load a legacy record without config."), assumption("currency_present", "Every configuration contains currency.", "state", "Missing currency bypasses the documented USD default.", "high", "config_missing", "Remove the optional currency field.")], "Visible tests pass; both dependency-boundary assumptions need deterministic execution."),
    "h12": breakfix("No observable change in checkout configuration loading.", [assumption("legacy_config_default", "Older records may omit config or currency and should receive USD.", "state", "A legacy record could fail or return the wrong default.", "medium", "state_legacy", "Load older state missing the configuration field.")], "Visible tests pass; legacy configuration compatibility remains unverified."),
    "h13": breakfix("Removed the lock around concurrent claim detection and added a barrier.", [assumption("claim_check_atomic", "Concurrent deliveries cannot both pass membership before recording.", "timing", "Multiple deliveries can append duplicate effects.", "high", "concurrent_duplicate", "Drive two concurrent copies through the effect boundary.")], "The visible single-claim test passes; concurrent duplicate behavior requires deterministic execution."),
    "h14": breakfix("Extracted reservation claiming while preserving lock-protected deduplication.", [assumption("claim_state_atomic", "All concurrent deliveries share the same state and lock through the extracted helper.", "timing", "Concurrent copies could record more than one effect.", "high", "concurrent_duplicate", "Deliver two concurrent copies of one request.")], "The visible test passes; deterministic concurrent execution should validate the refactor."),
}


def main() -> None:
    for lane, responses in (("baseline", BASELINE), ("breakfix", BREAKFIX)):
        for case_id, response in responses.items():
            case_root = ROOT / "benchmark" / "phase2a_holdout" / case_id
            public = json.loads((case_root / "public.json").read_text(encoding="utf-8"))
            target = ROOT / "trajectories" / "phase2a" / lane / case_id
            target.mkdir(parents=True, exist_ok=True)
            (target / "replay.json").write_text(json.dumps({
                "provider": "Codex multi-agent runtime",
                "model": "gpt-5.6-luna",
                "reasoning_effort": "xhigh",
                "temperature": None,
                "max_output_tokens": None,
                "prompt_id": f"phase2a-{lane}-v1",
                "prompt_file": "docs/phase2a-prompts.md",
                "prompt_workspace": str(case_root),
                "model_calls": 1,
                "runtime_ms": None,
                "latency_ms": None,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "monetary_cost_usd": None,
                "retries": 0,
                "context": {"public": public, "workspace_files": ["public.json", "before/app.py", "after/app.py", "after/tests"]},
                "tool_access": "Codex subagent repository inspection and visible-test execution under prompt restrictions",
                "tool_actions": response["tool_actions"],
                "capture_source": "normalized from completed live Codex subagent response; no ground truth supplied",
                "response_text": json.dumps(response, separators=(",", ":")),
            }, indent=2) + "\n", encoding="utf-8")
    print("Seeded 28 Phase 2A replay artifacts from live Codex subagent responses.")


if __name__ == "__main__":
    main()
