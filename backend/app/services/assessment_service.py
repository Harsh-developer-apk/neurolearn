import json
from collections import defaultdict
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AssessmentQuestion, AssessmentResponse, AssessmentSession, Competency, LearnerSkillState, SkillNode, SkillPrerequisite
from app.seed.question_bank import PROFILE_ACTIVE_COMPETENCY_IDS
from app.services.competency_service import get_required_competencies
from app.services.bkt_service import L0, update_mastery_probability
from app.services.irt_service import ability_label, probability_correct, update_theta
from app.services.confidence_service import response_weight
from app.services.profile_service import PROTOTYPE_PROFILE_ID, get_prototype_profile


MAX_QUESTIONS = 15
MIN_SKILL_EVIDENCE = 2
MAX_SKILL_EVIDENCE = 5
HIGHER_COGNITIVE_LEVELS = {"application", "analysis"}


def _active_competency_ids(db: Session, profile_id: str) -> set[str]:
    configured = PROFILE_ACTIVE_COMPETENCY_IDS.get(profile_id)
    if configured:
        return configured
    return {item["competency_id"] for item in get_required_competencies(db, profile_id)}


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _response_mode(question: AssessmentQuestion) -> str:
    return "multiple" if len(_json_list(question.correct_options)) > 1 or question.question_type == "multiple_response" else "single"


def public_question(question: AssessmentQuestion) -> dict:
    return {
        "question_id": question.question_id,
        "question_text": question.question_text,
        "options": {
            "A": question.option_a,
            "B": question.option_b,
            "C": question.option_c,
            "D": question.option_d,
        },
        "question_type": question.question_type,
        "response_mode": _response_mode(question),
        "cognitive_level": question.cognitive_level,
        "difficulty": question.irt_b,
        "competency_id": question.competency_id,
        "skill_node_id": question.skill_node_id,
    }


def _session_responses(db: Session, session_id: str) -> list[AssessmentResponse]:
    return (
        db.query(AssessmentResponse)
        .filter(AssessmentResponse.session_id == session_id)
        .order_by(AssessmentResponse.sequence_number)
        .all()
    )


def _answered_question_ids(responses: list[AssessmentResponse]) -> set[str]:
    return {response.question_id for response in responses}


def _skill_response_map(db: Session, session_id: str) -> dict[str, list[tuple[AssessmentResponse, AssessmentQuestion]]]:
    rows = (
        db.query(AssessmentResponse, AssessmentQuestion)
        .join(AssessmentQuestion, AssessmentResponse.question_id == AssessmentQuestion.question_id)
        .filter(AssessmentResponse.session_id == session_id)
        .order_by(AssessmentResponse.sequence_number)
        .all()
    )
    grouped: dict[str, list[tuple[AssessmentResponse, AssessmentQuestion]]] = defaultdict(list)
    for response, question in rows:
        grouped[response.skill_node_id].append((response, question))
    return grouped


def _state_by_skill(db: Session, profile_id: str) -> dict[str, LearnerSkillState]:
    return {
        state.skill_node_id: state
        for state in db.query(LearnerSkillState).filter(LearnerSkillState.profile_id == profile_id).all()
    }


def _active_skills(db: Session, profile_id: str) -> list[tuple[SkillNode, Competency]]:
    active_competency_ids = _active_competency_ids(db, profile_id)
    return (
        db.query(SkillNode, Competency)
        .join(Competency, SkillNode.competency_id == Competency.competency_id)
        .filter(SkillNode.competency_id.in_(active_competency_ids))
        .order_by(Competency.competency_id, SkillNode.difficulty_level, SkillNode.skill_node_id)
        .all()
    )


