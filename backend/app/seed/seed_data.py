import json

from sqlalchemy.orm import Session

from app.models import (
    Activity,
    ActivityCompetency,
    AssessmentQuestion,
    AssessmentResponse,
    AssessmentSession,
    Competency,
    Course,
    CourseCompetency,
    CourseLearningOutcome,
    CourseModule,
    CourseTopic,
    Department,
    LearnerSkillState,
    Organization,
    Position,
    Profile,
    ProfileActivity,
    ProfileDesiredCompetency,
    ProfileTraining,
    Role,
    RoleActivity,
    SkillNode,
    SkillPrerequisite,
    TrainingCatalog,
)
from app.seed.question_bank import CS_QUESTION_BANK
from app.seed.course_catalog import seed_course_catalog
from app.seed.dsa_curriculum import DSA_COMPETENCIES, DSA_PREREQUISITES, DSA_PROFILE_ID, DSA_SKILLS, DSA_STUDY_ORDER, DSA_SUBJECT
from app.seed.dsa_question_bank import DSA_QUESTION_BANK


def upsert(db: Session, model, key_name: str, values: dict):
    existing = db.get(model, values[key_name])
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        return existing

    item = model(**values)
    db.add(item)
    return item


def ensure_link(db: Session, model, filters: dict, values: dict | None = None):
    query = db.query(model)
    for key, value in filters.items():
        query = query.filter(getattr(model, key) == value)

    existing = query.first()
    if existing:
        return existing

    item = model(**filters, **(values or {}))
    db.add(item)
    return item


def upsert_by_field(db: Session, model, field_name: str, values: dict):
    existing = db.query(model).filter(getattr(model, field_name) == values[field_name]).first()
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        return existing

    item = model(**values)
    db.add(item)
    return item


def remove_statistics_seed_data(db: Session):
    competency_ids = [f"COMP{number:03d}" for number in range(1, 10)]
    skill_ids = [f"SKILL{number:03d}" for number in range(1, 37)]
    activity_ids = [f"ACT{number:03d}" for number in range(1, 6)]
    training_ids = [f"TRAIN{number:03d}" for number in range(1, 5)]
    session_ids = db.query(AssessmentSession.session_id).filter(AssessmentSession.profile_id == "PROFILE001")
    question_ids = db.query(AssessmentQuestion.question_id).filter(
        (AssessmentQuestion.profile_id == "PROFILE001") | AssessmentQuestion.competency_id.in_(competency_ids)
    )
    db.query(AssessmentResponse).filter(
        AssessmentResponse.session_id.in_(session_ids) | AssessmentResponse.question_id.in_(question_ids)
    ).delete(synchronize_session=False)
    db.query(AssessmentSession).filter(AssessmentSession.profile_id == "PROFILE001").delete()
    db.query(AssessmentQuestion).filter(AssessmentQuestion.question_id.in_(question_ids)).delete(synchronize_session=False)
    db.query(LearnerSkillState).filter(
        (LearnerSkillState.profile_id == "PROFILE001") | LearnerSkillState.skill_node_id.in_(skill_ids)
    ).delete(synchronize_session=False)
    for model in [ProfileActivity, ProfileTraining, ProfileDesiredCompetency]:
        db.query(model).filter(model.profile_id == "PROFILE001").delete()
    db.query(Profile).filter(Profile.id == "PROFILE001").delete()

    course_ids = [f"STAT-COURSE-{number:03d}" for number in range(1, 11)]
    for model in [CourseCompetency, CourseTopic, CourseLearningOutcome, CourseModule]:
        db.query(model).filter(model.course_id.in_(course_ids)).delete(synchronize_session=False)
    db.query(Course).filter(Course.course_id.in_(course_ids)).delete(synchronize_session=False)
    db.query(SkillPrerequisite).filter(
        SkillPrerequisite.skill_node_id.in_(skill_ids) | SkillPrerequisite.prerequisite_skill_node_id.in_(skill_ids)
    ).delete(synchronize_session=False)
    db.query(ActivityCompetency).filter(
        ActivityCompetency.activity_id.in_(activity_ids) | ActivityCompetency.competency_id.in_(competency_ids)
    ).delete(synchronize_session=False)
    db.query(RoleActivity).filter(
        (RoleActivity.role_id == "ROLE001") | RoleActivity.activity_id.in_(activity_ids)
    ).delete(synchronize_session=False)
    for model, key, values in [
        (SkillNode, "skill_node_id", skill_ids),
        (Competency, "competency_id", competency_ids),
        (Activity, "activity_id", activity_ids),
        (TrainingCatalog, "training_id", training_ids),
        (Role, "role_id", ["ROLE001"]),
        (Position, "position_id", ["POS001"]),
        (Department, "department_id", ["DEP001"]),
        (Organization, "organization_id", ["ORG001"]),
    ]:
        db.query(model).filter(getattr(model, key).in_(values)).delete(synchronize_session=False)


