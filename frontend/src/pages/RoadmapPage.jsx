import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import Badge from "../components/Badge.jsx";
import LoadingState from "../components/LoadingState.jsx";
import ProfileSelector, { getStoredProfileId } from "../components/ProfileSelector.jsx";
import { getLearnerRoadmap } from "../services/api.js";

function percent(value, empty = "Not assessed") {
  return value === null || value === undefined ? empty : `${Math.round(value * 100)}%`;
}

function gap(value) {
  return value === null || value === undefined ? "Unknown" : `${Math.round(value * 100)} points`;
}

function priorityLabel(score) {
  if (score >= 0.6) return "HIGH";
  if (score >= 0.35) return "MEDIUM";
  return "LOW";
}

function reasonText(item) {
  return item.reasons?.length
    ? item.reasons.join(", ") + "."
    : "Recommended by Phase 4 because this skill has a visible learner-state gap.";
}

function RoadmapStep({ item, index, isNext, profileId }) {
  return (
    <article className={`roadmap-step ${isNext ? "roadmap-next" : ""}`}>
      <div className="roadmap-rank">{index + 1}</div>
      <div className="min-w-0 flex-1">
        {isNext ? <Badge tone="orange">Recommended Next</Badge> : null}
        <div className="mt-1 flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="text-base font-bold text-ink">{item.name}</h3>
            <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted">{item.competency_name} - {item.skill_node_id}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={item.action === "covered" ? "green" : item.action === "verify" ? "orange" : "blue"}>
              {item.action_label}
            </Badge>
            <Badge tone={item.target_type === "required" ? "blue" : "green"}>
              {item.target_type === "required" ? "Core DSA Topic" : "My Goal"}
            </Badge>
          </div>
        </div>

        <div className="mt-3 grid gap-x-4 gap-y-1 text-xs text-slate-700 sm:grid-cols-3">
          <span>Current: <strong>{percent(item.mastery)}</strong></span>
          <span>Target: <strong>{percent(item.target_mastery)}</strong></span>
          <span>Gap: <strong>{gap(item.gap)}</strong></span>
          <span>Priority: <strong>{priorityLabel(item.priority_score)}</strong></span>
          <span>Evidence: <strong>{item.evidence_status.replaceAll("_", " ")}</strong></span>
          <span>Prerequisites: <strong>{item.prerequisite_health.prerequisite_health.replaceAll("_", " ")}</strong></span>
          {item.action !== "covered" ? <span>Start: <strong>{item.available_now ? "Ready now" : "After earlier steps"}</strong></span> : null}
        </div>

        <div className="mt-3 rounded-lg bg-slate-50 p-2 text-xs leading-5 text-slate-700">
          <strong>Why?</strong>
          <p>{reasonText(item)}</p>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {item.action !== "covered" ? <Link to={`/learn/${encodeURIComponent(item.skill_node_id)}?profile_id=${encodeURIComponent(profileId)}`} className="inline-flex rounded-lg bg-indigo px-4 py-2 text-sm font-bold text-white">Learn this topic</Link> : null}
          <Link to={`/assessment/topic?skill_node_id=${encodeURIComponent(item.skill_node_id)}&profile_id=${encodeURIComponent(profileId)}`} className="inline-flex rounded-lg border border-indigo px-4 py-2 text-sm font-bold text-indigo">Assess this topic</Link>
        </div>
      </div>
    </article>
  );
}

function filterItems(roadmap, activeFilter) {
  if (activeFilter === "covered") return roadmap.already_covered || [];
  if (roadmap.learning_path) {
    if (activeFilter === "required") return roadmap.learning_path.filter((item) => item.target_type === "required");
    if (activeFilter === "desired") return roadmap.learning_path.filter((item) => item.target_type === "desired");
    return roadmap.learning_path;
  }
  const merged = [
    ...roadmap.immediate_next,
    ...roadmap.near_term,
    ...roadmap.later,
    ...roadmap.desired_goal_path
  ];
  const unique = Array.from(new Map(merged.map((item) => [item.skill_node_id, item])).values());
  if (activeFilter === "required") return unique.filter((item) => item.target_type === "required");
  if (activeFilter === "desired") return unique.filter((item) => item.target_type === "desired");
  return unique;
}

