from typing import Literal

from pydantic import BaseModel, Field


class ActivityOut(BaseModel):
    activity_id: str
    name: str
    description: str


class TrainingOut(BaseModel):
    training_id: str
    title: str
    provider: str
    completion_status: str


class ProfileOut(BaseModel):
    profile_id: str
    full_name: str
    preferred_language: str
    age: int | None = None
    course_or_class: str | None = None
    subject_id: str = "dsa"
    learning_goal: str = "personal"
    goal_details: str | None = None
    activities: list[ActivityOut]
    training_history: list[TrainingOut]


class SyllabusPreviewRequest(BaseModel):
    filename: str | None = Field(default=None, max_length=255)
    content_type: str | None = Field(default=None, max_length=100)
    file_base64: str | None = Field(default=None, max_length=14_000_000)
    pasted_text: str | None = Field(default=None, max_length=100_000)


class LearnerOnboardingRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=10, le=100)
    course_or_class: str = Field(min_length=2, max_length=120)
    preferred_language: str = Field(default="English", min_length=2, max_length=40)
    subject_id: Literal["dsa"] = "dsa"
    learning_goal: Literal["personal", "exam"] = "personal"
    goal_details: str = Field(default="", max_length=500)
    syllabus_filename: str | None = Field(default=None, max_length=255)
    syllabus_content_type: str | None = Field(default=None, max_length=100)
    syllabus_text: str = Field(default="", max_length=100_000)
    suggested_skill_ids: list[str] = Field(default_factory=list, max_length=10)
    included_skill_ids: list[str] = Field(default_factory=list, max_length=10)
