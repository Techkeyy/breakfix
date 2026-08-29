# Final independent evaluation report

Run: `final-eval-20260829T212423Z`  
Protocol: `final-independent-evaluation-v1`  
Product checkpoint: `13b8c89`  
Public holdout checkpoint: `4939d76`

## Result

**Primary gate: PASS**

| Lane | Fault recall | Safe false confirmed breaks | Experiments | Eligible |
| --- | ---: | ---: | ---: | --- |
| Generic comparator | 7/8 (87.5%) | 0/8 | 0 | No, secondary lane |
| Fixed matrix | 8/8 (100%) | 0/8 | 128 | Yes |
| BreakFix targeted | 8/8 (100%) | 0/8 | 38 | Yes |

BreakFix used 70.3125% fewer deterministic experiments than the fixed matrix
and averaged 4.75 targeted experiments per confirmed faulty case. All 16 live
provider outputs were structured and valid on the first recorded model
completion attempt; the two transport retries are preserved in telemetry.

The generic comparator and BreakFix lanes each used 16 recorded model calls,
for 32 total. Approximate recorded provider cost was `$0.138005824` under the
DeepSeek pricing metadata captured by the adapter.

The complete oracle-free bundle is under
`evidence/final-eval-20260829T212423Z/`. Evaluator-only expected outputs remain
outside the repository in the Temp run workspace.
