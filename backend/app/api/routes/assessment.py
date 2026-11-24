from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.assessment import AssessmentResultResponse, StartAssessmentResponse, SubmitAnswerRequest, SubmitAnswerResponse, TopicAssessmentRequest
from app.services.assessment_service import get_assessment_result, run_sample_assessment, start_assessment, start_topic_assessment, submit_answer
from app.services.profile_service import PROTOTYPE_PROFILE_ID


router = APIRouter(prefix="/api/v1/assessment", tags=["assessment"])


@router.post("/start", response_model=StartAssessmentResponse)
def start(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return start_assessment(db, profile_id)


@router.post("/topic/start", response_model=StartAssessmentResponse)
def start_topic(payload: TopicAssessmentRequest, db: Session = Depends(get_db)):
    return start_topic_assessment(db, payload.profile_id, payload.skill_node_id)


@router.post("/sample", response_model=AssessmentResultResponse)
def sample(profile_id: str = Query(PROTOTYPE_PROFILE_ID), db: Session = Depends(get_db)):
    return run_sample_assessment(db, profile_id)


@router.post("/{session_id}/answer", response_model=SubmitAnswerResponse)
def answer(session_id: str, payload: SubmitAnswerRequest, db: Session = Depends(get_db)):
    return submit_answer(
        db=db,
        session_id=session_id,
        question_id=payload.question_id,
        selected_option=payload.selected_option,
        selected_options=payload.selected_options,
        response_time_ms=payload.response_time_ms,
        confidence=payload.confidence,
    )


@router.get("/{session_id}/result", response_model=AssessmentResultResponse)
def result(session_id: str, db: Session = Depends(get_db)):
    return get_assessment_result(db, session_id)
