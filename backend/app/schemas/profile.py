from pydantic import BaseModel


class OrganizationOut(BaseModel):
    organization_id: str
    name: str


class DepartmentOut(BaseModel):
    department_id: str
    organization_id: str
    name: str


class PositionOut(BaseModel):
    position_id: str
    department_id: str
    designation: str


class RoleOut(BaseModel):
    role_id: str
    name: str
    description: str


class ActivityOut(BaseModel):
    activity_id: str
    name: str
    description: str


class TrainingOut(BaseModel):
    training_id: str
    title: str
    provider: str
    completion_status: str


class EducationOut(BaseModel):
    qualification: str
    specialization: str


class ProfileOut(BaseModel):
    profile_id: str
    full_name: str
    preferred_language: str
    organization: OrganizationOut
    department: DepartmentOut
    position: PositionOut
    role: RoleOut
    years_experience: int
    education: EducationOut
    activities: list[ActivityOut]
    training_history: list[TrainingOut]
