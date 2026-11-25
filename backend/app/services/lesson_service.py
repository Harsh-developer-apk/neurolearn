import json
import logging
import os
import re
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    AssessmentQuestion,
    AssessmentResponse,
    AssessmentSession,
    LearnerSkillState,
    Profile,
    SyllabusDocument,
    SkillNode,
    SkillPrerequisite,
)
from app.seed.dsa_curriculum import DSA_PROFILE_ID, DSA_SKILLS
from app.services.ai_provider import generate_json
from app.services.profile_service import get_learning_scope


logger = logging.getLogger("neurolearn.ai")
MAX_PLAN_BLOCKS = 12
MAX_LESSON_BLOCKS = 20


def _json_object(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="The lesson provider returned invalid structured content.") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail="The lesson provider returned an unexpected response.")
    return value


def _topic_context(db: Session, skill_node_id: str, profile_id: str):
    skill = db.query(SkillNode).filter(SkillNode.skill_node_id == skill_node_id).first()
    if not skill or skill_node_id not in {row[0] for row in DSA_SKILLS}:
        raise HTTPException(status_code=404, detail="Unknown DSA topic.")
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Learner profile was not found.")
    learning_scope = get_learning_scope(db, profile_id)
    if learning_scope and skill_node_id not in learning_scope["included_skill_ids"]:
        raise HTTPException(status_code=403, detail="This topic is outside the syllabus scope selected for this learner.")

    edges = db.query(SkillPrerequisite).filter(
        or_(
            SkillPrerequisite.skill_node_id == skill_node_id,
            SkillPrerequisite.prerequisite_skill_node_id == skill_node_id,
        ),
        SkillPrerequisite.relationship_type.in_(["prerequisite", "study_order"]),
    ).all()
    prerequisites = sorted({
        edge.prerequisite_skill_node_id
        for edge in edges
        if edge.skill_node_id == skill_node_id and edge.relationship_type == "prerequisite"
    })
    related_ids = {skill_node_id, *prerequisites}
    for edge in edges:
        related_ids.update((edge.skill_node_id, edge.prerequisite_skill_node_id))

    state = db.query(LearnerSkillState).filter(
        LearnerSkillState.profile_id == profile_id,
        LearnerSkillState.skill_node_id == skill_node_id,
    ).first()
    learner = {
        "preferred_language": profile.preferred_language,
        "topic_mastery_estimate": round(state.mastery_probability, 2) if state else None,
        "diagnostic_attempts": state.attempts if state else 0,
        "course_or_class": profile.course_or_class,
        "learning_goal": profile.learning_goal,
        "goal_details": profile.goal_details,
    }
    if learning_scope:
        document = db.query(SyllabusDocument).filter(SyllabusDocument.profile_id == profile_id).order_by(SyllabusDocument.created_at.desc()).first()
        learner["syllabus_scope"] = learning_scope
        learner["syllabus_context"] = _syllabus_context(document.extracted_text, skill) if document else []
    return skill, prerequisites, related_ids, learner


def _syllabus_context(text: str, skill: SkillNode) -> list[str]:
    stop_words = {"and", "the", "with", "from", "into", "use", "using", "for", "its", "their", "about"}
    topic_terms = {
        term for term in re.findall(r"[a-z0-9]+", f"{skill.name} {skill.description}".casefold())
        if len(term) > 2 and term not in stop_words
    }
    paragraphs = [part.strip() for part in re.split(r"\n+|(?<=[.!?])\s+", text) if part.strip()]
    ranked = []
    for paragraph in paragraphs:
        words = set(re.findall(r"[a-z0-9]+", paragraph.casefold()))
        score = len(topic_terms & words)
        if score:
            ranked.append((score, paragraph[:800]))
    ranked.sort(key=lambda item: (-item[0], len(item[1])))
    return [text for _, text in ranked[:4]]


