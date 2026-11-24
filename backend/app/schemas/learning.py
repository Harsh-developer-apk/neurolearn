from pydantic import BaseModel, Field


class LearningPlanRequest(BaseModel):
    profile_id: str = "PROFILE-DSA"
    skill_node_id: str


class LearningBlockRequest(LearningPlanRequest):
    block_index: int = Field(ge=0, le=20)
    block: dict = Field(default_factory=dict)
    feedback: str = Field(default="", max_length=400)
    completed_blocks: list[dict] = Field(default_factory=list, max_length=20)


class LessonBlock(BaseModel):
    title: str
    overview: str
    content_blocks: list[dict]
    key_takeaways: list[str]
    misconception_guidance: list[dict]


class LearningPlanResponse(BaseModel):
    skill_node_id: str
    topic: str
    blocks: list[dict]
    learner_context: dict
    misconception_indicators: list[dict]
    sources: list[dict]
    provider: str
    model: str


class LearningBlockResponse(BaseModel):
    skill_node_id: str
    block_index: int
    lesson: LessonBlock
    sources: list[dict]
    misconception_indicators: list[dict]
    provider: str
    model: str
