from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Activity, Profile, ProfileActivity, ProfileTraining, TrainingCatalog
from app.seed.dsa_curriculum import DSA_PROFILE_ID


PROTOTYPE_PROFILE_ID = DSA_PROFILE_ID


def list_profiles(db: Session):
    rows = (
        db.query(Profile)
        .filter(Profile.id == PROTOTYPE_PROFILE_ID)
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
