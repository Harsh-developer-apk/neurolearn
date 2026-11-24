from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.learning import LearningBlockRequest, LearningPlanRequest
from app.services.ai_provider import configured_models
from app.services.lesson_service import create_block, create_plan


router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


@router.get("/debug/providers")
def learning_provider_status():
    """Return provider/model configuration only; never returns API keys."""
    return {"providers": configured_models()}


@router.post("/plan")
def learning_plan(payload: LearningPlanRequest, db: Session = Depends(get_db)):
    try:
        return create_plan(db, payload.profile_id, payload.skill_node_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/block")
def learning_block(payload: LearningBlockRequest, db: Session = Depends(get_db)):
    try:
        return create_block(db, payload.profile_id, payload.skill_node_id, payload.block_index,
                            payload.block, payload.feedback, payload.completed_blocks)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