def seed_database(db: Session):
    remove_statistics_seed_data(db)
    cs_competencies = [
        ("COMP-CS-001", "Coding Skills", "Ability to understand, write, debug and reason about software programs.", "Computer Science"),
        ("COMP-CS-002", "Logical Reasoning", "Ability to reason about conditions, sequences, relationships and computational logic.", "Computer Science"),
        ("COMP-CS-003", "Problem Solving", "Ability to decompose programming problems and develop correct algorithmic solutions.", "Computer Science"),
        ("COMP-CS-004", "Analytical Thinking", "Ability to analyze computational problems, tradeoffs, complexity and system behavior.", "Computer Science"),
        ("COMP-CS-005", "AI/ML", "Ability to understand basic machine learning concepts and model behavior.", "Computer Science"),
        ("COMP-CS-006", "Android Development", "Ability to build Android applications using modern Android development practices.", "Computer Science"),
        ("COMP-CS-007", "Web Development", "Ability to build web applications and backend APIs.", "Computer Science"),
    ]
    for competency_id, name, description, category in cs_competencies:
        upsert(db, Competency, "competency_id", {
            "competency_id": competency_id,
            "name": name,
            "description": description,
            "category": category,
        })

    cs_skill_nodes = [
        ("CS-SKILL-OOPS", "COMP-CS-001", "OOPS", "Object-oriented programming concepts including encapsulation, inheritance, polymorphism and design relationships.", 2),
        ("CS-SKILL-DSA", "COMP-CS-002", "DSA", "Data structures, algorithms, complexity reasoning and algorithmic patterns.", 2),
        ("CS-SKILL-PROBLEM", "COMP-CS-003", "Algorithmic Problem Solving", "Decomposes programming problems, selects approaches and reasons about constraints.", 2),
        ("CS-SKILL-DBMS", "COMP-CS-004", "DBMS", "Relational data modeling, SQL reasoning, normalization, transactions and indexes.", 2),
        ("CS-SKILL-OS", "COMP-CS-004", "Operating Systems", "Processes, threads, scheduling, synchronization, memory management and deadlocks.", 2),
        ("CS-SKILL-ML", "COMP-CS-005", "Machine Learning Fundamentals", "Features, labels, model training and evaluation basics.", 2),
        ("CS-SKILL-MODEL-EVAL", "COMP-CS-005", "Model Evaluation", "Evaluates model behavior with suitable metrics and validation methods.", 2),
        ("CS-SKILL-ANDROID", "COMP-CS-006", "Android Fundamentals", "Android lifecycle, UI, state and application structure.", 1),
        ("CS-SKILL-COMPOSE", "COMP-CS-006", "Jetpack Compose", "Declarative Android UI development with Compose.", 2),
        ("CS-SKILL-WEB", "COMP-CS-007", "Web Fundamentals", "HTML, CSS, JavaScript and client-server web basics.", 1),
        ("CS-SKILL-API", "COMP-CS-007", "Backend/API Development", "REST APIs, backend request handling and persistence fundamentals.", 2),
    ]
    for skill_node_id, competency_id, name, description, difficulty_level in cs_skill_nodes:
        upsert(db, SkillNode, "skill_node_id", {
            "skill_node_id": skill_node_id,
            "competency_id": competency_id,
            "name": name,
            "description": description,
            "difficulty_level": difficulty_level,
        })

    db.query(SkillPrerequisite).delete()
    prerequisites = [
        ("CS-SKILL-PROBLEM", "CS-SKILL-DSA"),
        ("CS-SKILL-OS", "CS-SKILL-DSA"),
        ("CS-SKILL-MODEL-EVAL", "CS-SKILL-ML"),
        ("CS-SKILL-COMPOSE", "CS-SKILL-ANDROID"),
        ("CS-SKILL-API", "CS-SKILL-WEB"),
    ]
    for skill_node_id, prerequisite_skill_node_id in prerequisites:
        ensure_link(db, SkillPrerequisite, {
            "skill_node_id": skill_node_id,
            "prerequisite_skill_node_id": prerequisite_skill_node_id,
        })


    upsert(db, Organization, "organization_id", {
        "organization_id": "ORG-CS-001",
        "name": "J.C. Bose University / Computer Science",
    })
    upsert(db, Department, "department_id", {
        "department_id": "DEP-CS-001",
        "organization_id": "ORG-CS-001",
        "name": "Computer Science",
    })
    upsert(db, Position, "position_id", {
        "position_id": "POS-CS-001",
        "department_id": "DEP-CS-001",
        "designation": "Computer Science Student",
    })
    upsert(db, Role, "role_id", {
        "role_id": "ROLE-CS-001",
        "name": "Software / Computer Science Learner",
        "description": "Builds foundations in programming, algorithms, systems, databases and software design.",
    })
    cs_activities = [
        ("ACT-CS-001", "Coding Practice", "Writes, debugs and reasons about software programs."),
        ("ACT-CS-002", "Algorithmic Reasoning", "Solves computational problems using data structures and algorithms."),
        ("ACT-CS-003", "Systems and Data Reasoning", "Analyzes databases, operating systems and computational tradeoffs."),
        ("ACT-CS-004", "Software Problem Solving", "Decomposes programming tasks and chooses suitable implementation approaches."),
    ]
    for activity_id, name, description in cs_activities:
        upsert(db, Activity, "activity_id", {
            "activity_id": activity_id,
            "name": name,
            "description": description,
        })
        ensure_link(db, RoleActivity, {"role_id": "ROLE-CS-001", "activity_id": activity_id})

    cs_activity_competencies = [
        ("ACT-CS-001", "COMP-CS-001", 3),
        ("ACT-CS-002", "COMP-CS-002", 3),
        ("ACT-CS-003", "COMP-CS-004", 3),
        ("ACT-CS-004", "COMP-CS-003", 3),
    ]
    for activity_id, competency_id, target_level in cs_activity_competencies:
        ensure_link(
            db,
            ActivityCompetency,
            {"activity_id": activity_id, "competency_id": competency_id},
            {"target_level": target_level},
        )

    upsert(db, Profile, "id", {
        "id": "PROFILE002",
        "full_name": "Arjun Mehta",
        "preferred_language": "English",
    })

    for activity_id, _, _ in cs_activities:
        ensure_link(db, ProfileActivity, {"profile_id": "PROFILE002", "activity_id": activity_id})

    cs_desired_competencies = [
        ("COMP-CS-005", 2),
        ("COMP-CS-006", 2),
        ("COMP-CS-007", 2),
    ]
    for competency_id, target_level in cs_desired_competencies:
        ensure_link(
            db,
            ProfileDesiredCompetency,
            {"profile_id": "PROFILE002", "competency_id": competency_id},
            {"target_level": target_level},
        )

    seed_questions(db, CS_QUESTION_BANK, "PROFILE002")
    seed_dsa_curriculum(db)
    seed_course_catalog(db)
    db.commit()


