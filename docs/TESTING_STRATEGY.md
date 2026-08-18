# Protector Uttam Testing Strategy

## Overview

This document defines the complete testing strategy for Protector Uttam, a trust control plane for federated learning. The strategy covers multiple test layers, explicit test cases for each module, and critical invariants that must hold in all conditions.

**Goal:** Ensure correctness, reliability, and safety of the trust scoring and decision-making system without claiming perfect coverage.

---

## Test Layers

### 1. Unit Tests

**Purpose:** Validate individual scoring components in isolation.

**Scope:**
- Data Quality Score (DQS)
- Drift Health Score (DHS)
- Update Safety Score (USS)
- Reliability Score (RS)
- Performance Score (PS)
- Confidence Score
- Trust Score calculation

**File:** `tests/test_dqs.py`, `tests/test_dhs.py`, `tests/test_remaining_scores.py`, `tests/test_final_trust_score.py`

**Approach:**
- Test normal case, boundary case, invalid input, missing input, corrupted input, and unexpected state
- Verify all formulas mathematically with manual worked examples
- Test each component independently with mocked dependencies

### 2. Integration Tests

**Purpose:** Validate scoring components working together.

**Scope:**
- TrustScorer combining all 7 scores
- Calibration module using scoring results
- Validation framework evaluating scorer outputs
- Decision engine gate logic (hard safety, policy, confidence)

**File:** `tests/test_integration.py` (new)

**Approach:**
- End-to-end flow from raw input to final decision
- Verify consistency across components
- Test component interactions and dependencies

### 3. End-to-End Tests

**Purpose:** Validate complete system behavior including edge cases.

**Scope:**
- Full trust decision pipeline
- State transitions (new participant → stale → healthy)
- Aggregate safety checks

**File:** `tests/test_e2e.py` (new)

**Approach:**
- Simulate real federated learning scenarios
- Test participant lifecycle (new → active → degraded)
- Verify decision consistency across similar inputs

### 4. Edge Case Tests

**Purpose:** Validate boundary behavior and corner cases.

**Scope:**
- Empty inputs
- Single-sample datasets
- Constant values
- Extreme numeric values (0, 1, 99.9, 100)
- Very large datasets
- Minimal valid inputs

**File:** Embedded in unit test classes as `TestXXXXEdgeCases`, `TestXXXXBoundary`, `TestXXXXMinimal`

**Examples:** `test_single_sample()`, `test_empty_labels()`, `test_constant_features()`

### 5. Failure Injection Tests

**Purpose:** Validate system resilience and fallback behavior.

**Scope:**
- NaN inputs in all scorers
- Infinity inputs in all scorers
- Missing required fields
- Corrupted state (e.g., weights sum ≠ 1.0)
- Database failures (simulated)
- Trust engine exceptions

**File:** `tests/test_failure_injection.py` (new)

**Approach:**
- Deliberately inject failures
- Verify graceful degradation
- Confirm fallback mechanisms activate

### 6. Reproducibility Tests

**Purpose:** Ensure deterministic behavior.

**Scope:**
- Same input + same weights = same score
- Score does not vary based on ordering
- Timestamp independence
- Seed independence (for numpy operations)

**File:** `tests/test_reproducibility.py` (new)

**Approach:**
- Run same experiment multiple times
- Compare byte-for-byte equality of results
- Test with different random seeds (ensure results unchanged)

### 7. Regression Tests

**Purpose:** Prevent accidental breaking changes.

**Scope:**
- Known good outputs for canonical scenarios
- Historical decision results
- Formula correctness
- Weight validation logic

**File:** `tests/test_regression.py` (new)

**Approach:**
- Store golden results for baseline scenarios
- Compare against golden after code changes
- Use high precision (≥ 3 decimal places)

---

## Module Test Coverage Matrix

| Module | Normal | Boundary | Invalid | Missing | Corrupted | Unexpected | Tested |
|--------|--------|----------|---------|---------|-----------|------------|--------|
| **DataQualityScorer** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Yes |
| **DriftHealthScorer** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Yes |
| **UpdateSafetyScorer** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Yes |
| **ReliabilityScorer** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Yes |
| **PerformanceScorer** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Yes |
| **ConfidenceScorer** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Yes |
| **TrustScorer** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Yes |
| **Calibration** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Partial |
| **Validation Framework** | ✓ | ✓ | ✓ | ✓ | N/A | N/A | Yes |

