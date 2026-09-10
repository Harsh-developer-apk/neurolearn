from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.course_service import get_course_detail


router = APIRouter(prefix="/api/v1/courses", tags=["courses"])


@router.get("/{course_id}")
def course_detail(course_id: str, db: Session = Depends(get_db)):
    course = get_course_detail(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
