READINESS_MASTERY = 0.65
REVIEW_MASTERY = 0.55
ACTION_LABELS = {
    "learn": "Learn",
    "review": "Brief revision",
    "verify": "Verify knowledge",
    "covered": "Already covered",
}
PRIORITY_WEIGHTS = {
    "gap": 0.35,
    "role_requirement": 0.25,
    "prerequisite_impact": 0.20,
    "evidence_confidence": 0.10,
    "misconception": 0.10,
}


def _learning_action(skill):
    mastery = skill["mastery"]
    reliable = skill["evidence_status"] == "sufficient_mastery"
    if mastery is None or skill["evidence_status"] not in {"sufficient_mastery", "weak"}:
        return "verify"
    if skill.get("effective_attempts", skill["attempts"]) < 2:
        return "verify"
    if reliable and mastery >= skill["target_mastery"]:
        return "covered"
    return "review" if mastery >= REVIEW_MASTERY else "learn"


def _ancestors(skill_id, parents, visiting=None, cache=None):
    visiting = set() if visiting is None else visiting
    cache = {} if cache is None else cache
    if skill_id in visiting:
        raise ValueError("The learning curriculum contains a dependency cycle")
    if skill_id in cache:
        return cache[skill_id]
    ancestors = set(parents.get(skill_id, []))
    for parent_id in parents.get(skill_id, []):
        ancestors.update(_ancestors(parent_id, parents, visiting | {skill_id}, cache))
    cache[skill_id] = ancestors
    return ancestors


def prerequisite_health(skill_id, prerequisites, skills_by_id):
    prerequisite_ids = sorted(_ancestors(skill_id, prerequisites))
    weak = []
    unassessed = []
    uncertain = []
    ready = []
    for prerequisite_id in prerequisite_ids:
        prerequisite = skills_by_id.get(prerequisite_id)
        if not prerequisite or prerequisite["mastery"] is None:
            unassessed.append(prerequisite_id)
        elif prerequisite["evidence_status"] == "weak" and prerequisite.get("effective_attempts", prerequisite["attempts"]) >= 2:
            weak.append(prerequisite_id)
        elif prerequisite["evidence_status"] != "sufficient_mastery" or prerequisite.get("effective_attempts", prerequisite["attempts"]) < 2:
            uncertain.append(prerequisite_id)
        elif prerequisite["mastery"] < READINESS_MASTERY:
            weak.append(prerequisite_id)
        else:
            ready.append(prerequisite_id)
    health = "weak" if weak else "verification_required" if uncertain else "unassessed" if unassessed else "ready"
    return {
        "prerequisite_count": len(prerequisite_ids),
        "mastered_prerequisite_count": len(ready),
        "weak_prerequisite_count": len(weak),
        "unassessed_prerequisite_count": len(unassessed),
        "uncertain_prerequisite_count": len(uncertain),
        "weak_prerequisites": weak,
        "unassessed_prerequisites": unassessed,
        "uncertain_prerequisites": uncertain,
        "prerequisite_health": health,
    }


def _ordered_candidates(candidates, parents):
    remaining = {item["skill_node_id"]: item for item in candidates}
    ordered = []
    while remaining:
        eligible = [
            item for skill_id, item in remaining.items()
            if not any(parent_id in remaining for parent_id in parents.get(skill_id, []))
        ]
        if not eligible:
            raise ValueError("The learning curriculum contains a dependency cycle")
        selected = min(eligible, key=lambda item: (-item["priority_score"], item["skill_node_id"]))
        ordered.append(selected)
        remaining.pop(selected["skill_node_id"])
    return ordered


