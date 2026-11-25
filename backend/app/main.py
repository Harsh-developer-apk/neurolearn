from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import assessment, competency_graph, courses, health, learner, learning, profile
from app.database import Base, SessionLocal, engine
from app.seed.seed_data import seed_database


def ensure_profile_schema():
    """Remove legacy workplace/education columns while preserving profile IDs and dependents."""
    if engine.dialect.name != "sqlite":
        return
    legacy_columns = {
        "organization_id", "department_id", "position_id", "role_id",
        "years_experience", "highest_qualification", "specialization",
    }
    with engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(profile)").all()}
        connection.commit()
        if columns.intersection(legacy_columns):
            # SQLite requires FK enforcement to be disabled outside the rebuild transaction.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
            try:
                with connection.begin():
                    connection.exec_driver_sql("DROP TABLE IF EXISTS profile_new")
                    connection.exec_driver_sql(
                        "CREATE TABLE profile_new (id VARCHAR NOT NULL PRIMARY KEY, full_name VARCHAR NOT NULL, preferred_language VARCHAR NOT NULL, age INTEGER, course_or_class VARCHAR, subject_id VARCHAR NOT NULL DEFAULT 'dsa', learning_goal VARCHAR NOT NULL DEFAULT 'personal', goal_details TEXT)"
                    )
                    current = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(profile)").all()}
                    optional = {
                        "age": "age" if "age" in current else "NULL",
                        "course_or_class": "course_or_class" if "course_or_class" in current else "NULL",
                        "subject_id": "subject_id" if "subject_id" in current else "'dsa'",
                        "learning_goal": "learning_goal" if "learning_goal" in current else "'personal'",
                        "goal_details": "goal_details" if "goal_details" in current else "NULL",
                    }
                    column_list = "id, full_name, preferred_language, " + ", ".join(optional)
                    value_list = "id, full_name, preferred_language, " + ", ".join(optional.values())
                    connection.exec_driver_sql(f"INSERT INTO profile_new ({column_list}) SELECT {value_list} FROM profile")
                    connection.exec_driver_sql("DROP TABLE profile")
                    connection.exec_driver_sql("ALTER TABLE profile_new RENAME TO profile")
            finally:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                connection.commit()

    profile_defaults = {
        "age": "INTEGER",
        "course_or_class": "VARCHAR",
        "subject_id": "VARCHAR NOT NULL DEFAULT 'dsa'",
        "learning_goal": "VARCHAR NOT NULL DEFAULT 'personal'",
        "goal_details": "TEXT",
    }
    with engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(profile)").all()}
        for name, definition in profile_defaults.items():
            if columns and name not in columns:
                connection.exec_driver_sql(f"ALTER TABLE profile ADD COLUMN {name} {definition}")
        connection.commit()


def ensure_phase2_schema():
    with engine.connect() as connection:
        skill_columns = [row[1] for row in connection.exec_driver_sql("PRAGMA table_info(skill_nodes)").all()]
        if skill_columns and "difficulty_level" not in skill_columns:
            connection.exec_driver_sql("ALTER TABLE skill_nodes ADD COLUMN difficulty_level INTEGER NOT NULL DEFAULT 1")

        prereq_columns = [row[1] for row in connection.exec_driver_sql("PRAGMA table_info(skill_prerequisites)").all()]
        old_prereq_columns = {"prerequisite_skill_id", "dependent_skill_id"}
        if old_prereq_columns.intersection(prereq_columns):
            connection.exec_driver_sql("DROP TABLE skill_prerequisites")
        connection.commit()

    Base.metadata.tables["skill_prerequisites"].create(bind=engine, checkfirst=True)


def ensure_phase3_schema():
    with engine.connect() as connection:
        session_columns = [row[1] for row in connection.exec_driver_sql("PRAGMA table_info(assessment_sessions)").all()]
        if session_columns and "assessment_mode" not in session_columns:
            connection.exec_driver_sql("ALTER TABLE assessment_sessions ADD COLUMN assessment_mode TEXT NOT NULL DEFAULT 'live'")
        if session_columns and "scope_skill_node_id" not in session_columns:
            connection.exec_driver_sql("ALTER TABLE assessment_sessions ADD COLUMN scope_skill_node_id TEXT")

        question_columns = [row[1] for row in connection.exec_driver_sql("PRAGMA table_info(assessment_questions)").all()]
        question_defaults = {
            "profile_id": "TEXT NOT NULL DEFAULT 'PROFILE-DSA'",
            "question_type": "TEXT NOT NULL DEFAULT 'single_choice'",
            "cognitive_level": "TEXT NOT NULL DEFAULT 'recall'",
            "correct_options": "TEXT NOT NULL DEFAULT '[]'",
            "misconception_tags": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column_name, definition in question_defaults.items():
            if question_columns and column_name not in question_columns:
                connection.exec_driver_sql(f"ALTER TABLE assessment_questions ADD COLUMN {column_name} {definition}")

        response_columns = [row[1] for row in connection.exec_driver_sql("PRAGMA table_info(assessment_responses)").all()]
        response_defaults = {
            "selected_options": "TEXT NOT NULL DEFAULT '[]'",
            "correct_options": "TEXT NOT NULL DEFAULT '[]'",
            "confidence": "INTEGER NOT NULL DEFAULT 3",
            "irt_theta_before": "REAL NOT NULL DEFAULT 0.0",
            "irt_theta_after": "REAL NOT NULL DEFAULT 0.0",
            "bkt_mastery_before": "REAL NOT NULL DEFAULT 0.20",
            "bkt_mastery_after": "REAL NOT NULL DEFAULT 0.20",
            "created_at": "DATETIME",
        }
        for column_name, definition in response_defaults.items():
            if response_columns and column_name not in response_columns:
                connection.exec_driver_sql(f"ALTER TABLE assessment_responses ADD COLUMN {column_name} {definition}")
        connection.commit()


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    ensure_profile_schema()
    Base.metadata.tables["syllabus_documents"].create(bind=engine, checkfirst=True)
    ensure_phase2_schema()
    ensure_phase3_schema()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    app = FastAPI(title="Competency Intelligence API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(profile.router)
    app.include_router(competency_graph.router)
    app.include_router(assessment.router)
    app.include_router(learner.router)
    app.include_router(learner.profiles_router)
    app.include_router(learning.router)
    app.include_router(courses.router)
    return app


app = create_app()
