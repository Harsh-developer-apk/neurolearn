import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import AssessmentQuestion, AssessmentResponse, AssessmentSession, Competency, LearnerSkillState, SkillNode, SkillPrerequisite
from app.services.assessment_service import _evidence_adjusted_mastery, _skill_evidence
from app.services.competency_service import TARGET_LABELS, get_desired_competencies, get_profile_target_skills, get_required_competencies
from app.services.profile_service import PROTOTYPE_PROFILE_ID
from app.services.roadmap_service import build_roadmap, prerequisite_health


TARGET_MASTERY_BY_LEVEL = {
    1: 0.35,
    2: 0.55,
    3: 0.75,
    4: 0.90,
}



def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _latest_completed_session(db: Session, profile_id: str) -> AssessmentSession | None:
    return (
        db.query(AssessmentSession)
        .filter(
            AssessmentSession.profile_id == profile_id,
            AssessmentSession.status == "completed",
        )
        .order_by(AssessmentSession.completed_at.desc(), AssessmentSession.id.desc())
        .first()
    )


def _profile_responses(db: Session, profile_id: str, session_id: str | None) -> list[tuple[AssessmentResponse, AssessmentQuestion]]:
    if not session_id:
        return []
    return (
        db.query(AssessmentResponse, AssessmentQuestion)
        .join(AssessmentQuestion, AssessmentResponse.question_id == AssessmentQuestion.question_id)
        .join(AssessmentSession, AssessmentResponse.session_id == AssessmentSession.session_id)
        .filter(AssessmentSession.profile_id == profile_id, AssessmentSession.session_id == session_id)
        .order_by(AssessmentResponse.sequence_number)
        .all()
    )


def _response_evidence_by_skill(db: Session, profile_id: str, session_id: str | None) -> dict[str, dict]:
    grouped = _latest_session_rows_by_skill(db, profile_id, session_id)
    evidence_by_skill = {}
    for skill_id, rows in grouped.items():
        evidence = _skill_evidence(rows)
        evidence["raw_bkt_mastery"] = rows[-1][0].bkt_mastery_after
        evidence_by_skill[skill_id] = evidence
    return evidence_by_skill


