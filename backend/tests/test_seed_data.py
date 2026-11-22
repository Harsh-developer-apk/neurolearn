from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import AssessmentResponse, AssessmentSession, LearnerSkillState
from app.seed.seed_data import seed_database


def test_reseeding_removes_saved_statistics_data_and_preserves_cs_history():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, connection_record):
        connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_database(db)

        def copy_seed_row(table_name, overrides):
            table = Base.metadata.tables[table_name]
            values = dict(db.execute(select(table)).mappings().first())
            if "id" in values and table_name != "profile":
                values.pop("id")
            values.update(overrides)
            db.execute(table.insert().values(**values))

        copy_seed_row("profile", {"id": "PROFILE001"})
        copy_seed_row("competencies", {"competency_id": "COMP001"})
        copy_seed_row("skill_nodes", {"skill_node_id": "SKILL001", "competency_id": "COMP001"})
        copy_seed_row("assessment_questions", {
            "question_id": "Q001",
            "profile_id": "PROFILE001",
            "competency_id": "COMP001",
            "skill_node_id": "SKILL001",
        })
        copy_seed_row("profile_activities", {"profile_id": "PROFILE001"})
        copy_seed_row("profile_desired_competencies", {"profile_id": "PROFILE001", "competency_id": "COMP001"})
        copy_seed_row("courses", {"course_id": "STAT-COURSE-001"})
        for table_name in ["course_competencies", "course_topics", "course_learning_outcomes", "course_modules"]:
            copy_seed_row(table_name, {"course_id": "STAT-COURSE-001"})

        db.add_all([
            AssessmentSession(session_id="LEGACY", profile_id="PROFILE001"),
            AssessmentSession(session_id="KEEP-CS", profile_id="PROFILE002"),
            LearnerSkillState(profile_id="PROFILE001", skill_node_id="SKILL001", mastery_probability=0.4),
            LearnerSkillState(profile_id="PROFILE002", skill_node_id="CS-SKILL-DSA", mastery_probability=0.8),
        ])
        db.flush()
        db.add(AssessmentResponse(
            session_id="LEGACY", question_id="Q001", skill_node_id="SKILL001",
            selected_option="A", correct=False, response_time_ms=3000, sequence_number=1,
        ))
        db.commit()

        seed_database(db)
        seed_database(db)

        for table_name, column_name, removed_id in [
            ("profile", "id", "PROFILE001"),
            ("competencies", "competency_id", "COMP001"),
            ("skill_nodes", "skill_node_id", "SKILL001"),
            ("assessment_questions", "question_id", "Q001"),
            ("courses", "course_id", "STAT-COURSE-001"),
        ]:
            table = Base.metadata.tables[table_name]
            assert db.execute(select(table).where(table.c[column_name] == removed_id)).first() is None
        assert db.query(AssessmentResponse).count() == 0
        assert [session.session_id for session in db.query(AssessmentSession).all()] == ["KEEP-CS"]
        state = db.query(LearnerSkillState).one()
        assert state.profile_id == "PROFILE002"
        assert state.mastery_probability == 0.8
        assert db.connection().exec_driver_sql("PRAGMA foreign_key_check").all() == []
