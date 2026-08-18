# Fallback and Resilience Policy

## Overview

The system supports three operational modes:

- NORMAL: trust score calculations are running normally
- DEGRADED: a non-critical component failed, but enough independent evidence remains for a reduced-confidence decision
- SAFE_MODE: a critical failure or insufficient evidence requires deterministic fallback

The fail-safe policy is intentionally conservative:

- a crashed or invalid trust engine must never silently ALLOW
- NaN and Infinity values are treated as hard-block conditions
- invalid structures and wrong model versions are treated as blocking conditions
- unknown states fall back to REVIEW
- database and historical-data issues are handled conservatively with REVIEW or RESTRICT

## Fail-safe Rule

If an advanced scoring component fails, the system must:

1. record the failure
2. determine whether enough independent evidence remains
3. if not, activate deterministic fallback
4. never silently ALLOW because the Trust Engine crashed

## Deterministic Fallback Rules

| Failure type | Fallback decision |
|---|---|
| NaN | BLOCK |
| Infinity | BLOCK |
| invalid structure | BLOCK |
| wrong model version | BLOCK |
| unknown state | REVIEW |
| database unavailable | RESTRICT |
| missing historical data | RESTRICT |
| trust engine exception | BLOCK |

## Behavior by Mode

### NORMAL

All components are available and the trust engine computes a standard decision based on score and gates.

### DEGRADED

When the failure affects a non-critical component but at least 3 independent evidence signals remain, the system does not fail closed. Instead it transitions to DEGRADED and returns a conservative decision such as REVIEW or RESTRICT.

This mode is used for issues like:

- database unavailable
- missing historical data when enough other signals still exist
- isolated scoring component failures with redundancy left

### SAFE_MODE

When the trust engine fails, a critical signal is invalid, or evidence is insufficient, the system enters SAFE_MODE and applies a deterministic fallback.

Examples:

- NaN => BLOCK
- Infinity => BLOCK
- invalid structure => BLOCK
- wrong model version => BLOCK
- unknown state => REVIEW
- trust engine exception => BLOCK

## Failure Injection Coverage

The implementation includes resilience checks for these failure modes:

- Trust Engine exception
- database unavailable
- Drift Engine failure
- Performance Engine failure
- missing historical data

These are covered in the dedicated resilience tests in `tests/test_fail_safe_resilience.py`.

## Verification

The resilience suite was executed successfully:

- `python -m pytest tests/test_fail_safe_resilience.py -q`
- Result: 6 passed in 0.32s

## Summary

The fail-safe policy is intentionally conservative and prevents unsafe allow decisions. The system records failures, evaluates whether independent evidence remains, and enforces deterministic fallback when needed.
