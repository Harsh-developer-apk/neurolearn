from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import assessment, competency_graph, courses, health, learner, profile
from app.database import Base, SessionLocal, engine
from app.seed.seed_data import seed_database


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
    app.include_router(courses.router)
    return app


app = create_app()