def _skill_evidence(rows: list[tuple[AssessmentResponse, AssessmentQuestion]]) -> dict:
    attempts = len(rows)
    correct = sum(1 for response, _ in rows if response.correct)
    confidence_avg = round(sum(response.confidence for response, _ in rows) / attempts, 2) if attempts else 0.0
    avg_time = round(sum(response.response_time_ms for response, _ in rows) / attempts, 1) if attempts else 0.0
    reliable_rows = [(response, question) for response, question in rows if response.confidence > 1]
    effective_attempts = sum(response_weight(response.confidence) for response, _ in reliable_rows)
    effective_correct = sum(response_weight(response.confidence) for response, _ in reliable_rows if response.correct)
    has_higher = any(question.cognitive_level in HIGHER_COGNITIVE_LEVELS for _, question in reliable_rows)
    has_nontrivial = any(question.irt_b >= 0.0 for _, question in reliable_rows)

    if attempts == 0:
        status = "limited_evidence"
        decision = "Gather evidence"
    elif attempts >= MAX_SKILL_EVIDENCE:
        status = "sufficient_mastery" if effective_correct >= 4 and has_higher else "uncertain"
        decision = "Stop skill - maximum evidence reached"
    elif effective_attempts >= 3 and effective_correct == effective_attempts and has_higher and has_nontrivial:
        status = "sufficient_mastery"
        decision = "Skill evidence sufficient"
    elif effective_attempts >= 3 and effective_correct == 0:
        status = "weak"
        decision = "Skill appears weak"
    elif effective_attempts >= 3 and effective_correct <= 1:
        status = "weak"
        decision = "Weak evidence"
    elif effective_attempts < MIN_SKILL_EVIDENCE:
        status = "gathering_evidence"
        decision = "Continue skill"
    else:
        status = "uncertain"
        decision = "Skill remains uncertain"

    return {
        "attempts": attempts,
        "correct_attempts": correct,
        "effective_attempts": round(effective_attempts, 4),
        "effective_correct_attempts": round(effective_correct, 4),
        "guessing_attempts": attempts - len(reliable_rows),
        "incorrect_attempts": attempts - correct,
        "confidence_avg": confidence_avg,
        "avg_response_time_ms": avg_time,
        "has_higher_cognitive_evidence": has_higher,
        "evidence_status": status,
        "decision": decision,
    }


def _evidence_adjusted_mastery(raw_mastery: float, evidence: dict) -> float:
    attempts = evidence.get("effective_attempts", evidence["attempts"])
    if attempts <= 0:
        return round(min(raw_mastery, L0), 4)

    accuracy = evidence.get("effective_correct_attempts", evidence["correct_attempts"]) / attempts
    status = evidence["evidence_status"]
    has_higher = evidence["has_higher_cognitive_evidence"]

    if status == "weak":
        cap = 0.35
    elif status == "uncertain":
        cap = 0.60
    elif status in {"limited_evidence", "gathering_evidence"}:
        cap = 0.50
    elif status == "sufficient_mastery":
        cap = 1.0
    else:
        cap = 0.65

    evidence_weight = min(1.0, attempts / 3)
    cognitive_weight = 1.0 if has_higher else 0.85
    accuracy_anchor = 0.15 + (accuracy * 0.75)
    adjusted = min(raw_mastery, accuracy_anchor * evidence_weight * cognitive_weight, cap)
    return round(max(0.0, min(1.0, adjusted)), 4)


def _prerequisite_penalty(db: Session, skill_node_id: str, skill_evidence: dict[str, dict]) -> float:
    prerequisites = (
        db.query(SkillPrerequisite.prerequisite_skill_node_id)
        .filter(SkillPrerequisite.skill_node_id == skill_node_id, SkillPrerequisite.relationship_type == "prerequisite")
        .all()
    )
    penalty = 0.0
    for row in prerequisites:
        status = skill_evidence.get(row.prerequisite_skill_node_id, {}).get("evidence_status")
        if status in {None, "limited_evidence", "gathering_evidence"}:
            penalty += 1.0
        elif status == "weak":
            penalty += 1.5
    return penalty


def _skill_uncertainty(state: LearnerSkillState | None, evidence: dict) -> float:
    if not state:
        return 0.75
    if evidence["evidence_status"] == "uncertain":
        return 1.0
    if evidence["evidence_status"] == "gathering_evidence":
        return 0.9
    return 1 - abs(state.mastery_probability - 0.5) * 2


def _preferred_cognitive_bonus(question: AssessmentQuestion, evidence: dict) -> float:
    attempts = evidence["attempts"]
    if attempts == 0 and question.cognitive_level in {"recall", "understanding"}:
        return 0.35
    if attempts >= 1 and question.cognitive_level in {"application", "analysis"}:
        return 0.45
    return 0.0


