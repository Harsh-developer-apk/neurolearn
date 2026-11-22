from pydantic import BaseModel


class CompetencyOut(BaseModel):
    competency_id: str
    name: str
    description: str
    category: str


class RequiredCompetencyOut(CompetencyOut):
    required: bool = True
    source_activity_ids: list[str]
    target_level: int


class DesiredCompetencyOut(CompetencyOut):
    target_level: int
    target_label: str


class RequiredCompetenciesResponse(BaseModel):
    profile_id: str
    source: str
    competencies: list[RequiredCompetencyOut]


class DesiredCompetenciesResponse(BaseModel):
    profile_id: str
    source: str
    competencies: list[DesiredCompetencyOut]


class ProfileTargetsResponse(BaseModel):
    profile_id: str
    required_competencies: list[RequiredCompetencyOut]
    desired_competencies: list[DesiredCompetencyOut]


class SkillNodeOut(BaseModel):
    skill_node_id: str
    competency_id: str
    name: str
    description: str
    difficulty_level: int
    prerequisites: list[str]
    study_predecessors: list[str] = []
    next_skills: list[str]


class CompetencySkillsResponse(BaseModel):
    competency_id: str
    name: str
    description: str
    category: str
    skill_nodes: list[SkillNodeOut]


class CompetencyGraphResponse(BaseModel):
    competencies: list[CompetencySkillsResponse]
    relationships: list[dict[str, str]]


class TargetSkillGroupOut(BaseModel):
    competency_id: str
    competency_name: str
    target_level: int
    target_label: str | None = None
    skill_nodes: list[SkillNodeOut]


class ProfileTargetSkillsResponse(BaseModel):
    profile_id: str
    required: list[TargetSkillGroupOut]
    desired: list[TargetSkillGroupOut]


class SkillTraversalResponse(BaseModel):
    skill_node_id: str
    skills: list[SkillNodeOut]
