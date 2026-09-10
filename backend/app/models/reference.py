from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    organization_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    departments: Mapped[list["Department"]] = relationship(back_populates="organization")


class Department(Base):
    __tablename__ = "departments"

    department_id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="departments")
    positions: Mapped[list["Position"]] = relationship(back_populates="department")


class Position(Base):
    __tablename__ = "positions"

    position_id: Mapped[str] = mapped_column(String, primary_key=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"), nullable=False)
    designation: Mapped[str] = mapped_column(String, nullable=False)

    department: Mapped[Department] = relationship(back_populates="positions")


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class Activity(Base):
    __tablename__ = "activities"

    activity_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class RoleActivity(Base):
    __tablename__ = "role_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.role_id"), nullable=False)
    activity_id: Mapped[str] = mapped_column(ForeignKey("activities.activity_id"), nullable=False)


class TrainingCatalog(Base):
    __tablename__ = "training_catalog"

    training_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