def _current_skill_id(responses: list[AssessmentResponse]) -> str | None:
    return responses[-1].skill_node_id if responses else None


def select_next_question(db: Session, session: AssessmentSession) -> AssessmentQuestion | None:
    if session.current_question_number >= session.max_questions:
        return None

    responses = _session_responses(db, session.session_id)
    answered_ids = _answered_question_ids(responses)
    grouped = _skill_response_map(db, session.session_id)
    skill_evidence = {skill_id: _skill_evidence(rows) for skill_id, rows in grouped.items()}
    states = _state_by_skill(db, session.profile_id)
    active_competency_ids = _active_competency_ids(db, session.profile_id)
    active_skill_ids = [skill.skill_node_id for skill, _ in _active_skills(db, session.profile_id)]

    candidates = (
        db.query(AssessmentQuestion)
        .filter(
            AssessmentQuestion.profile_id == session.profile_id,
            AssessmentQuestion.competency_id.in_(active_competency_ids),
            AssessmentQuestion.skill_node_id.in_(active_skill_ids),
        )
        .all()
    )
    candidates = [question for question in candidates if question.question_id not in answered_ids]
    if session.scope_skill_node_id:
        generated_prefix = f"AIQ-{session.session_id}-"
        candidates = [
            question for question in candidates
            if question.skill_node_id == session.scope_skill_node_id and question.question_id.startswith(generated_prefix)
        ]
    if not candidates:
        return None

    current_skill = _current_skill_id(responses)
    question_number = session.current_question_number

    def score(question: AssessmentQuestion) -> tuple[float, str]:
        evidence = skill_evidence.get(question.skill_node_id, _skill_evidence([]))
        status = evidence["evidence_status"]
        attempts = evidence["attempts"]
        if status in {"sufficient_mastery", "weak"} or attempts >= MAX_SKILL_EVIDENCE:
            return (-1000.0, question.question_id)

        state = states.get(question.skill_node_id)
        coverage_bonus = 0.0
        if question_number < 5:
            assessed_competencies = {
                db.query(AssessmentQuestion.competency_id)
                .filter(AssessmentQuestion.question_id == response.question_id)
                .scalar()
                for response in responses
            }
            if question.competency_id not in assessed_competencies:
                coverage_bonus += 1.2
            if attempts == 0:
                coverage_bonus += 0.5

        continue_bonus = 0.35 if current_skill == question.skill_node_id and status in {"gathering_evidence", "uncertain"} else 0.0
        min_evidence_bonus = 0.8 if 0 < attempts < MIN_SKILL_EVIDENCE else 0.0
        uncertainty_bonus = _skill_uncertainty(state, evidence)
        prereq_penalty = _prerequisite_penalty(db, question.skill_node_id, skill_evidence)
        cognitive_bonus = _preferred_cognitive_bonus(question, evidence)
        difficulty_distance = abs(question.irt_b - session.theta)

        difficulty_bonus = max(0.0, 1.25 - difficulty_distance)
        progression_bonus = 0.0
        if responses and responses[-1].correct and question.irt_b >= session.theta - 0.25:
            progression_bonus = 0.25
        if question.question_type in {"scenario", "interpretation", "multiple_response"}:
            progression_bonus += 0.1

        total = (
            coverage_bonus
            + continue_bonus
            + min_evidence_bonus
            + uncertainty_bonus
            + cognitive_bonus
            + difficulty_bonus
            + progression_bonus
            - prereq_penalty
            - attempts * 0.12
        )
        return (round(total, 4), question.question_id)

    return sorted(candidates, key=score, reverse=True)[0]


