from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Competency(Base):
    __tablename__ = "competencies"

    competency_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)


class ActivityCompetency(Base):
    __tablename__ = "activity_competencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.activity_id"), nullable=False)
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.competency_id"), nullable=False)
    target_level: Mapped[int] = mapped_column(Integer, nullable=False, default=2)


class SkillNode(Base):
    __tablename__ = "skill_nodes"

    skill_node_id: Mapped[str] = mapped_column(String, primary_key=True)
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.competency_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class SkillPrerequisite(Base):
    __tablename__ = "skill_prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_node_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.skill_node_id"), nullable=False)
    prerequisite_skill_node_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.skill_node_id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False, default="prerequisite")