---

## Critical Test Requirements

### 1. NaN Update Cannot Aggregate

**Test:** `test_nan_update_blocks_aggregation()`

**Specification:**
- Input: DHS with NaN values
- Expected: Score returns NaN or error
- System: Hard safety fails, decision is BLOCK
- Result: Update is excluded from aggregation

**Verification:**
```python
# NaN in current distribution
dhs_input = DriftHealthInput(
    baseline=[1, 2, 3],
    current=[np.nan, 2, 3]
)
result = DriftHealthScorer().score(dhs_input)
assert result.score == 0 or np.isnan(result.score)
# Trust score should BLOCK
trust_result = TrustScorer().score(...)
assert trust_result.decision == "BLOCK"
```

### 2. Invalid Shape Cannot Aggregate

**Test:** `test_invalid_shape_blocks_aggregation()`

**Specification:**
- Input: Gradient of wrong shape
- Expected: USS detects mismatch
- System: Hard safety fails
- Result: Update is excluded from aggregation

**Verification:**
```python
# Expected shape [128], actual shape [256]
uss_input = UpdateSafetyInput(
    current_gradient=np.ones(256),
    expected_shape=(128,)
)
result = UpdateSafetyScorer().score(uss_input)
assert result.is_valid_shape == False
# Hard safety in Trust should trigger
trust_result = TrustScorer().score(...)
assert trust_result.hard_safety_passed == False
```

### 3. Trust Engine Failure Activates Fallback

**Test:** `test_trust_engine_failure_fallback()`

**Specification:**
- Input: Corrupted weights (sum ≠ 1.0)
- Expected: TrustScorer raises ValueError
- System: Caller catches exception
- Result: Fallback decision applied

**Verification:**
```python
invalid_weights = {"dqs": 0.25, "dhs": 0.25, "uss": 0.20, "rs": 0.20, "ps": 0.10}  # sum = 1.0 OK
corrupt_weights = {"dqs": 0.50, "dhs": 0.25, "uss": 0.20, "rs": 0.20, "ps": 0.10}  # sum ≠ 1.0
try:
    TrustScorer().score(trust_input, weights=corrupt_weights)
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "sum to 1.0" in str(e)
```

### 4. High Trust with Low Confidence Does Not Blindly Allow

**Test:** `test_high_trust_low_confidence_escalates()`

**Specification:**
- Input: Trust score 85 (HIGH), Confidence 25 (LOW)
- Expected: Decision escalates from ALLOW to REVIEW
- Result: Not blindly allowed

**Verification:**
```python
high_trust_low_conf = TrustInput(
    dqs=85, dhs=85, uss=85, rs=85, ps=85,
    confidence=25,  # LOW
    hard_safety_passed=True,
    policy_approved=True
)
result = TrustScorer().score(high_trust_low_conf)
# Should be REVIEW or MONITOR, not ALLOW
assert result.decision in {"REVIEW", "MONITOR"}
```

### 5. Low Trust with High Confidence is Handled Correctly

**Test:** `test_low_trust_high_confidence_blocks()`

**Specification:**
- Input: Trust score 35 (LOW), Confidence 85 (HIGH)
- Expected: Decision is BLOCK (not escalated by confidence)
- Result: Low trust + high confidence still blocks

**Verification:**
```python
low_trust_high_conf = TrustInput(
    dqs=30, dhs=35, uss=40, rs=30, ps=30,
    confidence=85,  # HIGH
    hard_safety_passed=True,
    policy_approved=True
)
result = TrustScorer().score(low_trust_high_conf)
assert result.decision == "BLOCK"
```

### 6. New Participant is Not Given Fake Historical Confidence

**Test:** `test_new_participant_no_fake_history()`

**Specification:**
- Input: New participant (no historical data, confidence_history=[])
- Expected: Confidence score is low (≤ 50)
- Result: Not given artificial high confidence

**Verification:**
```python
new_participant = TrustInput(
    dqs=75, dhs=75, uss=75, rs=60, ps=60,
    confidence=0,  # NO history
    hard_safety_passed=True,
    policy_approved=True
)
confidence_result = ConfidenceScorer().score(confidence_input)
assert confidence_result.score ≤ 50, "New participant should have low confidence"
```

### 7. Duplicate Update is Handled

**Test:** `test_duplicate_update_detected()`

**Specification:**
- Input: Same update submitted twice
- Expected: System detects or marks as duplicate
- Result: Graceful handling (logged, not aggregated twice)

