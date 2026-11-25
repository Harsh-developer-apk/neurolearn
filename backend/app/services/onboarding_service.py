import base64
import binascii
import io
import json
import logging
import re
import zipfile
from uuid import uuid4
from xml.etree import ElementTree

from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models import Activity, Profile, ProfileActivity, SyllabusDocument
from app.seed.dsa_curriculum import DSA_COMPETENCIES, DSA_SKILLS, DSA_SUBJECT
from app.services.ai_provider import extract_syllabus_image


logger = logging.getLogger("neurolearn.ai")
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARS = 100_000
MAX_PDF_PAGES = 50

TOPIC_TERMS = {
    "DSA-COMPLEXITY": ["complexity", "big o", "big-o", "asymptotic", "time analysis", "space analysis", "amortized"],
    "DSA-ARRAYS": ["array", "arrays", "string", "strings", "prefix sum", "two pointer", "sliding window"],
    "DSA-LINKED": ["linked list", "singly linked", "doubly linked", "circular list"],
    "DSA-STACKS": ["stack", "stacks", "queue", "queues", "deque", "lifo", "fifo"],
    "DSA-HASHING": ["hashing", "hash table", "hash map", "hashmap", "hash set", "collision", "dictionary"],
    "DSA-SEARCH-SORT": ["searching", "sorting", "binary search", "quick sort", "merge sort", "selection sort", "partition"],
    "DSA-TREES": ["tree", "trees", "binary search tree", "bst", "heap", "heaps", "priority queue"],
    "DSA-GRAPHS": ["graph", "graphs", "bfs", "dfs", "shortest path", "topological", "spanning tree"],
    "DSA-RECURSION": ["recursion", "recursive", "backtracking", "base case", "call stack"],
    "DSA-GREEDY-DP": ["dynamic programming", "memoization", "tabulation", "greedy", "optimal substructure", "overlapping subproblems"],
}


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_EXTRACTED_CHARS]


def _extract_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(entry.file_size for entry in entries) > 20 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="This document expands beyond the supported size limit.")
            document = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise HTTPException(status_code=422, detail="The Word document could not be read. Try saving it as DOCX or PDF.") from exc
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in document.findall(".//w:p", namespace):
        value = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
        if value.strip():
            paragraphs.append(value)
    return "\n".join(paragraphs)


def _topic_matches(text: str) -> list[dict]:
    normalized = re.sub(r"\s+", " ", text.casefold())
    matches = []
    for skill_id, _, name, description, _ in DSA_SKILLS:
        terms = TOPIC_TERMS.get(skill_id, [])
        found = [term for term in terms if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", normalized)]
        if found:
            matches.append({
                "skill_node_id": skill_id,
                "name": name,
                "description": description,
                "matched_terms": found,
                "included_by_default": True,
            })
    return matches


def preview_syllabus(payload) -> dict:
    pasted = (payload.pasted_text or "").strip()
    if len(pasted) > MAX_EXTRACTED_CHARS:
        raise HTTPException(status_code=413, detail="Pasted syllabus text must be 100,000 characters or fewer.")
    extracted = pasted
    filename = (payload.filename or "").strip()
    content_type = "text/plain" if pasted else (payload.content_type or "application/octet-stream")
    ocr_provider = None
    ocr_model = None

    if payload.file_base64:
        if pasted:
            raise HTTPException(status_code=422, detail="Upload a file or paste syllabus text, then preview it.")
        try:
            data = base64.b64decode(payload.file_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=422, detail="The uploaded file could not be decoded.") from exc
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Syllabus files must be 10 MB or smaller.")
        suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if suffix == "txt":
            try:
                extracted = data.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=422, detail="Text files must use UTF-8 encoding.") from exc
            content_type = "text/plain"
        elif suffix == "pdf":
            try:
                reader = PdfReader(io.BytesIO(data))
                if len(reader.pages) > MAX_PDF_PAGES:
                    raise HTTPException(status_code=413, detail="Syllabus PDFs are limited to 50 pages.")
                extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=422, detail="The PDF could not be read. Try a text based PDF or paste the syllabus.") from exc
            content_type = "application/pdf"
        elif suffix == "docx":
            extracted = _extract_docx(data)
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif suffix in {"png", "jpg", "jpeg"}:
            content_type = "image/png" if suffix == "png" else "image/jpeg"
            try:
                extracted, ocr_provider, ocr_model = extract_syllabus_image(data, content_type)
            except RuntimeError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=415, detail="Use one PDF, DOCX, TXT, PNG, JPG, or JPEG syllabus file.")

    extracted = _clean_text(extracted)
    if len(extracted) < 20:
        raise HTTPException(status_code=422, detail="We couldn't find enough readable syllabus text. Try a clearer file or paste the text.")
    matches = _topic_matches(extracted)
    return {
        "filename": filename or "Pasted syllabus",
        "content_type": content_type,
        "extracted_text": extracted,
        "extracted_characters": len(extracted),
        "topics": matches,
        "all_topics": [
            {"skill_node_id": skill_id, "name": name, "description": description, "matched_terms": next((item["matched_terms"] for item in matches if item["skill_node_id"] == skill_id), []), "included_by_default": any(item["skill_node_id"] == skill_id for item in matches)}
            for skill_id, _, name, description, _ in DSA_SKILLS
        ],
        "ocr_provider": ocr_provider,
        "ocr_model": ocr_model,
        "file_limit_bytes": MAX_FILE_BYTES,
        "text_limit_characters": MAX_EXTRACTED_CHARS,
    }


