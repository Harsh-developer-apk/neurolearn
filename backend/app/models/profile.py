from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    course_or_class: Mapped[str | None] = mapped_column(String, nullable=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, default="dsa")
    learning_goal: Mapped[str] = mapped_column(String, nullable=False, default="personal")
    goal_details: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProfileActivity(Base):
    __tablename__ = "profile_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), nullable=False)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.activity_id"), nullable=False)


class ProfileTraining(Base):
    __tablename__ = "profile_training"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), nullable=False)
    training_id: Mapped[str] = mapped_column(ForeignKey("training_catalog.training_id"), nullable=False)
    completion_status: Mapped[str] = mapped_column(String, nullable=False)


class ProfileDesiredCompetency(Base):
    __tablename__ = "profile_desired_competencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), nullable=False)
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.competency_id"), nullable=False)
    target_level: Mapped[int] = mapped_column(Integer, nullable=False)
