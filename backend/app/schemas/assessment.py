from pydantic import BaseModel, Field


class QuestionOut(BaseModel):
    question_id: str
    question_text: str
    options: dict[str, str]
    question_type: str
    response_mode: str
    cognitive_level: str
    difficulty: float
    competency_id: str
    skill_node_id: str


class StartAssessmentResponse(BaseModel):
    session_id: str
    question_number: int
    total_questions: int
    question: QuestionOut
    model_state: dict


class SubmitAnswerRequest(BaseModel):
    question_id: str
    selected_option: str | None = Field(default=None, pattern="^[ABCD]$")
    selected_options: list[str] | None = None
    response_time_ms: int = Field(ge=0)
    confidence: int = Field(ge=1, le=5)


class AssessmentProgressOut(BaseModel):
    current: int
    total: int


class IrtOut(BaseModel):
    theta: float
    theta_before: float | None = None
    estimated_probability: float | None = None


class SkillUpdateOut(BaseModel):
    skill_node_id: str
    mastery_probability: float
    mastery_before: float | None = None
    evidence_status: str | None = None
    attempts: int | None = None
    correct_attempts: int | None = None


class SubmitAnswerResponse(BaseModel):
    correct: bool
    explanation: str
    progress: AssessmentProgressOut
    irt: IrtOut
    skill: SkillUpdateOut
    next_question: QuestionOut | None
    model_state: dict
    decision: str
    response_evidence: dict


class AssessmentSummaryOut(BaseModel):
    questions_answered: int
    accuracy: float
    correct_count: int = 0
    incorrect_count: int = 0
    average_response_time_ms: float = 0.0
    average_confidence: float = 0.0


class AbilityOut(BaseModel):
    theta: float
    ability_label: str


class SkillMasteryOut(BaseModel):
    skill_node_id: str
    name: str
    competency_id: str
    competency_name: str
    mastery_probability: float
    raw_bkt_mastery_probability: float | None = None
    attempts: int
    correct_attempts: int
    incorrect_attempts: int = 0
    confidence_avg: float = 0.0
    avg_response_time_ms: float = 0.0
    evidence_status: str = "limited_evidence"


class AssessmentResultResponse(BaseModel):
    session_id: str
    profile_id: str
    assessment_mode: str = "live"
    assessment: AssessmentSummaryOut
    irt: AbilityOut
    skills: list[SkillMasteryOut]
    competencies: list[dict]
    confidence_analysis: dict
    response_time: dict
    misconception_signals: list[dict]


class CompetencyStateOut(BaseModel):
    competency_id: str
    competency_name: str
    competency_mastery: float
    assessed_skill_count: int
    skill_states: list[SkillMasteryOut]


class LearnerCompetencyStateResponse(BaseModel):
    profile_id: str
    source: str
    competencies: list[CompetencyStateOut]
