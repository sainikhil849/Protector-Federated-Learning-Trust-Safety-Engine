# Ablation Study: Score Component Contribution

## Objective

This study evaluates whether each score component meaningfully contributes to prototype performance by comparing the full model against variant models where one component is removed and the remaining weights are renormalized.

The evaluated variants are:

- all components
- without Data Quality
- without Drift
- without Update Safety
- without Reliability
- without Performance

## Method

The validation framework in `src/validation_framework.py` was used with the eight ground-truth scenarios defined in the same module. For each ablation, the remaining component weights were renormalized to sum to 1.0 while the excluded component was set to 0.0.

The comparison metrics were:

- Precision
- Recall
- F1
- FPR
- FNR

## Actual Results

The following results were measured from the real prototype using the actual validation scenarios and the actual scorer implementation.

| Variant | Precision | Recall | F1 | FPR | FNR | Correct / Total |
|---|---:|---:|---:|---:|---:|---:|
| all components | 0.500000 | 1.000000 | 0.666667 | 0.142857 | 0.000000 | 5 / 8 |
| without Data Quality | 0.500000 | 1.000000 | 0.666667 | 0.142857 | 0.000000 | 5 / 8 |
| without Drift | 0.500000 | 1.000000 | 0.666667 | 0.142857 | 0.000000 | 5 / 8 |
| without Update Safety | 0.500000 | 1.000000 | 0.666667 | 0.142857 | 0.000000 | 5 / 8 |
| without Reliability | 0.500000 | 1.000000 | 0.666667 | 0.142857 | 0.000000 | 5 / 8 |
| without Performance | 0.500000 | 1.000000 | 0.666667 | 0.142857 | 0.000000 | 5 / 8 |

## Interpretation

No ablation changed the measured metrics on this prototype validation set.

This means:

- Removing Data Quality did not worsen or improve the observed prototype performance.
- Removing Drift did not worsen or improve the observed prototype performance.
- Removing Update Safety did not worsen or improve the observed prototype performance.
- Removing Reliability did not worsen or improve the observed prototype performance.
- Removing Performance did not worsen or improve the observed prototype performance.

In other words, none of the tested components produced a measurable improvement over the full model on these eight validation scenarios, and none of them were individually required for the current prototype to achieve the same metrics.

## Conclusion

Under the current prototype and validation set, there is no evidence that any single score component contributes a measurable improvement.

The observed prototype behavior is effectively invariant to removal of any one component in this study, which means the component contribution is not supported by the current evidence.

This is not a claim that the components are useless in general; it is a claim that, on the provided validation set, each component failed to produce a measurable difference in the reported metrics.

## Evidence status

This conclusion is based on actual runs of the validation pipeline and not on fabricated or assumed improvements.