def create_learner(db: Session, payload) -> dict:
    profile_id = f"LEARNER-{uuid4().hex[:12].upper()}"
    profile = Profile(
        id=profile_id,
        full_name=payload.full_name.strip(),
        preferred_language=payload.preferred_language.strip(),
        age=payload.age,
        course_or_class=payload.course_or_class.strip(),
        subject_id=payload.subject_id,
        learning_goal=payload.learning_goal,
        goal_details=payload.goal_details.strip() or None,
    )
    db.add(profile)
    db.flush()

    for competency_id, _, _ in DSA_COMPETENCIES:
        activity_id = competency_id.replace("COMP-", "ACT-")
        if db.query(Activity).filter(Activity.activity_id == activity_id).first():
            db.add(ProfileActivity(profile_id=profile_id, activity_id=activity_id))

    document = None
    if payload.learning_goal == "exam" and payload.syllabus_text.strip():
        valid_ids = {item[0] for item in DSA_SKILLS}
        suggested_ids = [skill_id for skill_id in payload.suggested_skill_ids if skill_id in valid_ids]
        included_ids = [skill_id for skill_id in payload.included_skill_ids if skill_id in valid_ids]
        if not included_ids:
            included_ids = suggested_ids or list(valid_ids)
        document = SyllabusDocument(
            syllabus_id=f"SYLLABUS-{uuid4().hex[:12].upper()}",
            profile_id=profile_id,
            filename=(payload.syllabus_filename or "Pasted syllabus")[:255],
            content_type=(payload.syllabus_content_type or "text/plain")[:100],
            extracted_text=_clean_text(payload.syllabus_text),
            suggested_skill_ids=json.dumps(suggested_ids),
            included_skill_ids=json.dumps(list(dict.fromkeys(included_ids))),
        )
        db.add(document)

    db.commit()
    db.refresh(profile)
    logger.info("learner_onboarded profile_id=%s subject=%s goal=%s syllabus_saved=%s", profile_id, payload.subject_id, payload.learning_goal, bool(document))
    return {
        "profile_id": profile_id,
        "full_name": profile.full_name,
        "subject": DSA_SUBJECT,
        "learning_goal": profile.learning_goal,
        "syllabus_saved": bool(document),
        "included_skill_ids": json.loads(document.included_skill_ids) if document else [],
    }
