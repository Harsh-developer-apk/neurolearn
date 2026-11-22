from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal
from app.main import app
from app.models import AssessmentQuestion, AssessmentSession, LearnerSkillState
from app.seed.dsa_curriculum import DSA_COMPETENCIES, DSA_PREREQUISITES, DSA_PROFILE_ID, DSA_SKILLS, DSA_STUDY_ORDER
from app.seed.dsa_question_bank import DSA_QUESTION_BANK
from app.seed.question_bank import CS_QUESTION_BANK
from app.seed.seed_data import seed_database
from app.services.phase4_service import get_knowledge_graph_state, get_roadmap


client = TestClient(app)
QUESTION_BY_ID = {question["question_id"]: question for question in DSA_QUESTION_BANK}
SKILL_IDS = {skill_id for skill_id, *_ in DSA_SKILLS}
COMPETENCY_IDS = {competency_id for competency_id, *_ in DSA_COMPETENCIES}


def test_dsa_bank_has_unique_schema_valid_questions_for_every_topic():
    assert len(DSA_QUESTION_BANK) >= 100
    assert len(QUESTION_BY_ID) == len(DSA_QUESTION_BANK)
    assert len({question["question_text"].strip().lower() for question in DSA_QUESTION_BANK}) == len(DSA_QUESTION_BANK)
    topic_counts = Counter(question["skill_node_id"] for question in DSA_QUESTION_BANK)
    assert set(topic_counts) == SKILL_IDS
    assert all(count >= 10 for count in topic_counts.values())
    competency_by_skill = {skill_id: competency_id for skill_id, competency_id, *_ in DSA_SKILLS}
    for question in DSA_QUESTION_BANK:
        assert set(question) == set(CS_QUESTION_BANK[0])
        assert question["competency_id"] == competency_by_skill[question["skill_node_id"]]
        assert question["question_type"] in {"single_choice", "multiple_response", "scenario", "interpretation"}
        assert question["cognitive_level"] in {"recall", "understanding", "application", "analysis"}
        assert -2.0 <= question["difficulty"] <= 2.0
        assert [option["id"] for option in question["options"]] == ["A", "B", "C", "D"]
        assert len({option["text"] for option in question["options"]}) == 4
        assert set(question["correct_options"]) <= {"A", "B", "C", "D"}
        assert len(set(question["correct_options"])) == len(question["correct_options"])
        assert 0 < len(question["correct_options"]) < 4
        assert (len(question["correct_options"]) > 1) == (question["question_type"] == "multiple_response")
        assert question["explanation"] and question["misconception_tags"]
    for skill_id in SKILL_IDS:
        questions = [question for question in DSA_QUESTION_BANK if question["skill_node_id"] == skill_id]
        assert any(question["difficulty"] < -0.25 for question in questions)
        assert any(-0.25 <= question["difficulty"] <= 0.75 for question in questions)
        assert any(question["difficulty"] > 0.75 for question in questions)
        assert any(question["cognitive_level"] in {"application", "analysis"} for question in questions)


@pytest.mark.parametrize("answer_pattern", ["correct", "incorrect", "mixed"])
def test_fifteen_question_diagnostic_results_graph_and_roadmap_are_dsa_only(answer_pattern):
    started = client.post("/api/v1/assessment/start")
    assert started.status_code == 200
    data = started.json()
    assert data["total_questions"] == 15
    session_id = data["session_id"]
    question = data["question"]
    answered_ids = []
    expected_correct = 0

    while question:
        assert question["question_id"] in QUESTION_BY_ID
        assert question["skill_node_id"] in SKILL_IDS
        assert question["competency_id"] in COMPETENCY_IDS
        assert "correct_options" not in question and "correct_option" not in question
        answered_ids.append(question["question_id"])
        correct_options = QUESTION_BY_ID[question["question_id"]]["correct_options"]
        should_be_correct = answer_pattern == "correct" or (answer_pattern == "mixed" and len(answered_ids) % 2 == 0)
        selected_options = correct_options if should_be_correct else [next(option for option in ["A", "B", "C", "D"] if option not in correct_options)]
        expected_correct += int(should_be_correct)
        payload = {
            "question_id": question["question_id"],
            "selected_options": selected_options,
            "response_time_ms": 5000,
            "confidence": 3,
        }
        response = client.post(f"/api/v1/assessment/{session_id}/answer", json=payload)
        assert response.status_code == 200
        assert response.json()["correct"] is should_be_correct
        question = response.json()["next_question"]

    assert len(answered_ids) == len(set(answered_ids)) == 15
    result = client.get(f"/api/v1/assessment/{session_id}/result").json()
    assert result["profile_id"] == DSA_PROFILE_ID
    assert result["assessment"]["questions_answered"] == 15
    assert result["assessment"]["correct_count"] == expected_correct
    result_skill_ids = {skill["skill_node_id"] for skill in result["skills"]}
    assert result_skill_ids <= SKILL_IDS
    assert {QUESTION_BY_ID[question_id]["skill_node_id"] for question_id in answered_ids} <= result_skill_ids
    graph_response = client.get("/api/v1/learner/knowledge-graph")
    assert graph_response.status_code == 200
    graph = graph_response.json()
    assert graph["assessment_source"]["session_id"] == session_id
    assert {comp["competency_id"] for comp in graph["competencies"]} == COMPETENCY_IDS
    skills = [skill for competency in graph["competencies"] for skill in competency["skills"]]
    assert {skill["skill_node_id"] for skill in skills} == SKILL_IDS
    assert sum(skill["attempts"] for skill in skills) == 15
    for skill in skills:
        assert set(skill["prerequisites"]) <= SKILL_IDS
        if not skill["attempts"]:
            assert skill["mastery"] is None
            assert skill["evidence_status"] == "not_assessed"
    roadmap_response = client.get("/api/v1/learner/roadmap")
    assert roadmap_response.status_code == 200
    roadmap = roadmap_response.json()
    assert roadmap["assessment_source"]["session_id"] == session_id
    assert {item["skill_node_id"] for item in roadmap["all_candidates"]} == SKILL_IDS
    assert all(item["competency_id"] in COMPETENCY_IDS for item in roadmap["all_candidates"])
    assert all("recommended_course" not in item for item in roadmap["all_candidates"])
    assert roadmap["desired_goal_path"] == []


