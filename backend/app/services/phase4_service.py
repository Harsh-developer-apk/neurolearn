import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import AssessmentQuestion, AssessmentResponse, AssessmentSession, Competency, LearnerSkillState, SkillNode, SkillPrerequisite
from app.services.assessment_service import _evidence_adjusted_mastery, _skill_evidence
from app.services.competency_service import TARGET_LABELS, get_desired_competencies, get_profile_target_skills, get_required_competencies
from app.services.profile_service import PROTOTYPE_PROFILE_ID


TARGET_MASTERY_BY_LEVEL = {
    1: 0.35,
    2: 0.55,
    3: 0.75,
    4: 0.90,
}

PRIORITY_WEIGHTS = {
    "gap": 0.35,
    "role_requirement": 0.25,
    "prerequisite_impact": 0.20,
    "evidence_confidence": 0.10,
    "misconception": 0.10,
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
    grouped: dict[str, list[tuple[AssessmentResponse, AssessmentQuestion]]] = defaultdict(list)
    for response, question in _profile_responses(db, profile_id, session_id):
        grouped[response.skill_node_id].append((response, question))
    evidence_by_skill = {}
    for skill_id, rows in grouped.items():
        evidence = _skill_evidence(rows)
        evidence["raw_bkt_mastery"] = rows[-1][0].bkt_mastery_after
        evidence_by_skill[skill_id] = evidence
    return evidence_by_skill


def _misconceptions_by_skill(db: Session, profile_id: str, session_id: str | None) -> dict[str, list[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for response, question in _profile_responses(db, profile_id, session_id):
        if response.correct:
            continue
        for tag in _json_list(question.misconception_tags):
            result[response.skill_node_id].add(tag)
    return {skill_id: sorted(tags) for skill_id, tags in result.items()}


def _learner_states(db: Session, profile_id: str) -> dict[str, LearnerSkillState]:
    return {
        state.skill_node_id: state
        for state in db.query(LearnerSkillState).filter(LearnerSkillState.profile_id == profile_id).all()
    }


def _all_prerequisites(db: Session) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in db.query(SkillPrerequisite).all():
        grouped[row.skill_node_id].append(row.prerequisite_skill_node_id)
    return {skill_id: sorted(values) for skill_id, values in grouped.items()}


def _dependents(db: Session) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in db.query(SkillPrerequisite).all():
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


def _prerequisite_health(skill, skills_by_id):
    prereq_ids = skill["prerequisites"]
    weak = []
    unassessed = []
    mastered = []
    for prereq_id in prereq_ids:
        prereq = skills_by_id.get(prereq_id)
        if not prereq or prereq["mastery"] is None:
            unassessed.append(prereq_id)
        elif prereq["mastery"] >= 0.65 and prereq["evidence_status"] not in {"weak", "uncertain"}:
            mastered.append(prereq_id)
        else:
            weak.append(prereq_id)
    if weak:
        health = "weak"
    elif unassessed:
        health = "unassessed"
    else:
        health = "ready"
    return {
        "prerequisite_count": len(prereq_ids),
        "mastered_prerequisite_count": len(mastered),
        "weak_prerequisite_count": len(weak),
        "unassessed_prerequisite_count": len(unassessed),
        "weak_prerequisites": weak,
        "unassessed_prerequisites": unassessed,
        "prerequisite_health": health,
    }


def get_roadmap(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    graph = get_knowledge_graph_state(db, profile_id)
    skills = [skill for comp in graph["competencies"] for skill in comp["skills"]]
    skills_by_id = {skill["skill_node_id"]: skill for skill in skills}
    candidates = []

    for skill in skills:
        prereq = _prerequisite_health(skill, skills_by_id)
        if skill["mastery"] is None:
            gap_score = 0.35
            evidence_confidence_score = 1.0
            state = "not_assessed"
        else:
            gap_score = min(1.0, max(0.0, skill["gap"] or 0.0))
            evidence_confidence_score = 1.0 if skill["evidence_status"] in {"weak", "uncertain", "gathering_evidence"} else 0.25
            if skill["mastery"] >= skill["target_mastery"] and skill["evidence_status"] == "sufficient_mastery":
                state = "mastered"
            elif skill["evidence_status"] in {"limited_evidence", "gathering_evidence", "uncertain"} and skill["attempts"] < 2:
                state = "needs_more_evidence"
            elif prereq["prerequisite_health"] == "weak":
                state = "blocked_by_prerequisite"
            else:
                state = "learning_priority" if gap_score > 0.05 else "on_track"

        role_requirement_score = 1.0 if skill["target_type"] == "required" else 0.6
        prerequisite_impact_score = min(1.0, len(skill["dependents"]) / 3)
        misconception_score = min(1.0, len(skill["misconceptions"]) / 2)
        priority_score = (
            PRIORITY_WEIGHTS["gap"] * gap_score
            + PRIORITY_WEIGHTS["role_requirement"] * role_requirement_score
            + PRIORITY_WEIGHTS["prerequisite_impact"] * prerequisite_impact_score
            + PRIORITY_WEIGHTS["evidence_confidence"] * evidence_confidence_score
            + PRIORITY_WEIGHTS["misconception"] * misconception_score
        )
        if state in {"mastered", "on_track"}:
            priority_score *= 0.2
        if state == "blocked_by_prerequisite":
            priority_score *= 0.6

        reasons = []
        if skill["target_type"] == "required":
            reasons.append("Required for role")
        else:
            reasons.append("Supports desired goal")
        if skill["gap"] is not None:
            reasons.append(f"Mastery gap: {round(skill['gap'] * 100)} percentage points")
        if len(skill["dependents"]):
            reasons.append(f"Prerequisite for {len(skill['dependents'])} higher-level skill(s)")
        if prereq["weak_prerequisites"]:
            reasons.append(f"Blocked by prerequisite: {', '.join(prereq['weak_prerequisites'])}")
        if skill["misconceptions"]:
            reasons.append("Potential misconception signal: " + ", ".join(skill["misconceptions"][:2]))
        if state == "needs_more_evidence":
            reasons.append("Diagnostic evidence is still limited")

        candidates.append({
            "skill_node_id": skill["skill_node_id"],
            "name": skill["name"],
            "competency_id": skill["competency_id"],
            "competency_name": next(comp["name"] for comp in graph["competencies"] if comp["competency_id"] == skill["competency_id"]),
            "target_type": skill["target_type"],
            "state": state,
            "priority_score": round(priority_score, 4),
            "mastery": skill["mastery"],
            "target_mastery": skill["target_mastery"],
            "gap": skill["gap"],
            "evidence_status": skill["evidence_status"],
            "prerequisite_health": prereq,
            "reasons": reasons,
        })

    prioritized = sorted(candidates, key=lambda item: item["priority_score"], reverse=True)
    actionable = [item for item in prioritized if item["state"] not in {"mastered", "on_track"}]
    immediate = actionable[:1]
    near_term = actionable[1:4]
    later = actionable[4:8]
    desired = [item for item in prioritized if item["target_type"] == "desired" and item["state"] not in {"mastered", "on_track"}]

    return {
        "profile_id": profile_id,
        "source": "phase4_gap_analysis_and_roadmap",
        "assessment_source": graph["assessment_source"],
        "priority_weights": PRIORITY_WEIGHTS,
        "immediate_next": immediate,
        "near_term": near_term,
        "later": later,
        "desired_goal_path": desired[:5],
        "all_candidates": prioritized,
    }
