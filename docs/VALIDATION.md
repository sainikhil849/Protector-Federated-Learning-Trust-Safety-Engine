# Validation Framework

## Purpose

This validation framework is designed to evaluate Trust Score decisions against independent ground-truth scenarios. The ground truth is defined outside the Trust Score logic so the evaluation is not circular.

The framework produces per-experiment audits and summary metrics for all scenarios.

## Ground Truth Principle

The model is not allowed to define its own ground truth. Instead, each scenario is defined by independent expected behavior, such as:

- Healthy participant → expected SAFE
- NaN update → expected UNSAFE
- Infinity → expected UNSAFE
- Wrong shape → expected UNSAFE
- Stale update → expected RESTRICT
- New participant with little evidence → expected REVIEW or MONITOR
- Severe controlled corruption → expected degraded behavior
- Large abnormal update → expected suspicious or restricted behavior

These external expectations are the reference labels used during validation.

## Scenario Format

Each experiment captures:

- scenario ID
- input conditions
- ground truth
- Trust Score
- Confidence
- Hard Safety Result
- Decision
- correct/incorrect flag

## Experiment Metrics Computed

For every experiment set, the system calculates:

- TP
- TN
- FP
- FN
- Precision
- Recall
- F1
- Specificity
- Balanced Accuracy
- FPR
- FNR

Definitions used:

- TP: true positive
- TN: true negative
- FP: false positive
- FN: false negative
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 × Precision × Recall / (Precision + Recall)
- Specificity = TN / (TN + FP)
- Balanced Accuracy = (Recall + Specificity) / 2
- FPR = FP / (FP + TN)
- FNR = FN / (FN + TP)

## Output Artifacts

The system writes validation results to:

- experiments/results/validation_results.json
- experiments/results/validation_results.csv

These files are generated from actual experiment results and are not hardcoded.

## Validation Scenarios Included

The framework includes independent scenarios for:

1. healthy participant
2. NaN update
3. infinity update
4. wrong shape
5. stale update
6. new participant with little evidence
7. severe controlled corruption
8. large abnormal update

## Decision Interpretation

The validation framework classifies decisions into positive and negative categories for confusion-matrix purposes. This allows consistent TP/TN/FP/FN calculation regardless of the label naming.

## No Hardcoded Results

All metrics are computed dynamically from the evaluation set. There are no fixed outcome tables embedded in the validation logic.

## Usage

```python
from src.validation_framework import run_validation_experiments

result = run_validation_experiments(output_dir="experiments/results")
print(result["summary"])
```

## Notes

This validation layer is independent from the scoring implementation itself, which keeps the evaluation system auditable and resistant to circular reasoning.