def _diagnostic_misconceptions(db: Session, profile_id: str, skill_node_id: str, related_ids: set[str]) -> list[dict]:
    rows = (
        db.query(AssessmentResponse, AssessmentQuestion)
        .join(AssessmentQuestion, AssessmentResponse.question_id == AssessmentQuestion.question_id)
        .join(AssessmentSession, AssessmentResponse.session_id == AssessmentSession.session_id)
        .filter(
            AssessmentSession.profile_id == profile_id,
            AssessmentResponse.skill_node_id.in_(related_ids),
            AssessmentResponse.correct.is_(False),
            # Project policy: a confidence-1 guess is not evidence of a misconception.
            AssessmentResponse.confidence > 1,
        )
        .order_by(AssessmentResponse.created_at.desc())
        .all()
    )
    counts = Counter()
    for response, question in rows:
        try:
            tags = json.loads(question.misconception_tags or "[]")
        except (TypeError, json.JSONDecodeError):
            tags = []
        for tag in tags:
            if isinstance(tag, str) and tag.strip():
                counts[(response.skill_node_id, tag)] += 1
    if not counts:
        return []

    names = {
        node.skill_node_id: node.name
        for node in db.query(SkillNode).filter(SkillNode.skill_node_id.in_(related_ids)).all()
    }
    ordered = sorted(counts.items(), key=lambda item: (item[0][0] != skill_node_id, -item[1], item[0][1]))
    return [
        {
            "skill_node_id": topic_id,
            "topic": names.get(topic_id, topic_id),
            "indicator": tag.replace("_", " "),
            "evidence_count": count,
        }
        for (topic_id, tag), count in ordered[:6]
    ]


def _valid_plan_blocks(blocks) -> bool:
    return (
        isinstance(blocks, list)
        and 1 <= len(blocks) <= MAX_PLAN_BLOCKS
        and all(
            isinstance(item, dict)
            and isinstance(item.get("title"), str)
            and isinstance(item.get("objective"), str)
            and isinstance(item.get("subtopics", []), list)
            for item in blocks
        )
    )


def _valid_lesson(lesson: dict) -> bool:
    if not isinstance(lesson.get("title"), str) or not lesson["title"].strip():
        return False
    if not isinstance(lesson.get("overview"), str) or not lesson["overview"].strip():
        return False
    blocks = lesson.get("content_blocks")
    takeaways = lesson.get("key_takeaways")
    guidance = lesson.get("misconception_guidance")
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= MAX_LESSON_BLOCKS:
        return False
    if not isinstance(takeaways, list) or not takeaways or not all(isinstance(item, str) and item.strip() for item in takeaways):
        return False
    if not isinstance(guidance, list):
        return False

    for block in blocks:
        if not isinstance(block, dict):
            return False
        kind = block.get("type")
        if kind == "text" and all(isinstance(block.get(key), str) and block[key].strip() for key in ("heading", "content")):
            continue
        if kind == "code" and all(isinstance(block.get(key), str) and block[key].strip() for key in ("title", "language", "code")):
            continue
        if kind == "table" and isinstance(block.get("title"), str) and isinstance(block.get("columns"), list) and block["columns"] and isinstance(block.get("rows"), list) and block["rows"]:
            if all(isinstance(row, list) and len(row) == len(block["columns"]) for row in block["rows"]):
                continue
        if kind == "steps" and isinstance(block.get("title"), str) and isinstance(block.get("items"), list) and block["items"] and all(isinstance(item, str) and item.strip() for item in block["items"]):
            continue
        if kind == "callout" and isinstance(block.get("title"), str) and isinstance(block.get("content"), str) and block["content"].strip():
            continue
        if kind == "complexity" and isinstance(block.get("time"), str) and block["time"].strip() and isinstance(block.get("space"), str) and block["space"].strip():
            continue
        if kind == "diagram" and isinstance(block.get("nodes"), list) and isinstance(block.get("edges"), list):
            if all(isinstance(node, dict) and isinstance(node.get("id"), str) and isinstance(node.get("label"), str) for node in block["nodes"]) and all(isinstance(edge, dict) and isinstance(edge.get("from"), str) and isinstance(edge.get("to"), str) for edge in block["edges"]):
                continue
        return False
    return all(
        isinstance(item, dict)
        and all(isinstance(item.get(key), str) for key in ("topic", "indicator", "correction"))
        for item in guidance
    )


