import time

import pytest

from src.scoring_engines import TrustInput, TrustScorer


class TestFinalTrustScore:
    def test_exact_calculation_prototype_example(self):
        scorer = TrustScorer()
        values = {
            'dqs': 80,
            'dhs': 70,
            'uss': 90,
            'rs': 60,
            'ps': 80,
        }

        weights = {
            'dqs': 0.20,
            'dhs': 0.20,
            'uss': 0.30,
            'rs': 0.15,
            'ps': 0.15,
        }

        result = scorer.score(
            TrustInput(
                dqs=values['dqs'],
                dhs=values['dhs'],
                uss=values['uss'],
                rs=values['rs'],
                ps=values['ps'],
                confidence=80,
                hard_safety_passed=True,
                policy_approved=True,
                formula_version='initial-v1',
                weights=weights,
                timestamp=1700000000.0,
            )
        )

        expected_contributions = {
            'dqs': 16.0,
            'dhs': 14.0,
            'uss': 27.0,
            'rs': 9.0,
            'ps': 12.0,
        }

        assert result.score == pytest.approx(78.0)
        assert result.weights == weights
        assert result.raw_component_scores == values
        assert result.weighted_contributions == pytest.approx(expected_contributions)
        assert result.formula_version == 'initial-v1'
        assert result.timestamp == 1700000000.0
        assert result.decision == 'ALLOW'
        assert result.hard_safety_passed is True
        assert result.policy_approved is True

    def test_rejects_invalid_weight_configuration(self):
        scorer = TrustScorer()
        with pytest.raises(ValueError, match='must sum to exactly 1.0|must be exactly'):
            scorer.score(
                TrustInput(
                    dqs=80,
                    dhs=70,
                    uss=90,
                    rs=60,
                    ps=80,
                    confidence=80,
                    weights={'dqs': 0.20, 'dhs': 0.20, 'uss': 0.20, 'rs': 0.20, 'ps': 0.10},
                )
            )

    def test_requires_hard_safety_and_policy_checks(self):
        scorer = TrustScorer()
        result = scorer.score(
            TrustInput(
                dqs=80,
                dhs=70,
                uss=90,
                rs=60,
                ps=80,
                confidence=80,
                hard_safety_passed=False,
                policy_approved=True,
            )
        )
        assert result.decision == 'BLOCK'
        assert result.hard_safety_passed is False

        result2 = scorer.score(
            TrustInput(
                dqs=80,
                dhs=70,
                uss=90,
                rs=60,
                ps=80,
                confidence=80,
                hard_safety_passed=True,
                policy_approved=False,
            )
        )
        assert result2.decision == 'BLOCK'
        assert result2.policy_approved is False
