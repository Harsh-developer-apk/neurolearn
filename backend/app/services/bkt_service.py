from datetime import datetime

from sqlalchemy.orm import Session

from app.models import LearnerSkillState
from app.services.confidence_service import response_weight


L0 = 0.20
T = 0.10
G = 0.20
S = 0.10


def update_mastery_probability(current: float, correct: bool, confidence: int = 3) -> float:
    weight = response_weight(confidence)
    if correct:
        numerator = current * (1 - S)
        denominator = numerator + (1 - current) * G
        posterior = numerator / denominator if denominator else current
        updated = posterior + (1 - posterior) * T
    else:
        numerator = current * S
        denominator = numerator + (1 - current) * (1 - G)
        updated = numerator / denominator if denominator else current

    weighted = current + weight * (updated - current)
    return round(max(0.0, min(1.0, weighted)), 4)


def update_skill_state(db: Session, profile_id: str, skill_node_id: str, correct: bool, confidence: int = 3) -> LearnerSkillState:
    state = (
        db.query(LearnerSkillState)
        .filter(
            LearnerSkillState.profile_id == profile_id,
            LearnerSkillState.skill_node_id == skill_node_id,
        )
        .first()
    )

    if not state:
        state = LearnerSkillState(
            profile_id=profile_id,
            skill_node_id=skill_node_id,
            mastery_probability=L0,
            attempts=0,
            correct_attempts=0,
        )
        db.add(state)

    state.mastery_probability = update_mastery_probability(state.mastery_probability, correct, confidence)
    state.attempts += 1
    if correct:
        state.correct_attempts += 1
    state.last_updated = datetime.utcnow()
    return state
