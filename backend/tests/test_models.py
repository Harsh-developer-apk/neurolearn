from app.services.bkt_service import L0, update_mastery_probability
from app.services.irt_service import probability_correct, update_theta


def test_irt_probability_at_baseline():
    assert probability_correct(theta=0, b=0) == 0.5


def test_irt_correct_answer_increases_theta():
    updated, _ = update_theta(theta=0, observed=1, b=0)
    assert updated > 0


def test_irt_incorrect_answer_decreases_theta():
    updated, _ = update_theta(theta=0, observed=0, b=0)
    assert updated < 0


def test_bkt_repeated_correct_answers_increase_mastery():
    mastery = L0
    for _ in range(3):
        mastery = update_mastery_probability(mastery, correct=True)
    assert mastery > L0


def test_bkt_repeated_incorrect_answers_limit_mastery():
    mastery = L0
    for _ in range(3):
        mastery = update_mastery_probability(mastery, correct=False)
    assert mastery < L0