def test_curriculum_graph_is_dsa_only_and_has_no_prerequisite_cycles():
    response = client.get("/api/v1/competency-graph")
    assert response.status_code == 200
    graph = response.json()
    assert {comp["competency_id"] for comp in graph["competencies"]} == COMPETENCY_IDS
    assert {(edge["skill_node_id"], edge["prerequisite_skill_node_id"]) for edge in graph["relationships"] if edge["relationship_type"] == "prerequisite"} == set(DSA_PREREQUISITES)
    assert {(edge["skill_node_id"], edge["prerequisite_skill_node_id"]) for edge in graph["relationships"] if edge["relationship_type"] == "study_order"} == set(DSA_STUDY_ORDER)
    prerequisites = {skill_id: [] for skill_id in SKILL_IDS}
    for skill_id, prerequisite_id in DSA_PREREQUISITES + DSA_STUDY_ORDER:
        prerequisites[skill_id].append(prerequisite_id)

    def visit(skill_id, path):
        assert skill_id not in path
        for prerequisite_id in prerequisites[skill_id]:
            visit(prerequisite_id, path | {skill_id})

    for skill_id in SKILL_IDS:
        visit(skill_id, set())


def test_old_subject_history_is_preserved_without_affecting_new_dsa_evidence():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_database(db)
        db.add(AssessmentSession(session_id="OLD-CS", profile_id="PROFILE002", status="completed", theta=2.0))
        db.add(LearnerSkillState(profile_id="PROFILE002", skill_node_id="CS-SKILL-DSA", mastery_probability=0.99))
        db.commit()
        seed_database(db)
        graph = get_knowledge_graph_state(db)
        assert graph["assessment_source"]["session_id"] is None
        assert all(skill["mastery"] is None for comp in graph["competencies"] for skill in comp["skills"])
        assert all(item["mastery"] is None for item in get_roadmap(db)["all_candidates"])
        assert db.query(AssessmentSession).filter_by(session_id="OLD-CS").one().theta == 2.0
        assert db.query(LearnerSkillState).filter_by(profile_id="PROFILE002").one().mastery_probability == 0.99
        assert db.query(AssessmentQuestion).filter_by(profile_id=DSA_PROFILE_ID).count() == len(DSA_QUESTION_BANK)


def test_old_profile_cannot_start_a_diagnostic_or_reset_its_states():
    with SessionLocal() as db:
        before = [(state.id, state.mastery_probability) for state in db.query(LearnerSkillState).filter_by(profile_id="PROFILE002").all()]
    assert client.post("/api/v1/assessment/start?profile_id=PROFILE002").status_code == 400
    assert client.post("/api/v1/assessment/sample?profile_id=PROFILE002").status_code == 400
    with SessionLocal() as db:
        after = [(state.id, state.mastery_probability) for state in db.query(LearnerSkillState).filter_by(profile_id="PROFILE002").all()]
    assert before == after


def test_demo_diagnostic_uses_fifteen_dsa_questions():
    response = client.post("/api/v1/assessment/sample")
    assert response.status_code == 200
    result = response.json()
    assert result["profile_id"] == DSA_PROFILE_ID
    assert result["assessment_mode"] == "sample"
    assert result["assessment"]["questions_answered"] == 15
    assert all(skill["skill_node_id"] in SKILL_IDS for skill in result["skills"])
    assert client.get("/api/v1/learner/knowledge-graph").json()["assessment_source"]["session_id"] == result["session_id"]
