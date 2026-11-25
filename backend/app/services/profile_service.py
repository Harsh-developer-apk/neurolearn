import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Activity, Profile, ProfileActivity, ProfileTraining, SkillPrerequisite, SyllabusDocument, TrainingCatalog
from app.seed.dsa_curriculum import DSA_PROFILE_ID, DSA_SKILLS


PROTOTYPE_PROFILE_ID = DSA_PROFILE_ID


def list_profiles(db: Session):
    rows = (
        db.query(Profile)
        .filter(Profile.subject_id == "dsa")
        .order_by(Profile.id)
        .all()
    )
    return [
        {
            "profile_id": profile.id,
            "name": profile.full_name,
            "label": profile.full_name,
        }
        for profile in rows
    ]


def get_prototype_profile(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Prototype profile not found")

    activity_ids = [
        row.activity_id
        for row in db.query(ProfileActivity)
        .filter(ProfileActivity.profile_id == profile.id)
        .order_by(ProfileActivity.activity_id)
        .all()
    ]
    activities = db.query(Activity).filter(Activity.activity_id.in_(activity_ids)).all()
    activities_by_id = {activity.activity_id: activity for activity in activities}
    ordered_activities = [activities_by_id[activity_id] for activity_id in activity_ids if activity_id in activities_by_id]

    training_rows = (
        db.query(ProfileTraining, TrainingCatalog)
        .join(TrainingCatalog, ProfileTraining.training_id == TrainingCatalog.training_id)
        .filter(ProfileTraining.profile_id == profile.id)
        .order_by(ProfileTraining.training_id)
        .all()
    )

    return {
        "profile_id": profile.id,
        "full_name": profile.full_name,
        "preferred_language": profile.preferred_language,
        "age": profile.age,
        "course_or_class": profile.course_or_class,
        "subject_id": profile.subject_id,
        "learning_goal": profile.learning_goal,
        "goal_details": profile.goal_details,
        "activities": [
            {
                "activity_id": activity.activity_id,
                "name": activity.name,
                "description": activity.description,
            }
            for activity in ordered_activities
        ],
        "training_history": [
            {
                "training_id": training.training_id,
                "title": training.title,
                "provider": training.provider,
                "completion_status": profile_training.completion_status,
            }
            for profile_training, training in training_rows
        ],
    }


def get_learning_scope(db: Session, profile_id: str) -> dict | None:
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile or profile.learning_goal != "exam":
        return None
    document = (
        db.query(SyllabusDocument)
        .filter(SyllabusDocument.profile_id == profile_id)
        .order_by(SyllabusDocument.created_at.desc())
        .first()
    )
    if not document:
        return None
    try:
        selected = set(json.loads(document.included_skill_ids or "[]"))
    except (TypeError, json.JSONDecodeError):
        selected = set()
    valid_ids = {row[0] for row in DSA_SKILLS}
    selected.intersection_update(valid_ids)
    if not selected:
        return None
    prerequisites = {}
    for skill_id, prerequisite_id in db.query(SkillPrerequisite.skill_node_id, SkillPrerequisite.prerequisite_skill_node_id).filter(
        SkillPrerequisite.relationship_type == "prerequisite"
    ).all():
        prerequisites.setdefault(skill_id, set()).add(prerequisite_id)
    included = set(selected)
    frontier = list(selected)
    while frontier:
        current = frontier.pop()
        for prerequisite_id in prerequisites.get(current, set()):
            if prerequisite_id in valid_ids and prerequisite_id not in included:
                included.add(prerequisite_id)
                frontier.append(prerequisite_id)
    return {
        "mode": "exam",
        "syllabus_filename": document.filename,
        "selected_skill_ids": sorted(selected),
        "included_skill_ids": sorted(included),
    }