def _normalize_lesson(lesson: dict) -> dict:
    """Map common model schema variations into the renderer's small safe block vocabulary."""
    if isinstance(lesson.get("lesson"), dict):
        lesson = lesson["lesson"]

    raw_blocks = lesson.get("content_blocks")
    if isinstance(raw_blocks, str):
        try:
            parsed_blocks = json.loads(raw_blocks)
            raw_blocks = parsed_blocks if isinstance(parsed_blocks, (list, dict)) else [{"type": "text", "heading": "Explanation", "content": raw_blocks}]
        except json.JSONDecodeError:
            raw_blocks = [{"type": "text", "heading": "Explanation", "content": raw_blocks}]
    if isinstance(raw_blocks, dict):
        nested = next((raw_blocks[key] for key in ("blocks", "items", "sections") if isinstance(raw_blocks.get(key), list)), None)
        if nested is not None:
            raw_blocks = nested
        elif any(key in raw_blocks for key in ("type", "kind", "content", "text", "body", "code", "rows")):
            raw_blocks = [raw_blocks]
        else:
            raw_blocks = [
                {"type": "text", "heading": str(key).replace("_", " ").title(), "content": value}
                for key, value in raw_blocks.items()
            ]
    if not isinstance(raw_blocks, list):
        raw_blocks = []
        for section in lesson.get("sections", []) if isinstance(lesson.get("sections"), list) else []:
            if isinstance(section, dict):
                raw_blocks.append({"type": "text", "heading": section.get("heading", section.get("title", "Explanation")), "content": section.get("content", section.get("text", ""))})
        old_example = lesson.get("worked_example")
        if isinstance(old_example, dict):
            raw_blocks.append({"type": "steps", "title": old_example.get("title", "Worked example"), "items": old_example.get("steps", [])})
        if not raw_blocks and isinstance(lesson.get("content"), str):
            raw_blocks.append({"type": "text", "heading": "Explanation", "content": lesson["content"]})

    aliases = {
        "paragraph": "text", "explanation": "text", "section": "text",
        "markdown": "text", "bullet_list": "steps", "ordered_list": "steps", "list": "steps",
        "code_snippet": "code", "program": "code",
        "code_example": "code", "comparison_table": "table", "comparison": "table", "trace_table": "table",
        "ordered_steps": "steps", "example": "steps", "walkthrough": "steps",
        "mistake": "callout", "tip": "callout", "warning": "callout",
        "complexity_analysis": "complexity", "visualization": "diagram",
    }
    normalized = []
    for block in raw_blocks:
        if not isinstance(block, dict):
            continue
        kind = block.get("type", block.get("kind", ""))
        if not kind:
            kind = "code" if any(key in block for key in ("code", "snippet")) else "table" if "rows" in block else "text"
        kind = aliases.get(str(kind).lower(), str(kind).lower())
        if kind == "text":
            content = block.get("content", block.get("text", block.get("body", "")))
            normalized.append({"type": kind, "heading": str(block.get("heading", block.get("title", "Explanation"))), "content": str(content)})
        elif kind == "code":
            normalized.append({
                "type": kind,
                "title": str(block.get("title", "Code example")),
                "language": str(block.get("language", block.get("programming_language", "text"))),
                "code": str(block.get("code", block.get("snippet", ""))),
                "explanation": str(block.get("explanation", block.get("description", ""))),
            })
        elif kind == "table":
            columns = block.get("columns", block.get("headers", []))
            rows = block.get("rows", [])
            if isinstance(columns, list) and isinstance(rows, list):
                normalized.append({
                    "type": kind,
                    "title": str(block.get("title", "Comparison")),
                    "columns": [str(value) for value in columns],
                    "rows": [[str(value) for value in row] for row in rows if isinstance(row, list)],
                })
        elif kind == "steps":
            items = block.get("items", block.get("steps", []))
            if isinstance(items, list):
                normalized.append({"type": kind, "title": str(block.get("title", "Worked example")), "items": [str(value) for value in items]})
        elif kind == "callout":
            tone = block.get("tone", kind if kind in {"tip", "warning", "mistake"} else "note")
            normalized.append({"type": kind, "title": str(block.get("title", "Remember")), "tone": str(tone), "content": str(block.get("content", block.get("text", block.get("description", ""))))})
        elif kind == "complexity":
            normalized.append({
                "type": kind,
                "time": str(block.get("time", block.get("time_complexity", "Not specified"))),
                "space": str(block.get("space", block.get("space_complexity", "Not specified"))),
                "explanation": str(block.get("explanation", block.get("notes", ""))),
            })
        elif kind == "diagram":
            nodes = block.get("nodes", [])
            edges = block.get("edges", [])
            if isinstance(nodes, list) and isinstance(edges, list):
                normalized.append({"type": kind, "title": str(block.get("title", "Concept diagram")), "nodes": nodes, "edges": edges})
        else:
            content = block.get("content", block.get("text", block.get("body", block.get("description", block.get("explanation", "")))))
            if isinstance(content, (dict, list)):
                content = json.dumps(content, ensure_ascii=False, indent=2)
            if str(content).strip():
                normalized.append({
                    "type": "text",
                    "heading": str(block.get("heading", block.get("title", block.get("label", "Explanation")))),
                    "content": str(content),
                })

    if not normalized:
        fallback_text = lesson.get("content", lesson.get("explanation", lesson.get("overview", lesson.get("introduction", ""))))
        if isinstance(fallback_text, (dict, list)):
            fallback_text = json.dumps(fallback_text, ensure_ascii=False, indent=2)
        if str(fallback_text).strip():
            normalized.append({"type": "text", "heading": "Explanation", "content": str(fallback_text)})

    takeaways = lesson.get("key_takeaways", lesson.get("takeaways", []))
    if isinstance(takeaways, str):
        takeaways = [takeaways]
    guidance = lesson.get("misconception_guidance", [])
    if isinstance(guidance, dict):
        guidance = [guidance]
    normalized_lesson = {
        "title": str(lesson.get("title", lesson.get("heading", "Lesson"))),
        "overview": str(lesson.get("overview", lesson.get("introduction", ""))),
        "content_blocks": normalized,
        "key_takeaways": [str(item) for item in takeaways] if isinstance(takeaways, list) else [],
        "misconception_guidance": guidance if isinstance(guidance, list) else [],
    }
    return normalized_lesson


