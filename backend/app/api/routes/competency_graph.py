from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.competency import CompetencyGraphResponse, CompetencySkillsResponse, SkillTraversalResponse
from app.services.competency_service import get_competency_graph, get_next_skills, get_prerequisites, get_skills_for_competency


router = APIRouter(prefix="/api/v1", tags=["competency graph"])


@router.get("/competency-graph", response_model=CompetencyGraphResponse)
def competency_graph(db: Session = Depends(get_db)):
    return get_competency_graph(db)


@router.get("/competencies/{competency_id}/skills", response_model=CompetencySkillsResponse)
def competency_skills(competency_id: str, db: Session = Depends(get_db)):
    return get_skills_for_competency(db, competency_id)


@router.get("/skills/{skill_node_id}/prerequisites", response_model=SkillTraversalResponse)
def skill_prerequisites(skill_node_id: str, db: Session = Depends(get_db)):
    return {
        "skill_node_id": skill_node_id,
        "skills": get_prerequisites(db, skill_node_id),
    }


@router.get("/skills/{skill_node_id}/next-skills", response_model=SkillTraversalResponse)
def skill_next_skills(skill_node_id: str, db: Session = Depends(get_db)):
    return {
        "skill_node_id": skill_node_id,
        "skills": get_next_skills(db, skill_node_id),
    }