def _model_state(db: Session, session: AssessmentSession, question: AssessmentQuestion | None = None, decision: str = "Begin diagnostic") -> dict:
    grouped = _skill_response_map(db, session.session_id)
    states = _state_by_skill(db, session.profile_id)

    competencies: dict[str, dict] = {}
    for skill, competency in _active_skills(db, session.profile_id):
        evidence = _skill_evidence(grouped.get(skill.skill_node_id, []))
        state = states.get(skill.skill_node_id)
        skill_payload = {
            "skill_node_id": skill.skill_node_id,
            "name": skill.name,
            "mastery_probability": state.mastery_probability if state else None,
            "attempts": evidence["attempts"],
            "correct_attempts": evidence["correct_attempts"],
            "effective_attempts": evidence["effective_attempts"],
            "guessing_attempts": evidence["guessing_attempts"],
            "confidence_avg": evidence["confidence_avg"],
            "avg_response_time_ms": evidence["avg_response_time_ms"],
            "evidence_status": evidence["evidence_status"],
        }
        competencies.setdefault(
            competency.competency_id,
            {
                "competency_id": competency.competency_id,
                "name": competency.name,
                "skills": [],
            },
        )["skills"].append(skill_payload)

    current_skill = None
    if question:
        skill = db.query(SkillNode).filter(SkillNode.skill_node_id == question.skill_node_id).first()
        competency = db.query(Competency).filter(Competency.competency_id == question.competency_id).first()
        evidence = _skill_evidence(grouped.get(question.skill_node_id, []))
        state = states.get(question.skill_node_id)
        current_skill = {
            "skill_node_id": question.skill_node_id,
            "skill_name": skill.name if skill else question.skill_node_id,
            "competency_id": question.competency_id,
            "competency_name": competency.name if competency else question.competency_id,
            "bkt_mastery": state.mastery_probability if state else L0,
            "attempts": evidence["attempts"],
            "correct_attempts": evidence["correct_attempts"],
            "confidence_avg": evidence["confidence_avg"],
            "avg_response_time_ms": evidence["avg_response_time_ms"],
            "evidence_status": evidence["evidence_status"],
        }

    return {
        "irt": {
            "theta": round(session.theta, 4),
            "ability_label": ability_label(session.theta),
            "question_difficulty": question.irt_b if question else None,
            "estimated_probability": round(probability_correct(session.theta, question.irt_b), 4) if question else None,
        },
        "current_skill": current_skill,
        "question": {
            "question_type": question.question_type,
            "response_mode": _response_mode(question),
            "cognitive_level": question.cognitive_level,
            "difficulty": question.irt_b,
        } if question else None,
        "decision": decision,
        "competencies": list(competencies.values()),
    }


def _validate_assessment_profile(db: Session, profile_id: str):
    get_prototype_profile(db, profile_id)
    if profile_id not in PROFILE_ACTIVE_COMPETENCY_IDS:
        raise HTTPException(status_code=400, detail="Only the DSA diagnostic is currently available")