def seed_questions(db: Session, question_bank: list[dict], profile_id: str):
    for question in question_bank:
        options = {item["id"]: item["text"] for item in question["options"]}
        correct_options = question["correct_options"]
        irt_b = question["difficulty"]
        difficulty_label = "Basic" if irt_b < -0.25 else "Intermediate" if irt_b <= 0.75 else "Advanced"
        upsert_by_field(db, AssessmentQuestion, "question_id", {
            "question_id": question["question_id"],
            "profile_id": profile_id,
            "skill_node_id": question["skill_node_id"],
            "competency_id": question["competency_id"],
            "question_text": question["question_text"],
            "option_a": options["A"],
            "option_b": options["B"],
            "option_c": options["C"],
            "option_d": options["D"],
            "correct_option": correct_options[0],
            "difficulty": difficulty_label,
            "irt_b": irt_b,
            "question_type": question["question_type"],
            "cognitive_level": question["cognitive_level"],
            "correct_options": json.dumps(correct_options),
            "misconception_tags": json.dumps(question["misconception_tags"]),
            "explanation": question["explanation"],
        })

def seed_dsa_curriculum(db: Session):
    upsert(db, Department, "department_id", {
        "department_id": "DEP-DSA",
        "organization_id": "ORG-CS-001",
        "name": DSA_SUBJECT,
    })
    upsert(db, Position, "position_id", {
        "position_id": "POS-DSA",
        "department_id": "DEP-DSA",
        "designation": "DSA Learner",
    })
    upsert(db, Role, "role_id", {
        "role_id": "ROLE-DSA",
        "name": "Data Structures and Algorithms Learner",
        "description": "Analyzes algorithms and solves problems using data structures and algorithmic strategies.",
    })
    for competency_id, name, description in DSA_COMPETENCIES:
        upsert(db, Competency, "competency_id", {
            "competency_id": competency_id,
            "name": name,
            "description": description,
            "category": DSA_SUBJECT,
        })
        activity_id = competency_id.replace("COMP-", "ACT-")
        upsert(db, Activity, "activity_id", {
            "activity_id": activity_id,
            "name": name,
            "description": description,
        })
        ensure_link(db, RoleActivity, {"role_id": "ROLE-DSA", "activity_id": activity_id})
        ensure_link(db, ActivityCompetency, {
            "activity_id": activity_id,
            "competency_id": competency_id,
        }, {"target_level": 3})

    for skill_node_id, competency_id, name, description, difficulty_level in DSA_SKILLS:
        upsert(db, SkillNode, "skill_node_id", {
            "skill_node_id": skill_node_id,
            "competency_id": competency_id,
            "name": name,
            "description": description,
            "difficulty_level": difficulty_level,
        })
    for skill_node_id, prerequisite_skill_node_id in DSA_PREREQUISITES:
        ensure_link(db, SkillPrerequisite, {
            "skill_node_id": skill_node_id,
            "prerequisite_skill_node_id": prerequisite_skill_node_id,
            "relationship_type": "prerequisite",
        })
    for skill_node_id, preceding_skill_node_id in DSA_STUDY_ORDER:
        ensure_link(db, SkillPrerequisite, {
            "skill_node_id": skill_node_id,
            "prerequisite_skill_node_id": preceding_skill_node_id,
            "relationship_type": "study_order",
        })

    upsert(db, Profile, "id", {
        "id": DSA_PROFILE_ID,
        "full_name": "Arjun Mehta",
        "preferred_language": "English",
    })
    db.flush()
    for competency_id, _, _ in DSA_COMPETENCIES:
        ensure_link(db, ProfileActivity, {
            "profile_id": DSA_PROFILE_ID,
            "activity_id": competency_id.replace("COMP-", "ACT-"),
        })
    seed_questions(db, DSA_QUESTION_BANK, DSA_PROFILE_ID)
