from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.competency import DesiredCompetenciesResponse, ProfileTargetsResponse, ProfileTargetSkillsResponse, RequiredCompetenciesResponse
from app.schemas.profile import ProfileOut
from app.services.competency_service import get_desired_competencies, get_profile_target_skills, get_required_competencies
from app.services.profile_service import PROTOTYPE_PROFILE_ID, get_prototype_profile, list_profiles


router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def profile(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return get_prototype_profile(db, profile_id)


@router.get("s")
def profiles(db: Session = Depends(get_db)):
    return list_profiles(db)


@router.get("s/{profile_id}", response_model=ProfileOut)
def profile_by_id(profile_id: str, db: Session = Depends(get_db)):
    return get_prototype_profile(db, profile_id)


@router.get("/required-competencies", response_model=RequiredCompetenciesResponse)
def required_competencies(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return {
        "profile_id": profile_id,
        "source": "role_activity_mapping",
        "competencies": get_required_competencies(db, profile_id),
    }


@router.get("/desired-competencies", response_model=DesiredCompetenciesResponse)
def desired_competencies(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return {
        "profile_id": profile_id,
        "source": "hardcoded_profile_development_goals",
        "competencies": get_desired_competencies(db, profile_id),
    }


@router.get("/targets", response_model=ProfileTargetsResponse)
def profile_targets(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return {
        "profile_id": profile_id,
        "required_competencies": get_required_competencies(db, profile_id),
        "desired_competencies": get_desired_competencies(db, profile_id),
    }


@router.get("/target-skills", response_model=ProfileTargetSkillsResponse)
def profile_target_skills(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return get_profile_target_skills(db, profile_id)


@router.get("s/{profile_id}/targets", response_model=ProfileTargetsResponse)
def profile_targets_by_id(profile_id: str, db: Session = Depends(get_db)):
    return {
        "profile_id": profile_id,
        "required_competencies": get_required_competencies(db, profile_id),
        "desired_competencies": get_desired_competencies(db, profile_id),
    }