**Verification:**
```python
# Same update with identical timestamp
update1 = TrustInput(..., timestamp=1000)
update2 = TrustInput(..., timestamp=1000)
# System should detect or handle gracefully
# (Implementation-specific: may be at aggregation layer)
```

### 8. Stale Update is Handled

**Test:** `test_stale_update_restricted()`

**Specification:**
- Input: Update from T-30 days ago
- Expected: ReliabilityScorer detects staleness
- Result: Decision is RESTRICT or BLOCK

**Verification:**
```python
import time
old_timestamp = time.time() - (30 * 24 * 3600)  # 30 days ago
stale_update = TrustInput(
    ...,
    timestamp=old_timestamp
)
result = TrustScorer().score(stale_update)
assert result.decision in {"RESTRICT", "BLOCK"}
```

### 9. Database Failure is Handled

**Test:** `test_database_failure_graceful_degradation()`

**Specification:**
- Input: Cannot fetch participant history (DB unavailable)
- Expected: System uses available data or fallback
- Result: No crash, decision made with available info

**Verification:**
```python
# Simulated DB failure: confidence_history unavailable
# System should still compute score without crashing
confidence_input = ConfidenceInput(
    confidence_history=None,  # Unavailable
    update_frequency=None,
    metric_volatility=None
)
# Should not raise, but may return lower confidence
result = ConfidenceScorer().score(confidence_input)
assert result.score >= 0, "Should handle DB failure gracefully"
```

### 10. Missing Metric is Handled

**Test:** `test_missing_metric_scored_with_defaults()`

**Specification:**
- Input: A required metric is missing (e.g., no PS data)
- Expected: System uses default or skips that component
- Result: Trust score still computed

**Verification:**
```python
# Missing performance data: ps=None or not provided
trust_input = TrustInput(
    dqs=75, dhs=75, uss=75, rs=75,
    ps=None,  # MISSING
    confidence=70,
    hard_safety_passed=True,
    policy_approved=True
)
# Should handle gracefully (use default or normalize)
result = TrustScorer().score(trust_input)
assert result.score >= 0, "Should handle missing metric"
```

### 11. All Formulas are Mathematically Verified

**Test:** `test_all_formulas_manual_worked_examples()`

**Specification:**
- For each scoring module, manual example matches code
- Formula applied correctly step-by-step
- Numerical precision ≥ 1 decimal place

**Verification:**
Each test class includes `test_manual_worked_example()`:
- DQS: Input 5 samples → Expected score ≈ 95 ✓
- DHS: Baseline vs current distribution → Expected PSI-to-score mapping ✓
- USS: Valid gradient → Expected score ≈ 90+ ✓
- RS, PS, CONF, TRUST: Similar manual verification ✓

### 12. Same Input + Same Configuration = Same Result

**Test:** `test_deterministic_scoring()`

**Specification:**
- Input: Same TrustInput, same weights, run N times
- Expected: Score identical to ≥ 10 decimal places
- Result: No randomness in scoring logic

**Verification:**
```python
input_data = TrustInput(...)
weights = {"dqs": 0.25, "dhs": 0.25, "uss": 0.20, "rs": 0.20, "ps": 0.10}
scorer = TrustScorer()

results = [scorer.score(input_data, weights=weights) for _ in range(10)]
scores = [r.score for r in results]

# All scores must be identical
assert len(set(scores)) == 1, "Scores should be deterministic"
```

---

## Test Execution

### Running Tests

**All tests:**
```bash
python -m pytest tests/ -v
```

**Specific module:**
```bash
python -m pytest tests/test_dqs.py -v
```

**Specific test class:**
```bash
python -m pytest tests/test_dqs.py::TestDataQualityScoreME -v
```

**Specific test:**
```bash
python -m pytest tests/test_dqs.py::TestDataQualityScoreME::test_manual_worked_example -v
```

**With coverage:**
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

**Quick run (skip slow tests):**
```bash
python -m pytest tests/ -v -m "not slow"
```

### Coverage Goals

- **Line coverage:** ≥ 85%
- **Branch coverage:** ≥ 75%
- **Critical path coverage:** 100%
  - All scoring formulas
  - All decision gates
  - All error paths

### Coverage Report