def _misconceptions_by_skill(db: Session, profile_id: str, session_id: str | None) -> dict[str, list[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    rows_by_skill = _latest_session_rows_by_skill(db, profile_id, session_id)
    for rows in rows_by_skill.values():
        for response, question in rows:
            if response.correct or response.confidence == 1:
                continue
            for tag in _json_list(question.misconception_tags):
                result[response.skill_node_id].add(tag)
    return {skill_id: sorted(tags) for skill_id, tags in result.items()}


def _latest_session_rows_by_skill(db: Session, profile_id: str, latest_session_id: str | None):
    """Use the newest completed assessment evidence per topic, preserving unrelated topic history."""
    rows = (
        db.query(AssessmentResponse, AssessmentQuestion, AssessmentSession)
        .join(AssessmentQuestion, AssessmentResponse.question_id == AssessmentQuestion.question_id)
        .join(AssessmentSession, AssessmentResponse.session_id == AssessmentSession.session_id)
        .filter(AssessmentSession.profile_id == profile_id, AssessmentSession.status == "completed")
        .order_by(AssessmentSession.completed_at.desc(), AssessmentSession.id.desc(), AssessmentResponse.sequence_number.asc())
        .all()
    )
    newest_session_by_skill = {}
    for response, _, session in rows:
        newest_session_by_skill.setdefault(response.skill_node_id, session.session_id)
    grouped = defaultdict(list)
    for response, question, session in rows:
        if newest_session_by_skill.get(response.skill_node_id) == session.session_id:
            grouped[response.skill_node_id].append((response, question))
    return grouped


def _learner_states(db: Session, profile_id: str) -> dict[str, LearnerSkillState]:
    return {
        state.skill_node_id: state
        for state in db.query(LearnerSkillState).filter(LearnerSkillState.profile_id == profile_id).all()
    }


def _all_prerequisites(db: Session) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in db.query(SkillPrerequisite).filter(SkillPrerequisite.relationship_type == "prerequisite").all():
        grouped[row.skill_node_id].append(row.prerequisite_skill_node_id)
    return {skill_id: sorted(values) for skill_id, values in grouped.items()}


def _dependents(db: Session) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in db.query(SkillPrerequisite).filter(SkillPrerequisite.relationship_type == "prerequisite").all():
        grouped[row.prerequisite_skill_node_id].append(row.skill_node_id)
    return {skill_id: sorted(values) for skill_id, values in grouped.items()}


def _target_maps(db: Session, profile_id: str):
    required = {item["competency_id"]: item for item in get_required_competencies(db, profile_id)}
    desired = {item["competency_id"]: item for item in get_desired_competencies(db, profile_id)}
    return required, desired


def _skill_node_state(db: Session, profile_id: str, skill: dict, target_level: int, target_type: str, evidence_by_skill, states, misconceptions, prerequisites, dependents):
    skill_id = skill["skill_node_id"]
    state = states.get(skill_id)
    evidence = evidence_by_skill.get(skill_id)
    raw_mastery = evidence.get("raw_bkt_mastery") if evidence else None
    mastery = _evidence_adjusted_mastery(raw_mastery, evidence) if raw_mastery is not None and evidence else None
    attempts = evidence["attempts"] if evidence else 0
    correct = evidence["correct_attempts"] if evidence else 0
    accuracy = round(correct / attempts, 4) if attempts else None
    target_mastery = TARGET_MASTERY_BY_LEVEL.get(target_level, 0.75)
    gap = round(max(0.0, target_mastery - mastery), 4) if mastery is not None else None
    prereq_ids = prerequisites.get(skill_id, [])

    return {
        **skill,
        "target_level": target_level,
        "target_label": TARGET_LABELS.get(target_level, "Unknown"),
        "target_mastery": target_mastery,
        "target_type": target_type,
        "required": target_type == "required",
        "mastery": mastery,
        "raw_bkt_mastery": round(raw_mastery, 4) if raw_mastery is not None else None,
        "gap": gap,
        "evidence_status": evidence["evidence_status"] if evidence else "not_assessed",
        "attempts": attempts,
        "effective_attempts": evidence["effective_attempts"] if evidence else 0.0,
        "guessing_attempts": evidence["guessing_attempts"] if evidence else 0,
        "correct_attempts": correct,
        "incorrect_attempts": evidence["incorrect_attempts"] if evidence else 0,
        "accuracy": accuracy,
        "confidence": evidence["confidence_avg"] if evidence else None,
        "avg_response_time": evidence["avg_response_time_ms"] if evidence else None,
        "misconceptions": misconceptions.get(skill_id, []),
        "prerequisites": prereq_ids,
        "dependents": dependents.get(skill_id, []),
    }


def get_knowledge_graph_state(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    latest_session = _latest_completed_session(db, profile_id)
    targets = get_profile_target_skills(db, profile_id)
    required_targets, desired_targets = _target_maps(db, profile_id)
    evidence_by_skill = _response_evidence_by_skill(db, profile_id, latest_session.session_id if latest_session else None)
    states = _learner_states(db, profile_id)
    misconceptions = _misconceptions_by_skill(db, profile_id, latest_session.session_id if latest_session else None)
    prerequisites = _all_prerequisites(db)
    dependents = _dependents(db)

    competencies = []
    for target_type in ["required", "desired"]:
        for group in targets[target_type]:
            skill_states = [
                _skill_node_state(
                    db,
                    profile_id,
                    skill,
                    group["target_level"],
                    target_type,
                    evidence_by_skill,
                    states,
                    misconceptions,
                    prerequisites,
                    dependents,
                )
                for skill in group["skill_nodes"]
            ]
            assessed = [skill for skill in skill_states if skill["mastery"] is not None]
            competency_mastery = round(sum(skill["mastery"] for skill in assessed) / len(assessed), 4) if assessed else None
            target_mastery = TARGET_MASTERY_BY_LEVEL.get(group["target_level"], 0.75)
            competencies.append({
                "competency_id": group["competency_id"],
                "name": group["competency_name"],
                "target_type": target_type,
                "target_level": group["target_level"],
                "target_label": group.get("target_label") or TARGET_LABELS.get(group["target_level"]),
                "target_mastery": target_mastery,
                "observed_mastery": competency_mastery,
                "gap": round(max(0.0, target_mastery - competency_mastery), 4) if competency_mastery is not None else None,
                "evidence_coverage": {
                    "assessed_skills": len(assessed),
                    "total_skills": len(skill_states),
                },
                "skills": skill_states,
            })

    skills_by_id = {skill["skill_node_id"]: skill for competency in competencies for skill in competency["skills"]}
    prerequisite_map = {skill_id: skill["prerequisites"] for skill_id, skill in skills_by_id.items()}
    for skill_id, skill in skills_by_id.items():
        skill["prerequisite_health"] = prerequisite_health(skill_id, prerequisite_map, skills_by_id)

    return {
        "profile_id": profile_id,
        "source": "phase4_knowledge_graph_state",
        "assessment_source": {
            "session_id": latest_session.session_id if latest_session else None,
            "assessment_mode": latest_session.assessment_mode if latest_session else None,
            "completed_at": latest_session.completed_at.isoformat() if latest_session and latest_session.completed_at else None,
        },
        "competencies": competencies,
    }



def get_roadmap(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    return build_roadmap(get_knowledge_graph_state(db, profile_id))
