from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Activity, Department, Organization, Position, Profile, ProfileActivity, ProfileTraining, Role, TrainingCatalog


PROTOTYPE_PROFILE_ID = "PROFILE001"


def list_profiles(db: Session):
    rows = (
        db.query(Profile, Department)
        .join(Department, Profile.department_id == Department.department_id)
        .order_by(Profile.id)
        .all()
    )
    return [
        {
            "profile_id": profile.id,
            "name": profile.full_name,
            "domain": "Computer Science" if profile.id == "PROFILE002" else "Statistics",
            "label": f"{profile.full_name} - {'Computer Science' if profile.id == 'PROFILE002' else 'Statistics'}",
            "department": department.name,
        }
        for profile, department in rows
    ]


def get_prototype_profile(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Prototype profile not found")

    organization = db.get(Organization, profile.organization_id)
    department = db.get(Department, profile.department_id)
    position = db.get(Position, profile.position_id)
    role = db.get(Role, profile.role_id)

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
        "organization": {
            "organization_id": organization.organization_id,
            "name": organization.name,
        },
        "department": {
            "department_id": department.department_id,
            "organization_id": department.organization_id,
            "name": department.name,
        },
        "position": {
            "position_id": position.position_id,
            "department_id": position.department_id,
            "designation": position.designation,
        },
        "role": {
            "role_id": role.role_id,
            "name": role.name,
            "description": role.description,
        },
        "years_experience": profile.years_experience,
        "education": {
            "qualification": profile.highest_qualification,
            "specialization": profile.specialization,
        },
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