def _lesson_system_prompt() -> str:
    return (
        "You are a patient, accurate DSA tutor. Teach concepts rather than reciting quiz questions. "
        "Use learner evidence gently and never invent a weakness. Return only valid JSON matching the requested schema."
    )


def _parse_lesson_response(raw: str) -> dict | None:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None
    return value if isinstance(value, dict) else None


def _fallback_lesson(block: dict) -> dict:
    """Return a usable lesson outline if every configured model misses the schema."""
    title = str(block.get("title") or "Topic lesson")
    objective = str(block.get("objective") or "Build a clear understanding of this topic.")
    subtopics = [str(value).strip() for value in block.get("subtopics", []) if str(value).strip()]
    focus = "; ".join(subtopics) if subtopics else objective
    return {
        "title": title,
        "overview": objective,
        "content_blocks": [
            {"type": "text", "heading": "What this block covers", "content": f"{objective}\n\nKey ideas in this block: {focus}."},
            {"type": "steps", "title": "Learning path", "items": subtopics or [objective]},
            {"type": "callout", "title": "Continue learning", "tone": "note", "content": "The lesson service could not reach a model response this time. This outline is available now; use Regenerate with my prompt to request the full explanation when the provider is ready."},
        ],
        "key_takeaways": subtopics[:5] or [objective],
        "misconception_guidance": [],
    }


