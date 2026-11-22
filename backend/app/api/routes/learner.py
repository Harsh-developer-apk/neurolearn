from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.assessment import LearnerCompetencyStateResponse
from app.services.learner_service import get_competency_state
from app.services.phase4_service import get_knowledge_graph_state, get_roadmap
from app.services.profile_service import PROTOTYPE_PROFILE_ID


router = APIRouter(prefix="/api/v1/learner", tags=["learner"])
profiles_router = APIRouter(prefix="/api/v1/profiles", tags=["phase 4"])


@router.get("/competency-state", response_model=LearnerCompetencyStateResponse)
def competency_state(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return get_competency_state(db, profile_id)


@router.get("/knowledge-graph")
def knowledge_graph(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return get_knowledge_graph_state(db, profile_id)


@router.get("/roadmap")
def roadmap(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return get_roadmap(db, profile_id)


@profiles_router.get("/{profile_id}/knowledge-graph")
def profile_knowledge_graph(profile_id: str, db: Session = Depends(get_db)):
    return get_knowledge_graph_state(db, profile_id)


@profiles_router.get("/{profile_id}/roadmap")
def profile_roadmap(profile_id: str, db: Session = Depends(get_db)):
    return get_roadmap(db, profile_id)