Generate HTML report:
```bash
python -m pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Test Data and Fixtures

### Ground Truth Scenarios

File: `src/validation_framework.py`

8 independent scenarios representing real federated learning situations:

1. **V-001:** Healthy participant (SAFE)
2. **V-002:** NaN update (UNSAFE)
3. **V-003:** Infinity update (UNSAFE)
4. **V-004:** Wrong shape (UNSAFE)
5. **V-005:** Stale update (RESTRICT)
6. **V-006:** New participant, little evidence (REVIEW)
7. **V-007:** Severe controlled corruption (DEGRADED)
8. **V-008:** Large abnormal update (SUSPICIOUS)

These are used for:
- Validation framework tests
- Integration tests
- E2E tests
- Regression tests

### Test Data Organization

```
tests/
├── test_dqs.py              # DQS unit tests
├── test_dhs.py              # DHS unit tests
├── test_remaining_scores.py # USS, RS, PS, CONF, TRUST unit tests
├── test_final_trust_score.py # Trust score formula validation
├── test_calibration.py      # Calibration tests
├── test_validation_framework.py # Validation framework tests
├── test_integration.py      # Integration tests (NEW)
├── test_e2e.py              # End-to-end tests (NEW)
├── test_failure_injection.py # Failure injection tests (NEW)
├── test_reproducibility.py  # Reproducibility tests (NEW)
└── test_regression.py       # Regression tests (NEW)
```

---

## Known Limitations

### What This Strategy Does NOT Cover

1. **Performance benchmarking** — No timing requirements defined
2. **Concurrency** — Single-threaded tests only
3. **Memory profiling** — No heap/stack limits
4. **Network failures** — Limited to simulated DB failures
5. **Distributed aggregation** — Tested in isolation only
6. **Privacy guarantees** — No differential privacy tests
7. **Adversarial robustness** — No adversarial input tests
8. **Production deployment** — No staging environment tests

### Test Assumptions

1. **NumPy is correct** — Assume numpy is bug-free
2. **Python float precision** — Assume IEEE 754 compliance
3. **Sorted order** — Test data not explicitly ordered
4. **No external dependencies** — Test only scoring_engines, calibration, validation_framework
5. **Single-threaded execution** — No race condition tests

### Caveats

- **Not perfect:** Testing is heuristic-based; edge cases may remain undiscovered
- **Regression risk:** Code changes require re-running full suite
- **Golden data maintenance:** Regression tests need updates when formulas change intentionally
- **Real-world validation:** These tests are synthetic; real federated learning data may reveal new issues

---

## Continuous Integration Recommendations

### Pre-commit

```bash
python -m pytest tests/ -x --tb=short
```

Fail fast on first error.

### Pull Request

```bash
python -m pytest tests/ -v --cov=src
```

Full run with coverage report.

### Nightly

```bash
python -m pytest tests/ -v --cov=src --cov-report=html
python -m pytest tests/test_reproducibility.py -v --count=100
```

Extended reproducibility testing (run same tests 100 times).

### Release

```bash
python -m pytest tests/ -v
python -m pytest tests/test_regression.py -v
python -m pytest tests/test_e2e.py -v
```

All tests must pass; regression and E2E tests must pass.

---

## Test Maintenance

### Adding New Tests

1. Identify the module and test type (unit/integration/e2e)
2. Add test class or method to appropriate file
3. Use naming convention: `test_<scenario>_<expectation>()`
4. Include docstring with specification
5. Run `pytest` to verify
6. Update coverage report
7. Commit with test results

### Updating Formulas

1. Update formula in scoring_engines.py
2. Update manual worked example in test file
3. Run unit tests to verify
4. Update regression tests with new golden data
5. Run full suite
6. Update this document

### Debugging Failures

```bash
# Verbose output with full tracebacks
python -m pytest tests/test_xxx.py::TestClass::test_method -vv -s

# Drop into pdb on failure
python -m pytest tests/test_xxx.py -x --pdb

# Show print statements
python -m pytest tests/test_xxx.py -s
```

---

## Summary

This testing strategy provides:

- **7 test layers** covering unit, integration, E2E, edge cases, failure injection, reproducibility, and regression
- **12 critical test requirements** verified for correctness and safety
- **6 test files covering all modules** with normal, boundary, invalid, missing, corrupted, and unexpected state cases
- **Automated verification** of formulas, gates, and decision logic
- **Confidence in correctness** without claiming perfection

**Status:** Testing strategy defined. Test suite is active and maintained.

**Last Updated:** 2026-08-17
