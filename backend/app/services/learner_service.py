from collections import defaultdict

from sqlalchemy.orm import Session

from app.services.assessment_service import get_skill_mastery_states
from app.services.profile_service import PROTOTYPE_PROFILE_ID


def get_competency_state(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    skill_states = get_skill_mastery_states(db, profile_id)
    grouped = defaultdict(list)

    for state in skill_states:
        grouped[(state["competency_id"], state["competency_name"])].append(state)

    competencies = []
    for (competency_id, competency_name), states in sorted(grouped.items()):
        mastery = sum(state["mastery_probability"] for state in states) / len(states)
        competencies.append({
            "competency_id": competency_id,
            "competency_name": competency_name,
            "competency_mastery": round(mastery, 4),
            "assessed_skill_count": len(states),
            "skill_states": states,
        })

    return {
        "profile_id": profile_id,
        "source": "diagnostic_assessment_evidence",
        "competencies": competencies,
    }
