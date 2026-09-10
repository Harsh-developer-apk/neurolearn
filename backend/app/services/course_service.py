from sqlalchemy.orm import Session

from app.models import Course, CourseCompetency, CourseLearningOutcome, CourseModule, CourseTopic


FORMAT_SCORES = {
    "Interactive": 1.0,
    "Video + Assessment": 0.95,
    "Mixed": 0.9,
    "Video + PDF": 0.8,
    "Video": 0.7,
}


def _course_topics(db: Session, course_id: str) -> list[str]:
    return [
        row.topic_name
        for row in db.query(CourseTopic).filter(CourseTopic.course_id == course_id).order_by(CourseTopic.id).all()
    ]


def _course_outcomes(db: Session, course_id: str) -> list[str]:
    return [
        row.outcome_text
        for row in db.query(CourseLearningOutcome)
        .filter(CourseLearningOutcome.course_id == course_id)
        .order_by(CourseLearningOutcome.sequence_order)
        .all()
    ]


def _course_modules(db: Session, course_id: str) -> list[dict]:
    return [
        {
            "module_title": row.module_title,
            "sequence_order": row.sequence_order,
            "duration_minutes": row.duration_minutes,
            "content_type": row.content_type,
        }
        for row in db.query(CourseModule)
        .filter(CourseModule.course_id == course_id)
        .order_by(CourseModule.sequence_order)
        .all()
    ]


def _course_mappings(db: Session, course_id: str) -> list[dict]:
    return [
        {
            "competency_id": row.competency_id,
            "relevance_score": row.relevance_score,
        }
        for row in db.query(CourseCompetency)
        .filter(CourseCompetency.course_id == course_id)
        .order_by(CourseCompetency.relevance_score.desc(), CourseCompetency.competency_id)
        .all()
    ]


def serialize_course(db: Session, course: Course, recommendation: dict | None = None) -> dict:
    result = {
        "course_id": course.course_id,
        "title": course.title,
        "short_description": course.short_description,
        "description": course.description,
        "provider": course.provider,
        "source_platform": course.source_platform,
        "catalog_type": course.catalog_type,
        "duration_minutes": course.duration_minutes,
        "difficulty_level": course.difficulty_level,
        "language": course.language,
        "course_type": course.course_type,
        "learning_format": course.learning_format,
        "status": course.status,
        "external_url": course.external_url,
        "thumbnail_url": course.thumbnail_url,
        "topics": _course_topics(db, course.course_id),
        "learning_outcomes": _course_outcomes(db, course.course_id),
        "modules": _course_modules(db, course.course_id),
        "competency_alignment": _course_mappings(db, course.course_id),
    }
    if recommendation:
        result.update(recommendation)
    return result


def get_course_detail(db: Session, course_id: str) -> dict | None:
    course = db.get(Course, course_id)
    if not course:
        return None
    return serialize_course(db, course)


def _difficulty_alignment(course_difficulty: str, roadmap_item: dict) -> float:
    mastery = roadmap_item.get("mastery")
    gap = roadmap_item.get("gap")
    if mastery is None:
        desired = "Beginner"
    elif gap is not None and gap >= 0.45:
        desired = "Beginner"
    elif gap is not None and gap >= 0.2:
        desired = "Intermediate"
    else:
        desired = "Advanced"

    order = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}
    distance = abs(order.get(course_difficulty, 2) - order.get(desired, 2))
    return max(0.0, 1.0 - distance * 0.35)


def _gap_alignment(roadmap_item: dict) -> float:
    gap = roadmap_item.get("gap")
    if gap is None:
        return 0.65
    return min(1.0, max(0.0, gap / 0.75))


def _prerequisite_alignment(roadmap_item: dict) -> float:
    health = roadmap_item.get("prerequisite_health", {}).get("prerequisite_health")
    if health == "ready":
        return 1.0
    if health == "unassessed":
        return 0.65
    if health == "weak":
        return 0.45
    return 0.7


def _reason(roadmap_item: dict, exact_skill_match: bool) -> str:
    gap = roadmap_item.get("gap")
    gap_text = f"{round(gap * 100)}-point mastery gap" if gap is not None else "limited learner evidence"
    if exact_skill_match:
        return f"Recommended because this course directly aligns with {roadmap_item['name']} and the current {gap_text}."
    if roadmap_item.get("target_type") == "required":
        return f"Recommended because this required competency is below target and has a {gap_text}."
    return f"Recommended because this desired goal needs structured learning and currently has {gap_text}."


def recommend_course_for_roadmap_item(db: Session, roadmap_item: dict) -> dict | None:
    skill_id = roadmap_item["skill_node_id"]
    competency_id = roadmap_item["competency_id"]
    mappings = (
        db.query(CourseCompetency, Course)
        .join(Course, CourseCompetency.course_id == Course.course_id)
        .filter(
            Course.status == "active",
            CourseCompetency.competency_id.in_([skill_id, competency_id]),
        )
        .all()
    )
    if not mappings:
        return None

    scored = []
    for mapping, course in mappings:
        exact_skill_match = mapping.competency_id == skill_id
        relevance = mapping.relevance_score + (0.08 if exact_skill_match else 0.0)
        gap_score = _gap_alignment(roadmap_item)
        difficulty_score = _difficulty_alignment(course.difficulty_level, roadmap_item)
        prerequisite_score = _prerequisite_alignment(roadmap_item)
        format_score = FORMAT_SCORES.get(course.learning_format, 0.75)
        score = (
            0.45 * min(1.0, relevance)
            + 0.25 * gap_score
            + 0.15 * difficulty_score
            + 0.10 * prerequisite_score
            + 0.05 * format_score
        )
        scored.append({
            "course": course,
            "mapping": mapping,
            "exact_skill_match": exact_skill_match,
            "score": round(score, 4),
            "gap_score": gap_score,
            "difficulty_score": difficulty_score,
        })

    best = sorted(
        scored,
        key=lambda item: (
            -item["score"],
            -item["mapping"].relevance_score,
            -item["gap_score"],
            -item["difficulty_score"],
            item["course"].duration_minutes,
            item["course"].course_id,
        ),
    )[0]
    recommendation = {
        "recommendation_score": best["score"],
        "recommendation_reason": _reason(roadmap_item, best["exact_skill_match"]),
        "matched_competency_id": best["mapping"].competency_id,
        "prototype_catalog_notice": "Prototype course - catalog preview only",
    }
    return serialize_course(db, best["course"], recommendation)
