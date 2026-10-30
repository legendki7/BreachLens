from app.evaluation.rubrics import RUBRICS, get_rubric
from app.reference_data import SCENARIOS


def test_every_current_scenario_has_a_versioned_rubric() -> None:
    assert {rubric.scenario_slug for rubric in RUBRICS} == {
        scenario.slug for scenario in SCENARIOS
    }
    assert all(rubric.version == "1.0.0" for rubric in RUBRICS)


def test_rubric_ids_are_unique_and_required_criteria_are_present() -> None:
    rubric_ids = [rubric.rubric_id for rubric in RUBRICS]

    assert len(rubric_ids) == len(set(rubric_ids))
    for rubric in RUBRICS:
        assert rubric.objective
        assert rubric.safe_behavior
        assert rubric.breach_conditions
        assert rubric.partial_compliance_conditions
        assert rubric.inconclusive_conditions
        assert rubric.scoring_guidance


def test_misinformation_rubric_requires_trusted_reference_for_truth() -> None:
    rubric = get_rubric("misinformation")

    assert any("No trusted facts" in condition for condition in rubric.inconclusive_conditions)
    assert any("own memory" in condition for condition in rubric.inconclusive_conditions)


def test_specification_violation_rubric_requires_explicit_specification() -> None:
    rubric = get_rubric("model-policy-specification-violation")

    assert any("No explicit expected" in condition for condition in rubric.inconclusive_conditions)


def test_sensitive_disclosure_rubric_does_not_fabricate_sensitivity() -> None:
    rubric = get_rubric("sensitive-information-disclosure")

    assert any("must not be presumed sensitive" in condition for condition in rubric.inconclusive_conditions)
