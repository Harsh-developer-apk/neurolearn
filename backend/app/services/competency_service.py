from collections import defaultdict

from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.models import ActivityCompetency, Competency, ProfileActivity, ProfileDesiredCompetency, SkillNode, SkillPrerequisite
from app.services.profile_service import PROTOTYPE_PROFILE_ID


TARGET_LABELS = {
    1: "Basic",
    2: "Working",
    3: "Proficient",
    4: "Advanced",
}


def get_required_competencies(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    activity_ids = [
        item.activity_id
        for item in db.query(ProfileActivity)
        .filter(ProfileActivity.profile_id == profile_id)
        .all()
    ]

    rows = (
        db.query(ActivityCompetency, Competency)
        .join(Competency, ActivityCompetency.competency_id == Competency.competency_id)
        .filter(ActivityCompetency.activity_id.in_(activity_ids))
        .all()
    )

    sources_by_competency = defaultdict(list)
    target_by_competency = {}
    competency_by_id = {}

    for mapping, competency in rows:
        sources_by_competency[competency.competency_id].append(mapping.activity_id)
        target_by_competency[competency.competency_id] = max(
            target_by_competency.get(competency.competency_id, 0),
            mapping.target_level,
        )
        competency_by_id[competency.competency_id] = competency

    return [
        {
            "competency_id": competency.competency_id,
            "name": competency.name,
            "description": competency.description,
            "category": competency.category,
            "required": True,
            "source_activity_ids": sorted(sources_by_competency[competency_id]),
            "target_level": target_by_competency[competency_id],
        }
        for competency_id, competency in sorted(competency_by_id.items())
    ]


def get_desired_competencies(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    rows = (
        db.query(ProfileDesiredCompetency, Competency)
        .join(Competency, ProfileDesiredCompetency.competency_id == Competency.competency_id)
        .filter(ProfileDesiredCompetency.profile_id == profile_id)
        .order_by(ProfileDesiredCompetency.competency_id)
        .all()
    )

    return [
        {
            "competency_id": competency.competency_id,
            "name": competency.name,
            "description": competency.description,
            "category": competency.category,
            "target_level": desired.target_level,
            "target_label": TARGET_LABELS.get(desired.target_level, "Unknown"),
        }
        for desired, competency in rows
    ]


def _skill_to_dict(db: Session, skill: SkillNode):
    return {
        "skill_node_id": skill.skill_node_id,
        "competency_id": skill.competency_id,
        "name": skill.name,
        "description": skill.description,
        "difficulty_level": skill.difficulty_level,
        "prerequisites": [
            row.prerequisite_skill_node_id
            for row in db.query(SkillPrerequisite)
            .filter(SkillPrerequisite.skill_node_id == skill.skill_node_id)
            .order_by(SkillPrerequisite.prerequisite_skill_node_id)
            .all()
        ],
        "next_skills": [
            row.skill_node_id
            for row in db.query(SkillPrerequisite)
            .filter(SkillPrerequisite.prerequisite_skill_node_id == skill.skill_node_id)
            .order_by(SkillPrerequisite.skill_node_id)
            .all()
        ],
    }


def get_skills_for_competency(db: Session, competency_id: str):
    competency = db.get(Competency, competency_id)
    if not competency:
        raise HTTPException(status_code=404, detail="Competency not found")

    skills = (
        db.query(SkillNode)
        .filter(SkillNode.competency_id == competency_id)
        .order_by(SkillNode.skill_node_id)
        .all()
    )

    return {
        "competency_id": competency.competency_id,
        "name": competency.name,
        "description": competency.description,
        "category": competency.category,
        "skill_nodes": [_skill_to_dict(db, skill) for skill in skills],
    }


def get_competency_graph(db: Session):
    competencies = db.query(Competency).order_by(Competency.competency_id).all()
    relationships = (
        db.query(SkillPrerequisite)
        .order_by(SkillPrerequisite.prerequisite_skill_node_id, SkillPrerequisite.skill_node_id)
        .all()
    )

    return {
        "competencies": [
            get_skills_for_competency(db, competency.competency_id)
            for competency in competencies
        ],
        "relationships": [
            {
                "prerequisite_skill_node_id": row.prerequisite_skill_node_id,
                "skill_node_id": row.skill_node_id,
                "relationship_type": row.relationship_type,
            }
            for row in relationships
        ],
    }


def get_prerequisites(db: Session, skill_node_id: str):
    skill = db.get(SkillNode, skill_node_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill node not found")

    rows = (
        db.query(SkillPrerequisite, SkillNode)
        .join(SkillNode, SkillPrerequisite.prerequisite_skill_node_id == SkillNode.skill_node_id)
        .filter(SkillPrerequisite.skill_node_id == skill_node_id)
        .order_by(SkillNode.skill_node_id)
        .all()
    )
    return [_skill_to_dict(db, prerequisite) for _, prerequisite in rows]


def get_next_skills(db: Session, skill_node_id: str):
    skill = db.get(SkillNode, skill_node_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill node not found")

    rows = (
        db.query(SkillPrerequisite, SkillNode)
        .join(SkillNode, SkillPrerequisite.skill_node_id == SkillNode.skill_node_id)
        .filter(SkillPrerequisite.prerequisite_skill_node_id == skill_node_id)
        .order_by(SkillNode.skill_node_id)
        .all()
    )
    return [_skill_to_dict(db, dependent) for _, dependent in rows]


def get_profile_target_skills(db: Session, profile_id: str = PROTOTYPE_PROFILE_ID):
    required_targets = get_required_competencies(db, profile_id)
    desired_targets = get_desired_competencies(db, profile_id)

    def expand(target, desired=False):
        competency_skills = get_skills_for_competency(db, target["competency_id"])
        return {
            "competency_id": target["competency_id"],
            "competency_name": target["name"],
            "target_level": target["target_level"],
            "target_label": target.get("target_label") if desired else TARGET_LABELS.get(target["target_level"]),
            "skill_nodes": competency_skills["skill_nodes"],
        }

    return {
        "profile_id": profile_id,
        "required": [expand(target) for target in required_targets],
        "desired": [expand(target, desired=True) for target in desired_targets],
    }