def build_roadmap(graph):
    skills = [skill for competency in graph["competencies"] for skill in competency["skills"]]
    skills_by_id = {skill["skill_node_id"]: skill for skill in skills}
    competency_names = {competency["competency_id"]: competency["name"] for competency in graph["competencies"]}
    prerequisites = {skill_id: skill["prerequisites"] for skill_id, skill in skills_by_id.items()}
    study_order = {skill_id: skill.get("study_predecessors", []) for skill_id, skill in skills_by_id.items()}
    parents = {skill_id: sorted(set(prerequisites[skill_id] + study_order[skill_id])) for skill_id in skills_by_id}
    ancestors = {skill_id: _ancestors(skill_id, parents) for skill_id in skills_by_id}
    actions = {skill_id: _learning_action(skill) for skill_id, skill in skills_by_id.items()}
    gaps = {skill_id: 0.35 if skill["gap"] is None else min(1.0, max(0.0, skill["gap"])) for skill_id, skill in skills_by_id.items()}
    candidates = []

    for skill_id, skill in skills_by_id.items():
        action = actions[skill_id]
        health = prerequisite_health(skill_id, prerequisites, skills_by_id)
        blocked_by = sorted(set(health["weak_prerequisites"] + health["unassessed_prerequisites"] + health["uncertain_prerequisites"]))
        downstream = [
            dependent_id for dependent_id in skills_by_id
            if skill_id in ancestors[dependent_id] and actions[dependent_id] != "covered"
        ]
        downstream.sort(key=lambda dependent_id: (-gaps[dependent_id], dependent_id))
        foundation_boost = 0.2 * max((gaps[dependent_id] for dependent_id in downstream), default=0.0) * min(1.0, len(downstream) / 3)
        priority = (
            PRIORITY_WEIGHTS["gap"] * gaps[skill_id]
            + PRIORITY_WEIGHTS["role_requirement"] * (1.0 if skill["target_type"] == "required" else 0.6)
            + PRIORITY_WEIGHTS["prerequisite_impact"] * min(1.0, len(downstream) / 3)
            + PRIORITY_WEIGHTS["evidence_confidence"] * (1.0 if action == "verify" else 0.25)
            + PRIORITY_WEIGHTS["misconception"] * min(1.0, len(skill["misconceptions"]) / 2)
            + foundation_boost
        )
        if action == "covered":
            priority = 0.0
            foundation_boost = 0.0
        pending_before = sorted(parent_id for parent_id in parents[skill_id] if actions.get(parent_id) != "covered")
        available_now = action != "covered" and not blocked_by and not pending_before
        state = "mastered" if action == "covered" else "blocked_by_prerequisite" if blocked_by else "needs_more_evidence" if action == "verify" else "learning_priority"
        reasons = []
        if action == "covered":
            reasons.append("Target reached with sufficient evidence; no repeat lesson needed")
        elif action == "verify":
            reasons.append("Take a short knowledge check before deciding whether revision or learning is needed")
        elif action == "review":
            reasons.append("Revise the remaining gaps rather than repeat the entire topic")
        else:
            reasons.append("Build understanding with guided examples and focused practice")
        if skill["gap"] is not None and action != "covered":
            reasons.append(f"Mastery gap: {round(skill['gap'] * 100)} percentage points")
        if downstream and action != "covered":
            names = ", ".join(skills_by_id[dependent_id]["name"] for dependent_id in downstream[:3])
            reasons.append(f"Foundation for upcoming topics: {names}")
        if blocked_by and action != "covered":
            names = ", ".join(skills_by_id[parent_id]["name"] if parent_id in skills_by_id else parent_id for parent_id in blocked_by)
            reasons.append(f"Resolve prerequisite learning or verification first: {names}")
        if study_order[skill_id] and action != "covered":
            names = ", ".join(skills_by_id[parent_id]["name"] if parent_id in skills_by_id else parent_id for parent_id in study_order[skill_id])
            reasons.append(f"Suggested study order: after {names}")
        if skill.get("guessing_attempts", 0):
            reasons.append("Guessing responses do not establish prerequisite readiness")
        if skill["misconceptions"] and action != "covered":
            reasons.append("Potential misconception signal: " + ", ".join(skill["misconceptions"][:2]))
        candidates.append({
            "skill_node_id": skill_id,
            "name": skill["name"],
            "competency_id": skill["competency_id"],
            "competency_name": competency_names[skill["competency_id"]],
            "target_type": skill["target_type"],
            "state": state,
            "action": action,
            "action_label": ACTION_LABELS[action],
            "available_now": available_now,
            "blocked_by": blocked_by,
            "scheduled_after": pending_before,
            "prerequisites": prerequisites[skill_id],
            "study_predecessors": study_order[skill_id],
            "unlocks": downstream,
            "foundation_boost": round(foundation_boost, 4),
            "priority_score": round(min(1.0, priority), 4),
            "mastery": skill["mastery"],
            "target_mastery": skill["target_mastery"],
            "gap": skill["gap"],
            "evidence_status": skill["evidence_status"],
            "prerequisite_health": health,
            "reasons": reasons,
        })

    ordered = _ordered_candidates(candidates, parents)
    learning_path = [item for item in ordered if item["action"] != "covered"]
    for index, item in enumerate(learning_path):
        item["path_order"] = index + 1
    immediate = next((item for item in learning_path if item["available_now"]), None)
    return {
        "profile_id": graph["profile_id"],
        "source": "prerequisite_aware_learning_path",
        "assessment_source": graph["assessment_source"],
        "priority_weights": PRIORITY_WEIGHTS,
        "readiness_mastery": READINESS_MASTERY,
        "learning_path": learning_path,
        "already_covered": [item for item in ordered if item["action"] == "covered"],
        "immediate_next": [immediate] if immediate else [],
        "near_term": [item for item in learning_path[:4] if item is not immediate],
        "later": learning_path[4:],
        "desired_goal_path": [item for item in learning_path if item["target_type"] == "desired"],
        "all_candidates": ordered,
    }
