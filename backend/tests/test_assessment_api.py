from fastapi.testclient import TestClient

from app.main import app
from app.seed.dsa_curriculum import DSA_PROFILE_ID
from app.seed.dsa_question_bank import DSA_QUESTION_BANK


client = TestClient(app)


def answer_payload(question, selected):
    payload = {
        "question_id": question["question_id"],
        "response_time_ms": 4200,
        "confidence": 3,
    }
    if question["response_mode"] == "multiple":
        payload["selected_options"] = selected if isinstance(selected, list) else [selected]
    else:
        payload["selected_option"] = selected if isinstance(selected, str) else selected[0]
    return payload


def test_start_assessment_hides_correct_answer():
    response = client.post("/api/v1/assessment/start")
    assert response.status_code == 200
    data = response.json()
    assert data["total_questions"] == 15
    assert "correct_option" not in data["question"]
    assert "correct_options" not in data["question"]
    assert set(data["question"]["options"].keys()) == {"A", "B", "C", "D"}
    assert data["question"]["difficulty"] in [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
    assert data["model_state"]["irt"]["theta"] == 0.0


def test_statistics_profile_is_removed_and_default_pool_is_dsa():
    stats = client.post("/api/v1/assessment/start?profile_id=PROFILE001")
    cs = client.post("/api/v1/assessment/start")

    assert stats.status_code == 404
    assert client.get("/api/v1/profiles/PROFILE001").status_code == 404
    assert [profile["profile_id"] for profile in client.get("/api/v1/profiles").json()] == [DSA_PROFILE_ID]
    assert cs.status_code == 200

    cs_question = cs.json()["question"]

    assert cs_question["competency_id"].startswith("COMP-DSA-")
    assert cs_question["question_id"].startswith("DSAQ")


def test_answer_is_stored_and_duplicate_is_rejected():
    session = client.post("/api/v1/assessment/start").json()
    session_id = session["session_id"]
    question_id = session["question"]["question_id"]

    payload = answer_payload(session["question"], "A")
    first = client.post(f"/api/v1/assessment/{session_id}/answer", json=payload)
    assert first.status_code == 200

    duplicate = client.post(f"/api/v1/assessment/{session_id}/answer", json=payload)
    assert duplicate.status_code == 400


def test_assessment_stops_after_15_questions_and_next_question_hides_answer():
    session = client.post("/api/v1/assessment/start").json()
    session_id = session["session_id"]
    question = session["question"]
    answered = 0

    while question:
        response = client.post(
            f"/api/v1/assessment/{session_id}/answer",
            json={
                **answer_payload(question, "A"),
                "response_time_ms": 3000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        answered = data["progress"]["current"]
        question = data["next_question"]
        if question:
            assert "correct_option" not in question

    assert answered == 15

    result = client.get(f"/api/v1/assessment/{session_id}/result")
    assert result.status_code == 200
    assert result.json()["assessment"]["questions_answered"] == 15


def test_multiple_response_all_or_nothing_scoring():
    session = client.post("/api/v1/assessment/start").json()
    session_id = session["session_id"]
    question = session["question"]
    correct_answers = {item["question_id"]: item["correct_options"] for item in DSA_QUESTION_BANK}

    while question and question["response_mode"] != "multiple":
        response = client.post(
            f"/api/v1/assessment/{session_id}/answer",
            json=answer_payload(question, correct_answers[question["question_id"]]),
        )
        assert response.status_code == 200
        question = response.json()["next_question"]

    assert question is not None
    partial = client.post(
        f"/api/v1/assessment/{session_id}/answer",
        json=answer_payload(question, ["A"]),
    )
    assert partial.status_code == 200
    assert partial.json()["correct"] is False
