import pytest

from app.seed.dsa_curriculum import DSA_COMPETENCIES, DSA_PREREQUISITES, DSA_PROFILE_ID, DSA_SKILLS, DSA_STUDY_ORDER
from app.services.roadmap_service import build_roadmap


def learner_graph(overrides=None):
    overrides = overrides or {}
    competencies = []
    for competency_id, name, _ in DSA_COMPETENCIES:
        skills = []
        for skill_id, parent_id, skill_name, _, _ in DSA_SKILLS:
            if parent_id != competency_id:
                continue
            skill = {
                "skill_node_id": skill_id,
                "competency_id": competency_id,
                "name": skill_name,
                "mastery": 0.85,
                "target_mastery": 0.75,
                "target_type": "required",
                "evidence_status": "sufficient_mastery",
                "attempts": 4,
                "effective_attempts": 4.0,
                "guessing_attempts": 0,
                "misconceptions": [],
                "prerequisites": [parent for child, parent in DSA_PREREQUISITES if child == skill_id],
                "study_predecessors": [parent for child, parent in DSA_STUDY_ORDER if child == skill_id],
            }
            skill.update(overrides.get(skill_id, {}))
            skill["gap"] = None if skill["mastery"] is None else max(0.0, skill["target_mastery"] - skill["mastery"])
            skills.append(skill)
        competencies.append({"competency_id": competency_id, "name": name, "skills": skills})
    return {"profile_id": DSA_PROFILE_ID, "assessment_source": {}, "competencies": competencies}


def test_user_example_builds_foundations_before_trees_and_skips_covered_searching():
    roadmap = build_roadmap(learner_graph({
        "DSA-COMPLEXITY": {"mastery": 0.65},
        "DSA-SEARCH-SORT": {"mastery": 0.75},
        "DSA-LINKED": {"mastery": 0.60},
        "DSA-TREES": {"mastery": 0.12, "evidence_status": "weak"},
    }))
    path = roadmap["learning_path"]
    assert [item["skill_node_id"] for item in path] == ["DSA-COMPLEXITY", "DSA-LINKED", "DSA-TREES"]
    assert [item["action"] for item in path] == ["review", "review", "learn"]
    assert roadmap["immediate_next"][0]["skill_node_id"] == "DSA-COMPLEXITY"
    assert path[0]["gap"] < path[-1]["gap"]
    assert not path[-1]["available_now"]
    assert any(item["skill_node_id"] == "DSA-SEARCH-SORT" for item in roadmap["already_covered"])


def test_dependency_order_holds_for_all_unassessed_topics_and_full_path_is_returned():
    overrides = {skill_id: {"mastery": None, "evidence_status": "not_assessed", "attempts": 0, "effective_attempts": 0} for skill_id, *_ in DSA_SKILLS}
    roadmap = build_roadmap(learner_graph(overrides))
    assert len(roadmap["learning_path"]) == 10
    positions = {item["skill_node_id"]: index for index, item in enumerate(roadmap["learning_path"])}
    for child, parent in DSA_PREREQUISITES + DSA_STUDY_ORDER:
        assert positions[parent] < positions[child]
    assert all(item["action"] == "verify" for item in roadmap["learning_path"])
    assert roadmap["immediate_next"][0]["skill_node_id"] == "DSA-COMPLEXITY"
    assert len(roadmap["immediate_next"] + roadmap["near_term"] + roadmap["later"]) == 10


def test_uncertain_high_mastery_requires_verification_before_dependent_learning():
    roadmap = build_roadmap(learner_graph({
        "DSA-RECURSION": {"mastery": 0.90, "evidence_status": "uncertain"},
        "DSA-TREES": {"mastery": 0.12, "evidence_status": "weak"},
    }))
    items = {item["skill_node_id"]: item for item in roadmap["all_candidates"]}
    assert items["DSA-RECURSION"]["action"] == "verify"
    assert items["DSA-TREES"]["blocked_by"] == ["DSA-RECURSION"]
    assert items["DSA-TREES"]["prerequisite_health"]["prerequisite_health"] == "verification_required"
    assert roadmap["immediate_next"][0]["skill_node_id"] == "DSA-RECURSION"