def start_assessment(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID, assessment_mode: str = "live"):
    _validate_assessment_profile(db, profile_id)
    session = AssessmentSession(
        session_id=f"{'SAMPLE' if assessment_mode == 'sample' else 'SESSION'}{uuid4().hex[:8].upper()}",
        profile_id=profile_id,
        status="in_progress",
        current_question_number=0,
        max_questions=MAX_QUESTIONS,
        theta=0.0,
        assessment_mode=assessment_mode,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    question = select_next_question(db, session)
    if not question:
        raise HTTPException(status_code=500, detail="No diagnostic questions available")

    return {
        "session_id": session.session_id,
        "question_number": 1,
        "total_questions": session.max_questions,
        "question": public_question(question),
        "model_state": _model_state(db, session, question),
    }


def start_topic_assessment(db: Session, profile_id: str, skill_node_id: str):
    _validate_assessment_profile(db, profile_id)
    skill = db.query(SkillNode).filter(SkillNode.skill_node_id == skill_node_id).first()
    if not skill or skill_node_id not in {row[0].skill_node_id for row in _active_skills(db, profile_id)}:
        raise HTTPException(status_code=404, detail="Unknown DSA topic")

    session_id = f"TOPIC{uuid4().hex[:8].upper()}"
    from app.services.topic_assessment_service import generate_topic_questions
    try:
        questions, provider, model = generate_topic_questions(db, profile_id, skill, session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if len(questions) < 4:
        raise HTTPException(status_code=502, detail="The model generated too few valid assessment questions. Please try again.")
    db.add_all(questions)
    session = AssessmentSession(
        session_id=session_id,
        profile_id=profile_id,
        status="in_progress",
        current_question_number=0,
        max_questions=len(questions),
        theta=0.0,
        assessment_mode="topic",
        scope_skill_node_id=skill_node_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    question = select_next_question(db, session)
    if not question:
        raise HTTPException(status_code=500, detail="No generated topic questions available")
    return {
        "session_id": session.session_id,
        "question_number": 1,
        "total_questions": session.max_questions,
        "question": public_question(question),
        "model_state": _model_state(db, session, question, "Begin topic assessment"),
        "topic": {"skill_node_id": skill.skill_node_id, "name": skill.name},
        "question_provider": provider,
        "question_model": model,
    }


def _sample_answer_for_question(question: AssessmentQuestion, sequence_number: int, profile_id: str) -> dict:
    correct_options = sorted(_json_list(question.correct_options) or [question.correct_option])
    wrong_option = next(option for option in ["A", "B", "C", "D"] if option not in correct_options)

    profile_skill_pattern = {
        PROTOTYPE_PROFILE_ID: {
            "DSA-COMPLEXITY": [True, True, True, False],
            "DSA-ARRAYS": [True, True, False, True],
            "DSA-LINKED": [False, True, False],
            "DSA-STACKS": [True, True, False],
            "DSA-HASHING": [True, False, True],
            "DSA-SEARCH-SORT": [True, False, True],
            "DSA-TREES": [False, True, False],
            "DSA-GRAPHS": [False, False, True],
            "DSA-RECURSION": [True, True, False],
            "DSA-GREEDY-DP": [False, False, True],
        },
        "PROFILE002": {
            "CS-SKILL-OOPS": [True, True, True, False],
            "CS-SKILL-DSA": [True, False, True, False, True],
            "CS-SKILL-PROBLEM": [True, True, False],
            "CS-SKILL-DBMS": [False, False, True, False],
            "CS-SKILL-OS": [False, True, False],
        },
    }
    fallback_pattern = [True, False, True, False, True, False]
    pattern = profile_skill_pattern.get(profile_id, {}).get(question.skill_node_id, fallback_pattern)
    should_be_correct = pattern[sequence_number % len(pattern)]

    confidence_pattern = [4, 5, 3, 2, 4, 1, 5, 3, 2, 4, 5, 2, 3, 4, 1]
    time_pattern = [18400, 42100, 25300, 17200, 33600, 28700, 51200, 22400, 39700, 30600, 46200, 19500, 35800, 27800, 44100]
    confidence = confidence_pattern[sequence_number % len(confidence_pattern)]
    response_time_ms = time_pattern[sequence_number % len(time_pattern)]

    selected_options = correct_options if should_be_correct else [wrong_option]
    return {
        "question_id": question.question_id,
        "selected_options": selected_options,
        "is_correct": selected_options == correct_options,
        "time_taken_seconds": round(response_time_ms / 1000, 1),
        "response_time_ms": response_time_ms,
        "confidence": confidence,
        "cognitive_level": question.cognitive_level,
        "question_difficulty": question.difficulty,
        "irt_b": question.irt_b,
        "skill_node_id": question.skill_node_id,
        "competency_id": question.competency_id,
    }


def _sample_answer_dataset(db: Session, profile_id: str) -> dict[str, dict]:
    questions = (
        db.query(AssessmentQuestion)
        .filter(
            AssessmentQuestion.profile_id == profile_id,
            AssessmentQuestion.competency_id.in_(_active_competency_ids(db, profile_id)),
        )
        .order_by(AssessmentQuestion.question_id)
        .all()
    )
    return {
        question.question_id: _sample_answer_for_question(question, index, profile_id)
        for index, question in enumerate(questions)
    }


def run_sample_assessment(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    _validate_assessment_profile(db, profile_id)
    db.query(LearnerSkillState).filter(LearnerSkillState.profile_id == profile_id).delete()
    db.commit()

    started = start_assessment(db, profile_id, assessment_mode="sample")
    session_id = started["session_id"]
    question = started["question"]
    final_submission = None
    sample_answers = _sample_answer_dataset(db, profile_id)
    sequence_number = 0

    while question:
        sample_answer = sample_answers[question["question_id"]]
        payload = {
            "db": db,
            "session_id": session_id,
            "question_id": question["question_id"],
            "response_time_ms": sample_answer["response_time_ms"],
            "confidence": sample_answer["confidence"],
        }
        if question["response_mode"] == "multiple":
            payload["selected_options"] = sample_answer["selected_options"]
        else:
            payload["selected_option"] = sample_answer["selected_options"][0]
        final_submission = submit_answer(**payload)
        question = final_submission["next_question"]
        sequence_number += 1

    result = get_assessment_result(db, session_id)
    result["sample_submission_summary"] = {
        "answers_submitted": sequence_number,
        "last_decision": final_submission["decision"] if final_submission else "Assessment complete",
    }
    return result


def _normalize_selected_options(question: AssessmentQuestion, selected_option: str | None, selected_options: list[str] | None) -> list[str]:
    values = selected_options if selected_options is not None else ([selected_option] if selected_option else [])
    normalized = sorted({value for value in values if value in {"A", "B", "C", "D"}})
    if _response_mode(question) == "single" and len(normalized) != 1:
        raise HTTPException(status_code=422, detail="Select exactly one option")
    if _response_mode(question) == "multiple" and not normalized:
        raise HTTPException(status_code=422, detail="Select at least one option")
    return normalized


def submit_answer(
    db: Session,
    session_id: str,
    question_id: str,
    selected_option: str | None = None,
    response_time_ms: int = 0,
    selected_options: list[str] | None = None,
    confidence: int = 3,
):
    session = db.query(AssessmentSession).filter(AssessmentSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Assessment session not found")
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Assessment session is already completed")

    question = db.query(AssessmentQuestion).filter(AssessmentQuestion.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.profile_id != session.profile_id or question.competency_id not in _active_competency_ids(db, session.profile_id):
        raise HTTPException(status_code=400, detail="Question is outside active diagnostic scope")
    if session.scope_skill_node_id and question.skill_node_id != session.scope_skill_node_id:
        raise HTTPException(status_code=400, detail="Question is outside this topic assessment")

    already_answered = (
        db.query(AssessmentResponse)
        .filter(
            AssessmentResponse.session_id == session_id,
            AssessmentResponse.question_id == question_id,
        )
        .first()
    )
    if already_answered:
        raise HTTPException(status_code=400, detail="Question already answered in this session")

    normalized_selected = _normalize_selected_options(question, selected_option, selected_options)
    correct_options = sorted(_json_list(question.correct_options) or [question.correct_option])
    correct = normalized_selected == correct_options

    theta_before = session.theta
    estimated_probability = probability_correct(theta_before, question.irt_b)
    new_theta, _ = update_theta(theta_before, 1 if correct else 0, question.irt_b, confidence=confidence)
    session.theta = round(new_theta, 4)
    session.current_question_number += 1

    state = (
        db.query(LearnerSkillState)
        .filter(
            LearnerSkillState.profile_id == session.profile_id,
            LearnerSkillState.skill_node_id == question.skill_node_id,
        )
        .first()
    )
    mastery_before = state.mastery_probability if state else L0
    mastery_after = update_mastery_probability(mastery_before, correct, confidence)

    if not state:
        state = LearnerSkillState(
            profile_id=session.profile_id,
            skill_node_id=question.skill_node_id,
            mastery_probability=mastery_after,
            attempts=0,
            correct_attempts=0,
        )
        db.add(state)
    else:
        state.mastery_probability = mastery_after
    state.attempts += 1
    if correct:
        state.correct_attempts += 1
    state.last_updated = datetime.utcnow()

    response = AssessmentResponse(
        session_id=session.session_id,
        question_id=question.question_id,
        skill_node_id=question.skill_node_id,
        selected_option=normalized_selected[0],
        selected_options=json.dumps(normalized_selected),
        correct_options=json.dumps(correct_options),
        correct=correct,
        response_time_ms=response_time_ms,
        confidence=confidence,
        irt_theta_before=round(theta_before, 4),
        irt_theta_after=session.theta,
        bkt_mastery_before=round(mastery_before, 4),
        bkt_mastery_after=round(mastery_after, 4),
        sequence_number=session.current_question_number,
        created_at=datetime.utcnow(),
    )
    db.add(response)
    db.flush()

    grouped = _skill_response_map(db, session.session_id)
    evidence = _skill_evidence(grouped.get(question.skill_node_id, []))

    next_question = None
    if session.current_question_number >= session.max_questions:
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        decision = "Assessment complete"
    else:
        next_question = select_next_question(db, session)
        if not next_question:
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            decision = "Assessment complete"
        elif next_question.skill_node_id == question.skill_node_id:
            decision = evidence["decision"]
        else:
            decision = f"{evidence['decision']} - move to {next_question.skill_node_id}"

    db.commit()

    return {
        "correct": correct,
        "explanation": question.explanation,
        "progress": {
            "current": session.current_question_number,
            "total": session.max_questions,
        },
        "irt": {
            "theta": session.theta,
            "theta_before": round(theta_before, 4),
            "estimated_probability": round(estimated_probability, 4),
        },
        "skill": {
            "skill_node_id": state.skill_node_id,
            "mastery_probability": state.mastery_probability,
            "mastery_before": round(mastery_before, 4),
            "effective_attempts": evidence["effective_attempts"],
            "guessing_attempts": evidence["guessing_attempts"],
            "evidence_status": evidence["evidence_status"],
            "attempts": evidence["attempts"],
            "correct_attempts": evidence["correct_attempts"],
        },
        "next_question": public_question(next_question) if next_question else None,
        "model_state": _model_state(db, session, next_question or question, decision),
        "decision": decision,
        "response_evidence": {
            "question_id": question.question_id,
            "skill_node_id": question.skill_node_id,
            "selected_options": normalized_selected,
            "is_correct": correct,
            "response_time_ms": response_time_ms,
            "confidence": confidence,
            "evidence_weight": response_weight(confidence),
            "theta_update_weight": 0.0 if confidence == 1 and correct else response_weight(confidence),
            "weighting_reason": "Guessing: no positive ability update and minimal mastery influence" if confidence == 1 else "Low confidence: reduced influence" if confidence == 2 else "Standard evidence influence",
            "irt_theta_before": round(theta_before, 4),
            "irt_theta_after": session.theta,
            "bkt_mastery_before": round(mastery_before, 4),
            "bkt_mastery_after": round(mastery_after, 4),
            "misconception_tags": _json_list(question.misconception_tags) if not correct and confidence > 1 else [],
            "timestamp": response.created_at.isoformat(),
        },
    }


def _confidence_analysis(responses: list[AssessmentResponse]) -> dict:
    if not responses:
        return {
            "average_confidence": 0.0,
            "correct_high_confidence": 0,
            "correct_low_confidence": 0,
            "incorrect_high_confidence": 0,
            "incorrect_low_confidence": 0,
        }
    return {
        "average_confidence": round(sum(response.confidence for response in responses) / len(responses), 2),
        "correct_high_confidence": sum(1 for response in responses if response.correct and response.confidence >= 4),
        "correct_low_confidence": sum(1 for response in responses if response.correct and response.confidence <= 2),
        "incorrect_high_confidence": sum(1 for response in responses if not response.correct and response.confidence >= 4),
        "incorrect_low_confidence": sum(1 for response in responses if not response.correct and response.confidence <= 2),
    }


def get_assessment_result(db: Session, session_id: str):
    session = db.query(AssessmentSession).filter(AssessmentSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Assessment session not found")

    responses = _session_responses(db, session_id)
    correct_count = sum(1 for response in responses if response.correct)
    accuracy = round(correct_count / len(responses), 4) if responses else 0.0
    avg_time = round(sum(response.response_time_ms for response in responses) / len(responses), 1) if responses else 0.0
    confidence = _confidence_analysis(responses)
    skills = get_skill_mastery_states(db, session.profile_id, session_id)
    competencies = _competency_summary(skills)

    misconception_signals = []
    for response, question in (
        db.query(AssessmentResponse, AssessmentQuestion)
        .join(AssessmentQuestion, AssessmentResponse.question_id == AssessmentQuestion.question_id)
        .filter(AssessmentResponse.session_id == session_id, AssessmentResponse.correct == False, AssessmentResponse.confidence > 1)  # noqa: E712
        .all()
    ):
        tags = _json_list(question.misconception_tags)
        if tags:
            misconception_signals.append({
                "question_id": question.question_id,
                "skill_node_id": question.skill_node_id,
                "tags": tags,
                "label": "Potential misconception signal",
            })

    return {
        "session_id": session.session_id,
        "profile_id": session.profile_id,
        "assessment_mode": session.assessment_mode,
        "scope_skill_node_id": session.scope_skill_node_id,
        "assessment": {
            "questions_answered": len(responses),
            "accuracy": accuracy,
            "correct_count": correct_count,
            "incorrect_count": len(responses) - correct_count,
            "average_response_time_ms": avg_time,
            "average_confidence": confidence["average_confidence"],
        },
        "irt": {
            "theta": session.theta,
            "ability_label": ability_label(session.theta),
        },
        "skills": skills,
        "competencies": competencies,
        "confidence_analysis": confidence,
        "response_time": {
            "average_response_time_ms": avg_time,
        },
        "misconception_signals": misconception_signals,
    }


def get_skill_mastery_states(db: Session, profile_id: str, session_id: str | None = None):
    query = (
        db.query(LearnerSkillState, SkillNode, Competency)
        .join(SkillNode, LearnerSkillState.skill_node_id == SkillNode.skill_node_id)
        .join(Competency, SkillNode.competency_id == Competency.competency_id)
        .filter(
            LearnerSkillState.profile_id == profile_id,
            SkillNode.competency_id.in_(_active_competency_ids(db, profile_id)),
        )
    )
    scope = db.query(AssessmentSession.scope_skill_node_id).filter(AssessmentSession.session_id == session_id).scalar() if session_id else None
    if scope:
        query = query.filter(LearnerSkillState.skill_node_id == scope)
    rows = query.order_by(Competency.competency_id, SkillNode.skill_node_id).all()
    grouped = _skill_response_map(db, session_id) if session_id else {}

    result = []
    for state, skill, competency in rows:
        evidence = _skill_evidence(grouped.get(skill.skill_node_id, [])) if grouped else {
            "attempts": state.attempts,
            "correct_attempts": state.correct_attempts,
            "incorrect_attempts": state.attempts - state.correct_attempts,
            "confidence_avg": 0.0,
            "avg_response_time_ms": 0.0,
            "evidence_status": "limited_evidence",
            "has_higher_cognitive_evidence": False,
        }
        raw_mastery = state.mastery_probability
        if grouped.get(skill.skill_node_id):
            raw_mastery = grouped[skill.skill_node_id][-1][0].bkt_mastery_after
        display_mastery = _evidence_adjusted_mastery(raw_mastery, evidence)
        result.append({
            "skill_node_id": skill.skill_node_id,
            "name": skill.name,
            "competency_id": competency.competency_id,
            "competency_name": competency.name,
            "mastery_probability": display_mastery,
            "raw_bkt_mastery_probability": round(raw_mastery, 4),
            "effective_attempts": evidence.get("effective_attempts", evidence["attempts"]),
            "guessing_attempts": evidence.get("guessing_attempts", 0),
            "attempts": evidence["attempts"],
            "correct_attempts": evidence["correct_attempts"],
            "incorrect_attempts": evidence["incorrect_attempts"],
            "confidence_avg": evidence["confidence_avg"],
            "avg_response_time_ms": evidence["avg_response_time_ms"],
            "evidence_status": evidence["evidence_status"],
        })
    return result


def _competency_summary(skills: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for skill in skills:
        grouped[(skill["competency_id"], skill["competency_name"])].append(skill)

    summaries = []
    for (competency_id, name), skill_rows in sorted(grouped.items()):
        mastery = sum(skill["mastery_probability"] for skill in skill_rows) / len(skill_rows)
        evidence_count = sum(skill.get("effective_attempts", skill["attempts"]) for skill in skill_rows)
        if evidence_count >= 6:
            evidence_status = "moderate"
        elif evidence_count >= 3:
            evidence_status = "limited"
        else:
            evidence_status = "early"
        summaries.append({
            "competency_id": competency_id,
            "name": name,
            "mastery": round(mastery, 4),
            "evidence_status": evidence_status,
            "assessed_skill_count": len(skill_rows),
            "aggregation_method": "equal skill-weight average",
        })
    return summaries