export default function RoadmapPage() {
  const [activeProfileId, setActiveProfileId] = useState(getStoredProfileId());
  const [activeFilter, setActiveFilter] = useState("all");
  const [roadmap, setRoadmap] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadRoadmap() {
      try {
        setError("");
        setRoadmap(null);
        setRoadmap(await getLearnerRoadmap(activeProfileId));
      } catch (err) {
        setError("Unable to load roadmap.");
      }
    }
    loadRoadmap();
  }, [activeProfileId]);

  const items = useMemo(() => roadmap ? filterItems(roadmap, activeFilter) : [], [roadmap, activeFilter]);
  const nextItem = roadmap?.immediate_next?.[0];

  if (error) {
    return <main className="mx-auto max-w-5xl px-6 py-8"><section className="section-card">{error}</section></main>;
  }
  if (!roadmap) return <LoadingState />;

  return (
    <main className="mx-auto max-w-7xl px-6 py-6">
      <section className="mb-4 rounded-lg border border-line bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-indigo">Phase 4 - Decision / Path</p>
            <h1 className="mt-2 text-3xl font-bold text-ink">Personalized DSA Roadmap</h1>
            <p className="mt-3 max-w-3xl text-slate-700">
              Build foundations before advanced topics. Learn, revise or verify each topic based on your diagnostic evidence.
            </p>
            {roadmap.assessment_source?.assessment_mode === "sample" ? <div className="mt-3"><Badge tone="orange">Demo Sample Diagnostic</Badge></div> : null}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ProfileSelector activeProfileId={activeProfileId} onChange={setActiveProfileId} />
            <Link to="/knowledge-graph" className="rounded-lg border border-indigo px-5 py-3 text-sm font-bold text-indigo">View Knowledge Graph</Link>
          </div>
        </div>
      </section>

      {nextItem ? (
        <section className="roadmap-hero">
          <p className="text-xs font-bold uppercase tracking-wide text-indigo">Recommended Next</p>
          <h2 className="mt-1 text-xl font-bold text-ink">{nextItem.name}</h2>
          <div className="mt-2"><Badge tone="blue">{nextItem.action_label}</Badge></div>
          <p className="mt-1 text-sm text-slate-700">
            Mastery: <strong>{percent(nextItem.mastery)}</strong> to Target: <strong>{percent(nextItem.target_mastery)}</strong>
            {" "} | Priority: <strong>{priorityLabel(nextItem.priority_score)}</strong>
          </p>
          <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-700">{reasonText(nextItem)}</p>
        </section>
      ) : null}

      <section className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white p-3 shadow-sm">
        <div className="flex rounded-lg border border-line bg-slate-50 p-1">
          {[
            ["all", "Learning Path"],
            ["required", "Core Topics"],
            ...(roadmap.desired_goal_path.length ? [["desired", "My Goals"]] : []),
            ["covered", `Already Covered (${roadmap.already_covered?.length || 0})`]
          ].map(([key, label]) => (
            <button
              className={`rounded-md px-4 py-2 text-sm font-bold ${activeFilter === key ? "bg-indigo text-white" : "text-slate-700"}`}
              key={key}
              type="button"
              onClick={() => setActiveFilter(key)}
            >
              {label}
            </button>
          ))}
        </div>
        <p className="text-sm text-slate-700">
          Concept order comes first. Priority chooses between eligible topics; uncertain knowledge gets a verification step.
        </p>
      </section>

      <section className="roadmap-path">
        <div className="roadmap-origin">{activeFilter === "covered" ? "Already Covered" : "Current State"}</div>
        {items.length ? (
          items.map((item, index) => (
            <RoadmapStep
              key={`${activeFilter}-${item.skill_node_id}`}
              item={item}
              index={item.path_order ? item.path_order - 1 : index}
              isNext={item.skill_node_id === nextItem?.skill_node_id}
              profileId={activeProfileId}
            />
          ))
        ) : (
          <div className="section-card">{activeFilter === "covered" ? "No topics have reached the target with sufficient evidence yet." : "No pending roadmap steps match this filter."}</div>
        )}
        <div className="roadmap-origin roadmap-goal">{activeFilter === "desired" ? "Personal Goals" : "Target Competency State"}</div>
      </section>
    </main>
  );
}
