from pydantic import BaseModel


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
    activities: list[ActivityOut]
    training_history: list[TrainingOut]