def test_transitive_prerequisite_gap_blocks_advanced_topic_despite_ready_direct_parent():
    roadmap = build_roadmap(learner_graph({
        "DSA-ARRAYS": {"mastery": 0.20, "evidence_status": "weak"},
        "DSA-GRAPHS": {"mastery": 0.12, "evidence_status": "weak"},
    }))
    graph_step = next(item for item in roadmap["all_candidates"] if item["skill_node_id"] == "DSA-GRAPHS")
    assert "DSA-ARRAYS" in graph_step["blocked_by"]
    assert graph_step["state"] == "blocked_by_prerequisite"
    assert roadmap["immediate_next"][0]["skill_node_id"] == "DSA-ARRAYS"


def test_suggested_order_does_not_become_a_hard_readiness_requirement():
    roadmap = build_roadmap(learner_graph({
        "DSA-LINKED": {"mastery": 0.60},
        "DSA-TREES": {"mastery": 0.12, "evidence_status": "weak"},
    }))
    tree_step = next(item for item in roadmap["all_candidates"] if item["skill_node_id"] == "DSA-TREES")
    assert tree_step["prerequisite_health"]["prerequisite_health"] == "ready"
    assert "DSA-LINKED" in tree_step["scheduled_after"]
    assert "DSA-LINKED" not in tree_step["blocked_by"]
    assert roadmap["learning_path"][0]["skill_node_id"] == "DSA-LINKED"


def test_advanced_weakness_increases_foundation_priority_and_explains_why():
    stronger = build_roadmap(learner_graph({"DSA-COMPLEXITY": {"mastery": 0.65}, "DSA-TREES": {"mastery": 0.65}}))
    weaker = build_roadmap(learner_graph({"DSA-COMPLEXITY": {"mastery": 0.65}, "DSA-TREES": {"mastery": 0.12, "evidence_status": "weak"}}))
    first = next(item for item in stronger["all_candidates"] if item["skill_node_id"] == "DSA-COMPLEXITY")
    second = next(item for item in weaker["all_candidates"] if item["skill_node_id"] == "DSA-COMPLEXITY")
    assert second["foundation_boost"] > first["foundation_boost"]
    assert second["priority_score"] > first["priority_score"]
    assert any("Trees and Heaps" in reason for reason in second["reasons"])


def test_priority_selects_between_independent_eligible_topics():
    roadmap = build_roadmap(learner_graph({
        "DSA-HASHING": {"mastery": 0.10, "evidence_status": "weak"},
        "DSA-STACKS": {"mastery": 0.40, "evidence_status": "weak"},
    }))
    assert [item["skill_node_id"] for item in roadmap["learning_path"]] == ["DSA-HASHING", "DSA-STACKS"]


def test_fully_covered_curriculum_requires_no_repeat_lessons():
    roadmap = build_roadmap(learner_graph())
    assert roadmap["learning_path"] == roadmap["immediate_next"] == roadmap["near_term"] == roadmap["later"] == []
    assert len(roadmap["already_covered"]) == 10


def test_guessing_only_evidence_never_establishes_readiness():
    roadmap = build_roadmap(learner_graph({
        "DSA-RECURSION": {"mastery": 0.80, "effective_attempts": 0, "guessing_attempts": 4},
        "DSA-TREES": {"mastery": 0.12, "evidence_status": "weak"},
    }))
    items = {item["skill_node_id"]: item for item in roadmap["all_candidates"]}
    assert items["DSA-RECURSION"]["action"] == "verify"
    assert "DSA-RECURSION" in items["DSA-TREES"]["blocked_by"]


def test_missing_prerequisite_never_makes_topic_ready():
    roadmap = build_roadmap(learner_graph({"DSA-TREES": {"mastery": 0.12, "evidence_status": "weak", "prerequisites": ["MISSING"]}}))
    assert roadmap["immediate_next"] == []
    assert roadmap["learning_path"][0]["blocked_by"] == ["MISSING"]


def test_dependency_cycles_are_reported():
    with pytest.raises(ValueError, match="dependency cycle"):
        build_roadmap(learner_graph({"DSA-COMPLEXITY": {"prerequisites": ["DSA-TREES"]}}))
