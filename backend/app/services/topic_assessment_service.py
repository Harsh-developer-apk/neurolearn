import json
import logging
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AssessmentQuestion, Competency, Profile, SkillNode
from app.services.ai_provider import generate_json


logger = logging.getLogger("neurolearn.ai")
QUESTION_COUNT = 6
VALID_COGNITIVE_LEVELS = {"recall", "understanding", "application", "analysis"}


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="The question generator returned invalid structured content.") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail="The question generator returned an unexpected response.")
    return value


def _normalize_question(item: dict, profile_id: str, skill: SkillNode, competency_id: str, batch_id: str, ordinal: int):
    if not isinstance(item, dict):
        return None
    options = item.get("options")
    if isinstance(options, list):
        options = {chr(65 + index): option for index, option in enumerate(options[:4])}
    if not isinstance(options, dict):
        return None
    options = {key: str(options.get(key, "")).strip() for key in "ABCD"}
    question_text = str(item.get("question_text", "")).strip()
    correct_option = str(item.get("correct_option", "")).strip().upper()
    cognitive_level = str(item.get("cognitive_level", "understanding")).strip().lower()
    explanation = str(item.get("explanation", "")).strip()
    tags = item.get("misconception_tags", [])
    if (not question_text or any(not value for value in options.values()) or correct_option not in options
            or cognitive_level not in VALID_COGNITIVE_LEVELS or not explanation):
        return None
    if not isinstance(tags, list):
        tags = []
    tags = [re.sub(r"[^a-z0-9_]+", "_", str(tag).lower()).strip("_") for tag in tags]
    difficulty_value = item.get("irt_b", 0.0)
    try:
        irt_b = max(-2.0, min(2.0, float(difficulty_value)))
    except (TypeError, ValueError):
        irt_b = 0.0
    difficulty = "easy" if irt_b < -0.5 else "hard" if irt_b > 0.75 else "medium"
    return AssessmentQuestion(
        question_id=f"AIQ-{batch_id}-{ordinal + 1}",
        profile_id=profile_id,
        skill_node_id=skill.skill_node_id,
        competency_id=competency_id,
        question_text=question_text,
        option_a=options["A"], option_b=options["B"], option_c=options["C"], option_d=options["D"],
        correct_option=correct_option,
        difficulty=difficulty,
        irt_b=irt_b,
        question_type="single_choice",
        cognitive_level=cognitive_level,
        correct_options=json.dumps([correct_option]),
        misconception_tags=json.dumps(tags[:5]),
        explanation=explanation,
    )


def generate_topic_questions(db: Session, profile_id: str, skill: SkillNode, batch_id: str):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    competency = db.query(Competency).filter(Competency.competency_id == skill.competency_id).first()
    if not profile or not competency:
        raise HTTPException(status_code=404, detail="Topic assessment context is unavailable.")

    system_prompt = (
        "You create accurate college-level DSA assessment questions. Return only valid JSON. "
        "Every question must have exactly four plausible options A-D and exactly one correct answer. "
        "Avoid ambiguity, trivia, duplicate questions, and facts unrelated to the supplied topic. "
        "Include a concise explanation, a misconception tag for the likely distractor error, "
        "a cognitive level (recall, understanding, application, analysis), and IRT difficulty from -2 to 2."
    )
    prompt = {
        "task": "Create a topic assessment question set to be scored by the app's existing IRT and BKT model.",
        "topic": {"id": skill.skill_node_id, "name": skill.name, "description": skill.description,
                  "competency": competency.name, "competency_id": competency.competency_id},
        "learner": {"preferred_programming_language": profile.preferred_language},
        "question_count": QUESTION_COUNT,
        "difficulty_mix": "2 accessible, 3 intermediate, 1 challenging; vary cognitive levels and test concept understanding, application, and common misconceptions.",
        "requirements": [
            "Questions may use the learner's preferred language when code improves the question; language is optional.",
            "Do not require a specific programming language unless the question explicitly includes the code.",
            "Use distinct concepts and scenarios within the topic; keep each question self-contained.",
            "Return JSON with a questions array. Each item: question_text, options object with A/B/C/D, correct_option (one letter), explanation, misconception_tags (array of snake_case strings), cognitive_level, irt_b (number from -2 to 2).",
        ],
        "schema_example": {"questions": [{"question_text": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "correct_option": "A", "explanation": "...", "misconception_tags": ["..."], "cognitive_level": "application", "irt_b": 0.25}]},
    }
    raw, provider, model = generate_json(system_prompt, json.dumps(prompt, ensure_ascii=False), max_tokens=4200, task="topic-assessment-questions")
    payload = _parse_json(raw)
    items = payload.get("questions", [])
    if not isinstance(items, list):
        raise HTTPException(status_code=502, detail="The question generator did not return a question list.")
    questions = []
    signatures = set()
    for ordinal, item in enumerate(items):
        question = _normalize_question(item, profile_id, skill, competency.competency_id, batch_id, ordinal)
        if not question:
            continue
        signature = question.question_text.casefold()
        if signature not in signatures:
            questions.append(question)
            signatures.add(signature)
    if len(questions) < 4:
        logger.warning("topic_assessment_invalid_batch profile_id=%s skill_node_id=%s valid_questions=%s provider=%s model=%s", profile_id, skill.skill_node_id, len(questions), provider, model)
        raise HTTPException(status_code=502, detail="The model returned too few valid questions. Please try again.")
    logger.info("topic_assessment_questions_saved profile_id=%s skill_node_id=%s count=%s provider=%s model=%s", profile_id, skill.skill_node_id, len(questions), provider, model)
    return questions[:QUESTION_COUNT], provider, model