def create_plan(db: Session, profile_id: str, skill_node_id: str) -> dict:
    skill, prerequisites, related_ids, learner = _topic_context(db, skill_node_id, profile_id)
    misconceptions = _diagnostic_misconceptions(db, profile_id, skill_node_id, related_ids)
    sources = _retrieve(db, profile_id, skill_node_id, prerequisites, f"{skill.name} {skill.description}", 5)
    prompt = {
        "topic": {"id": skill_node_id, "name": skill.name, "description": skill.description},
        "learner": learner,
        "related_topics": sorted(related_ids - {skill_node_id}),
        "diagnostic_misconception_indicators": misconceptions,
        "retrieved_context": sources,
        "instruction": (
            "Create a complete progressive teaching plan. Choose the number of blocks this topic actually needs; "
            "do not target a fixed count or add filler. Each block has one objective and a short subtopic list. "
            "Return JSON {blocks:[{title,objective,subtopics:[...]}]}. Build from foundations toward application. "
            "Use misconception indicators to cover evidenced gaps, but do not label the learner. Follow the syllabus scope when supplied. Retrieved question explanations "
            "are supporting concept context only: do not make the lesson plan about quiz questions."
        ),
    }
    raw, provider, model = generate_json(
        "Design accurate, learner-centered DSA teaching plans. Return only valid JSON.",
        json.dumps(prompt, ensure_ascii=False), 2800, task="plan",
    )
    data = _json_object(raw)
    blocks = data.get("blocks")
    if not _valid_plan_blocks(blocks):
        logger.warning("ai_output_invalid task=plan provider=%s model=%s issue=adaptive_block_schema", provider, model)
        repair_prompt = {
            **prompt,
            "instruction": (
                "Repair the previous plan to contain a non-empty blocks array. Choose the number the topic needs; "
                "never force five or pad content. Each block needs string title, string objective, and a subtopics array. "
                f"Use no more than {MAX_PLAN_BLOCKS} blocks as a safety limit. Return JSON only."
            ),
            "previous_attempt": data,
        }
        raw, provider, model = generate_json(
            "Return a valid adaptive DSA teaching plan as JSON. Do not add text outside JSON.",
            json.dumps(repair_prompt, ensure_ascii=False), 3200, task="plan-repair",
        )
        data = _json_object(raw)
        blocks = data.get("blocks")
        if not _valid_plan_blocks(blocks):
            logger.error("ai_output_invalid task=plan-repair provider=%s model=%s issue=adaptive_block_schema", provider, model)
            raise HTTPException(status_code=502, detail="The model did not return a valid adaptive learning plan. Check backend logs.")

    return {
        "skill_node_id": skill_node_id,
        "topic": skill.name,
        "blocks": blocks,
        "learner_context": learner,
        "misconception_indicators": misconceptions,
        "sources": sources,
        "provider": provider,
        "model": model,
    }


def _retrieve(db: Session, profile_id: str, skill_id: str, prerequisite_ids: list[str], query: str, limit: int) -> list[dict]:
    ids = [skill_id, *prerequisite_ids]
    questions = db.query(AssessmentQuestion).filter(
        AssessmentQuestion.skill_node_id.in_(ids),
        AssessmentQuestion.profile_id.in_({profile_id, DSA_PROFILE_ID}),
    ).all()
    terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    ranked = []
    for question in questions:
        try:
            tags = json.loads(question.misconception_tags or "[]")
        except (TypeError, json.JSONDecodeError):
            tags = []
        text = f"{question.question_text} {question.explanation} {' '.join(tags)}".strip()
        qterms = set(re.findall(r"[a-z0-9]+", text.lower()))
        score = len(terms & qterms) / max(1, len(terms))
        score += 0.15 if question.skill_node_id == skill_id else 0
        ranked.append((score, question, text))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        {"source_id": question.question_id, "topic_id": question.skill_node_id, "content": content[:1000]}
        for _, question, content in ranked[:limit]
    ]


