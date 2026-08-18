# Scenario Testing for Prototype Validation

This document describes the additional prototype validation layer for scenario-based checks of the Protector Uttam trust system.

## Scope

The scenario layer intentionally does not modify the frozen scoring formulas, thresholds, decision logic, or the existing 188 tests. Instead, it builds a small set of end-to-end validation scenarios that start from a valid baseline and modify only the inputs necessary to simulate realistic operating conditions.

The system under test is the real trust engine from `src/scoring_engines.py`, called through `TrustScorer.score(...)` without mocking or formula duplication.

---

## Baseline Input

Every scenario begins from the same valid baseline input:

- DQS: 92
- DHS: 90
- USS: 95
- RS: 88
- PS: 90
- Confidence: 85
- Hard Safety: PASS
- Policy Approved: True

This creates a healthy participant profile and ensures every scenario isolates a single risk pattern.

---

## Scenario Catalog

### 1. healthy_participant

- Simulates: A reliable, healthy participant with strong quality and safe model behavior.
- Input modified: No overrides from baseline.
- Why this matters: Establishes the control case for all other scenarios.
- Score that should react: All component scores remain high.
- Expected decision: ALLOW
- Actual result: Verified by running the real scoring engine.
- Scenario pass status: PASS when actual decision matches ALLOW.

### 2. poor_data_quality

- Simulates: A participant whose training data is noisy, incomplete, or low quality.
- Input modified: DQS lowered to 32, RS to 42, PS to 38, confidence reduced to 68.
- Why this matters: Low-quality data often creates unstable or misleading model updates.
- Score that should react: DQS and PS drop sharply; trust score reduces from the healthy baseline.
- Expected decision: REVIEW or MONITOR depending on the actual scorer result. The prototype scenario is expected to require additional review because evidence is weak.
- Actual result: Verified by the real engine.
- Scenario pass status: PASS when output is consistent with documented policy.

### 3. high_data_drift

- Simulates: Participant data distribution shifted away from expected historical distribution.
- Input modified: DHS lowered to 18 while keeping other components near healthy values.
- Why this matters: Distribution drift can lead to negative transfer and poor generalization.
- Score that should react: DHS is the primary trigger.
- Expected decision: MONITOR
- Actual result: Verified at execution time.
- Scenario pass status: PASS when actual decision matches the expected prototype policy.

### 4. unsafe_update

- Simulates: A structurally invalid or unsafe model update.
- Input modified: USS lowered to 12 and hard_safety_passed set to False.
- Why this matters: Hard safety failures should block the update immediately.
- Score that should react: USS drops sharply and the hard safety gate fails.
- Expected decision: BLOCK
- Actual result: Verified by the scorer.
- Scenario pass status: PASS when the actual decision is BLOCK.

### 5. stale_update

- Simulates: an update whose timestamp exceeds the configured staleness threshold.
- Input modified: Timestamp set to a value older than 180 days.
- Why this matters: Freshness is a real validation concern; stale updates may not reflect current model state.
- Score that should react: Freshness policy, not raw trust score alone, should trigger the block.
- Expected decision: BLOCK
- Actual result: Verified by the real engine.
- Scenario pass status: PASS when actual decision equals BLOCK.

### 6. high_trust_low_confidence

- Simulates: A participant with high measured trust but weak evidence coverage.
- Input modified: Confidence reduced to 28.
- Why this matters: A high score is not trustworthy if the confidence in the evaluation is poor.
- Score that should react: Confidence and review gating are the decisive factors.
- Expected decision: REVIEW
- Actual result: Verified after execution.
- Scenario pass status: PASS when the actual decision is REVIEW.

### 7. unreliable_participant

- Simulates: A participant with poor reliability history or inconsistent performance.
- Input modified: RS lowered to 20 while other components remain moderate.
- Why this matters: Reliability affects whether the participant should remain in the trusted cohort.
- Score that should react: RS and overall trust drop.
- Expected decision: REVIEW or MONITOR depending on the actual engine result.
- Actual result: Verified at runtime.
- Scenario pass status: PASS when actual decision aligns with the documented policy semantics.

### 8. poor_model_performance

- Simulates: A model update that performs too poorly to justify inclusion.
- Input modified: PS lowered to 18 and confidence reduced to 60.
- Why this matters: Even safe updates can be harmful if they degrade model quality or do not improve the target objective.
- Score that should react: PS and trust score drop meaningfully.
- Expected decision: MONITOR
- Actual result: Verified via `TrustScorer` output.
- Scenario pass status: PASS when decision reflects the actual prototype policy.

---

## Execution Model

Each scenario is evaluated as follows:

1. Start from the valid baseline input.
2. Apply only the scenario-specific overrides.
3. Use `TrustInput(...)` from the real scoring engine.
4. Call `TrustScorer().score(...)` exactly as production code does.
5. Export a summary row containing the component scores, trust score, confidence label, safety result, freshness result, expected decision, actual decision, and PASS/FAIL result.

No formulas are rewritten, no mocks are used, and no core logic is altered.

---

## Output File Contract

The runner writes:

- `experiments/results/scenario_results.json`
- `experiments/results/scenario_results.csv`

Each result includes:

- DQS
- DHS
- USS
- RS
- PS
- Trust Score
- Confidence
- Hard Safety result
- Freshness result
- Final Decision
- Decision reason
- Expected Decision
- PASS/FAIL status

---

## Current Validation Status

The scenario validation layer is an additional prototype demonstration layer and must be interpreted as an external validation harness, not as a replacement for the core test suite.
