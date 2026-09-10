from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), nullable=False, default="PROFILE001")
    skill_node_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.skill_node_id"), nullable=False)
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.competency_id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_option: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    irt_b: Mapped[float] = mapped_column(Float, nullable=False)
    question_type: Mapped[str] = mapped_column(String, nullable=False, default="single_choice")
    cognitive_level: Mapped[str] = mapped_column(String, nullable=False, default="recall")
    correct_options: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    misconception_tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="in_progress")
    current_question_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    theta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    assessment_mode: Mapped[str] = mapped_column(String, nullable=False, default="live")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("assessment_sessions.session_id"), nullable=False)
    question_id: Mapped[str] = mapped_column(ForeignKey("assessment_questions.question_id"), nullable=False)
    skill_node_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.skill_node_id"), nullable=False)
    selected_option: Mapped[str] = mapped_column(String, nullable=False)
    selected_options: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    correct_options: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    irt_theta_before: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    irt_theta_after: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bkt_mastery_before: Mapped[float] = mapped_column(Float, nullable=False, default=0.20)
    bkt_mastery_after: Mapped[float] = mapped_column(Float, nullable=False, default=0.20)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class LearnerSkillState(Base):
    __tablename__ = "learner_skill_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), nullable=False)
    skill_node_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.skill_node_id"), nullable=False)
    mastery_probability: Mapped[float] = mapped_column(Float, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