def create_block(db: Session, profile_id: str, skill_node_id: str, block_index: int,
                 block: dict, feedback: str, completed_blocks: list[dict]) -> dict:
    skill, prerequisites, related_ids, learner = _topic_context(db, skill_node_id, profile_id)
    misconceptions = _diagnostic_misconceptions(db, profile_id, skill_node_id, related_ids)
    block = block or {
        "title": f"Explore further: {skill.name}",
        "objective": "Extend the learner's understanding with a useful next concept",
        "subtopics": [],
    }
    query = " ".join([skill.name, str(block.get("title", "")), str(block.get("objective", "")), feedback])
    sources = _retrieve(db, profile_id, skill_node_id, prerequisites, query, 5)
    prompt = {
        "topic": {"name": skill.name, "description": skill.description},
        "learner": learner,
        "related_topics": sorted(related_ids - {skill_node_id}),
        "diagnostic_misconception_indicators": misconceptions,
        "requested_block_number": block_index + 1,
        "block_plan": block,
        "prior_block_titles_and_objectives": completed_blocks,
        "learner_feedback": feedback.strip(),
        "retrieved_context": sources,
        "requirements": (
            "Teach only this block, completely and without filler. Explain a clear mental model and a relatable example. "
            "Use code only when it materially helps; if feedback explicitly requests Java, C++, Python, Kotlin, or another "
            "language, use that language. Otherwise use pseudocode or omit code. When code is useful, explain it line by line "
            "and analyze time and space complexity. Include an operation/alternative comparison table when useful. Explain common "
            "mistakes. Do not write a quiz and do not center the lesson on retrieved questions. Address the supplied misconception "
            "indicators gently, distinguishing related-topic evidence from this topic, and do not invent indicators. "
            "When syllabus scope/context is present in learner data, stay within selected units and align examples to its wording; "
            "treat it as scope guidance rather than a replacement for accurate subject knowledge. "
            "Return JSON fields: title, overview, content_blocks, key_takeaways, misconception_guidance. Content block types: "
            "text {type,heading,content}; code {type,title,language,code,explanation}; "
            "table {type,title,columns:[...],rows:[[...]]}; steps {type,title,items:[...]}; "
            "callout {type,title,tone,content}; complexity {type,time,space,explanation}; "
            "diagram {type,title,nodes:[{id,label,x,y}],edges:[{from,to,label}]}. Use only helpful block types, "
            "1-20 content blocks, and diagram coordinates between 5 and 95. "
            "misconception_guidance is [{topic,indicator,correction}] and must be [] when no evidence is supplied."
        ),
    }
    provider = "unknown"
    model = "unknown"
    lesson = None
    try:
        raw, provider, model = generate_json(
            _lesson_system_prompt(), json.dumps(prompt, ensure_ascii=False), 7000, task="lesson-block",
        )
        original_lesson = _parse_lesson_response(raw)
        lesson = _normalize_lesson(original_lesson or {})
    except Exception as exc:
        original_lesson = None
        logger.warning("lesson_generation_recovery task=lesson-block stage=primary exception_type=%s", type(exc).__name__)

    if not _valid_lesson(lesson or {}):
        logger.warning("ai_output_invalid task=lesson-block provider=%s model=%s issue=rich_content_schema top_keys=%s",
                       provider, model, sorted(original_lesson.keys()) if original_lesson else [])
        # A fresh request to Gemini's native JSON endpoint avoids repeating the
        # same provider's schema failure and works even when the OpenAI adapter
        # has intermittent structured-output issues.
        try:
            fallback_model = os.getenv("GEMINI_LESSON_MODEL", "gemini-3.5-flash-lite")
            raw, provider, model = generate_json(
                "You are an accurate, patient DSA tutor. Create the lesson requested in the user data. "
                "Return one complete JSON object only. Never echo the request. All fields must be present and non-null. "
                "Include title, overview, 2 to 6 content_blocks, key_takeaways, and misconception_guidance. "
                "Every content block must use one supported type and have its required fields.",
                json.dumps(prompt, ensure_ascii=False), 6000, task="lesson-native-fallback",
                providers=["gemini"], model_overrides={"gemini": fallback_model}, native_gemini=True,
            )
            recovered = _normalize_lesson(_parse_lesson_response(raw) or {})
            if _valid_lesson(recovered):
                lesson = recovered
            else:
                logger.warning("ai_output_invalid task=lesson-native-fallback provider=%s model=%s issue=rich_content_schema", provider, model)
        except Exception as exc:
            logger.warning("lesson_generation_recovery task=lesson-block stage=native_fallback exception_type=%s", type(exc).__name__)

    if not _valid_lesson(lesson or {}):
        lesson = _fallback_lesson(block)
        provider, model = "local-fallback", "built-in lesson outline"
        logger.warning("ai_output_fallback task=lesson-block provider=%s model=%s", provider, model)

    return {
        "skill_node_id": skill_node_id,
        "block_index": block_index,
        "lesson": lesson,
        "sources": sources,
        "misconception_indicators": misconceptions,
        "provider": provider,
        "model": model,
    }
