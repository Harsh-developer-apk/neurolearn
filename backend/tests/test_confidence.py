from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed.dsa_question_bank import DSA_QUESTION_BANK
from app.services.assessment_service import _evidence_adjusted_mastery, _skill_evidence
from app.services.bkt_service import L0, update_mastery_probability
from app.services.irt_service import update_theta


client = TestClient(app)
QUESTIONS = {question["question_id"]: question for question in DSA_QUESTION_BANK}


@pytest.mark.parametrize("difficulty", [-2.0, 0.0, 2.0])
def test_correct_guess_never_increases_theta(difficulty):
    updated, _ = update_theta(0.0, 1, difficulty, confidence=1)
    assert updated == 0.0
    assert update_theta(0.0, 1, difficulty, confidence=3)[0] > 0


def test_incorrect_guess_has_only_five_percent_of_normal_theta_effect():
    normal, _ = update_theta(0.0, 0, 0.0, confidence=3)
    guessed, _ = update_theta(0.0, 0, 0.0, confidence=1)
    assert guessed == pytest.approx(normal * 0.05)


@pytest.mark.parametrize("correct", [True, False])
def test_guessing_has_minimal_mastery_effect(correct):
    normal = update_mastery_probability(L0, correct, confidence=3)
    guessed = update_mastery_probability(L0, correct, confidence=1)
    assert guessed - L0 == pytest.approx((normal - L0) * 0.05, abs=0.0001)


def test_low_confidence_is_reduced_without_rewarding_overconfidence():
    normal, _ = update_theta(0, 1, 0, confidence=3)
    reduced, _ = update_theta(0, 1, 0, confidence=2)
    assert reduced == normal * 0.5
    assert update_theta(0, 1, 0, confidence=5)[0] == normal


def test_five_correct_guesses_cannot_establish_skill_mastery():
    rows = [(SimpleNamespace(correct=True, confidence=1, response_time_ms=1000), SimpleNamespace(cognitive_level="analysis", irt_b=1.0)) for _ in range(5)]
    evidence = _skill_evidence(rows)
    assert evidence["evidence_status"] == "uncertain"
    assert evidence["effective_attempts"] == 0
    assert evidence["guessing_attempts"] == 5
    assert not evidence["has_higher_cognitive_evidence"]
    assert _evidence_adjusted_mastery(0.99, evidence) <= L0


@pytest.mark.parametrize("correct", [True, False])
def test_api_applies_guessing_weights_and_preserves_correctness(correct):
    started = client.post("/api/v1/assessment/start").json()
    question = started["question"]
    answer = QUESTIONS[question["question_id"]]["correct_options"]
    chosen = answer if correct else [next(option for option in ["A", "B", "C", "D"] if option not in answer)]
    response = client.post(f"/api/v1/assessment/{started['session_id']}/answer", json={
        "question_id": question["question_id"], "selected_options": chosen, "response_time_ms": 1500, "confidence": 1,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["correct"] is correct
    assert data["response_evidence"]["evidence_weight"] == 0.05
    assert data["irt"]["theta"] <= data["irt"]["theta_before"]
    assert data["skill"]["effective_attempts"] == 0
    assert data["skill"]["guessing_attempts"] == 1
    assert abs(data["skill"]["mastery_probability"] - data["skill"]["mastery_before"]) < 0.025
    assert data["skill"]["evidence_status"] != "sufficient_mastery"


def test_fifteen_correct_guesses_keep_theta_unchanged_and_roadmap_requires_verification():
    started = client.post("/api/v1/assessment/start").json()
    session_id = started["session_id"]
    question = started["question"]
    answered = 0
    while question:
        response = client.post(f"/api/v1/assessment/{session_id}/answer", json={
            "question_id": question["question_id"],
            "selected_options": QUESTIONS[question["question_id"]]["correct_options"],
            "response_time_ms": 1000,
            "confidence": 1,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["irt"]["theta"] == 0
        answered += 1
        question = data["next_question"]
    assert answered == 15
    result = client.get(f"/api/v1/assessment/{session_id}/result").json()
    assert result["assessment"]["correct_count"] == 15
    assert result["irt"]["theta"] == 0
    assert all(skill["evidence_status"] != "sufficient_mastery" for skill in result["skills"])
    assert all(competency["evidence_status"] == "early" for competency in result["competencies"])
    graph = client.get("/api/v1/learner/knowledge-graph").json()
    assert all(skill["mastery"] is None or skill["mastery"] <= L0 for comp in graph["competencies"] for skill in comp["skills"])
    roadmap = client.get("/api/v1/learner/roadmap").json()
    assert all(item["action"] == "verify" for item in roadmap["learning_path"])
    assert roadmap["already_covered"] == []
