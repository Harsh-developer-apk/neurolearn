import json
import logging
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
    SkillNode,
    SkillPrerequisite,
)
from app.seed.dsa_curriculum import DSA_SKILLS
from app.services.ai_provider import generate_json


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
    }
    return skill, prerequisites, related_ids, learner


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
    if not isinstance(lesson.get("title"), str) or not isinstance(lesson.get("overview"), str):
        return False
    blocks = lesson.get("content_blocks")
    takeaways = lesson.get("key_takeaways")
    guidance = lesson.get("misconception_guidance")
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= MAX_LESSON_BLOCKS:
        return False
    if not isinstance(takeaways, list) or not all(isinstance(item, str) for item in takeaways):
        return False
    if not isinstance(guidance, list):
        return False

    for block in blocks:
        if not isinstance(block, dict):
            return False
        kind = block.get("type")
        if kind == "text" and all(isinstance(block.get(key), str) for key in ("heading", "content")):
            continue
        if kind == "code" and all(isinstance(block.get(key), str) for key in ("title", "language", "code")):
            continue
        if kind == "table" and isinstance(block.get("title"), str) and isinstance(block.get("columns"), list) and isinstance(block.get("rows"), list):
            if all(isinstance(row, list) and len(row) == len(block["columns"]) for row in block["rows"]):
                continue
        if kind == "steps" and isinstance(block.get("title"), str) and isinstance(block.get("items"), list) and all(isinstance(item, str) for item in block["items"]):
            continue
        if kind == "callout" and isinstance(block.get("title"), str) and isinstance(block.get("content"), str):
            continue
        if kind == "complexity" and isinstance(block.get("time"), str) and isinstance(block.get("space"), str):
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


def create_plan(db: Session, profile_id: str, skill_node_id: str) -> dict:
    skill, prerequisites, related_ids, learner = _topic_context(db, skill_node_id, profile_id)
    misconceptions = _diagnostic_misconceptions(db, profile_id, skill_node_id, related_ids)
    sources = _retrieve(db, skill_node_id, prerequisites, f"{skill.name} {skill.description}", 5)
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
            "Use misconception indicators to cover evidenced gaps, but do not label the learner. Retrieved question explanations "
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


def _retrieve(db: Session, skill_id: str, prerequisite_ids: list[str], query: str, limit: int) -> list[dict]:
    ids = [skill_id, *prerequisite_ids]
    questions = db.query(AssessmentQuestion).filter(AssessmentQuestion.skill_node_id.in_(ids)).all()
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
    sources = _retrieve(db, skill_node_id, prerequisites, query, 5)
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
            "Return JSON fields: title, overview, content_blocks, key_takeaways, misconception_guidance. Content block types: "
            "text {type,heading,content}; code {type,title,language,code,explanation}; "
            "table {type,title,columns:[...],rows:[[...]]}; steps {type,title,items:[...]}; "
            "callout {type,title,tone,content}; complexity {type,time,space,explanation}; "
            "diagram {type,title,nodes:[{id,label,x,y}],edges:[{from,to,label}]}. Use only helpful block types, "
            "1-20 content blocks, and diagram coordinates between 5 and 95. "
            "misconception_guidance is [{topic,indicator,correction}] and must be [] when no evidence is supplied."
        ),
    }
    raw, provider, model = generate_json(
        _lesson_system_prompt(), json.dumps(prompt, ensure_ascii=False), 7000, task="lesson-block",
    )
    original_lesson = _json_object(raw)
    lesson = _normalize_lesson(original_lesson)
    if not _valid_lesson(lesson):
        original_blocks = original_lesson.get("content_blocks")
        raw_block_summary = {
            "container_type": type(original_blocks).__name__,
            "count": len(original_blocks) if isinstance(original_blocks, (list, dict)) else None,
            "sample_keys": sorted(original_blocks[0].keys())[:12] if isinstance(original_blocks, list) and original_blocks and isinstance(original_blocks[0], dict) else sorted(original_blocks.keys())[:12] if isinstance(original_blocks, dict) else [],
            "sample_types": [item.get("type", item.get("kind")) for item in original_blocks[:5] if isinstance(item, dict)] if isinstance(original_blocks, list) else [],
        }
        logger.warning("ai_output_invalid task=lesson-block provider=%s model=%s issue=rich_content_schema top_keys=%s block_shapes=%s",
                       provider, model, sorted(lesson.keys()),
                       raw_block_summary)
        repair_prompt = {
            "required_shape": {
                "title": "string",
                "overview": "string",
                "content_blocks": [{"type": "text|code|table|steps|callout|complexity|diagram", "fields": "as defined in requirements"}],
                "key_takeaways": ["string"],
                "misconception_guidance": [{"topic": "string", "indicator": "string", "correction": "string"}],
            },
            "invalid_previous_output": original_lesson,
            "instruction": "Repair the content into valid JSON matching required_shape. Preserve useful details and requested code language. Do not invent diagnostic evidence.",
        }
        raw, provider, model = generate_json(
            "Repair rich lesson JSON to match the requested schema. Return JSON only.",
            json.dumps(repair_prompt, ensure_ascii=False), 6000, task="lesson-repair",
        )
        lesson = _normalize_lesson(_json_object(raw))
        if not _valid_lesson(lesson):
            logger.error("ai_output_invalid task=lesson-repair provider=%s model=%s issue=rich_content_schema", provider, model)
            raise HTTPException(status_code=502, detail="The model returned an incomplete lesson after retry. Check backend logs.")

    return {
        "skill_node_id": skill_node_id,
        "block_index": block_index,
        "lesson": lesson,
        "sources": sources,
        "misconception_indicators": misconceptions,
        "provider": provider,
        "model": model,
    }
