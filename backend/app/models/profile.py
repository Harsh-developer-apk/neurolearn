from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"), nullable=False)
    position_id: Mapped[str] = mapped_column(ForeignKey("positions.position_id"), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.role_id"), nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False)
    highest_qualification: Mapped[str] = mapped_column(String, nullable=False)
    specialization: Mapped[str] = mapped_column(String, nullable=False)


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
