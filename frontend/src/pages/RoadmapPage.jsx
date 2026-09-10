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

function RoadmapStep({ item, index, isNext }) {
  return (
    <article className={`roadmap-step ${isNext ? "roadmap-next" : ""}`}>
      <div className="roadmap-rank">{index + 1}</div>
      <div className="min-w-0 flex-1">
        {isNext ? <Badge tone="orange">Next Learning Step</Badge> : null}
        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-xl font-bold text-ink">{item.name}</h3>
            <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted">{item.competency_name} - {item.skill_node_id}</p>
          </div>
          <Badge tone={item.target_type === "required" ? "blue" : "green"}>
            {item.target_type === "required" ? "Required for Role" : "My Goal"}
          </Badge>
        </div>

        <div className="mt-4 grid gap-3 text-sm text-slate-700 sm:grid-cols-3">
          <span>Current: <strong>{percent(item.mastery)}</strong></span>
          <span>Target: <strong>{percent(item.target_mastery)}</strong></span>
          <span>Gap: <strong>{gap(item.gap)}</strong></span>
          <span>Priority: <strong>{priorityLabel(item.priority_score)}</strong></span>
          <span>Evidence: <strong>{item.evidence_status.replaceAll("_", " ")}</strong></span>
          <span>Prerequisites: <strong>{item.prerequisite_health.prerequisite_health.replaceAll("_", " ")}</strong></span>
        </div>

        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-700">
          <strong>Why?</strong>
          <p>{reasonText(item)}</p>
        </div>
      </div>
    </article>
  );
}

function filterItems(roadmap, activeFilter) {
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
    <main className="mx-auto max-w-7xl px-6 py-8">
      <section className="mb-6 rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-indigo">Phase 4 - Decision / Path</p>
            <h1 className="mt-2 text-3xl font-bold text-ink">Personalized Roadmap</h1>
            <p className="mt-3 max-w-3xl text-slate-700">
              Your personalized path from current capability to required and desired competency targets.
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
          <h2 className="mt-2 text-2xl font-bold text-ink">{nextItem.name}</h2>
          <p className="mt-2 text-slate-700">
            Mastery: <strong>{percent(nextItem.mastery)}</strong> to Target: <strong>{percent(nextItem.target_mastery)}</strong>
            {" "} | Priority: <strong>{priorityLabel(nextItem.priority_score)}</strong>
          </p>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">{reasonText(nextItem)}</p>
        </section>
      ) : null}

      <section className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white p-4 shadow-sm">
        <div className="flex rounded-lg border border-line bg-slate-50 p-1">
          {[
            ["all", "All"],
            ["required", "Required for Role"],
            ["desired", "My Goals"]
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
          Priority model: gap, role requirement, prerequisite impact, evidence confidence and misconception signals.
        </p>
      </section>

      <section className="roadmap-path">
        <div className="roadmap-origin">Current State</div>
        {items.length ? (
          items.map((item, index) => (
            <RoadmapStep
              key={`${activeFilter}-${item.skill_node_id}`}
              item={item}
              index={index}
              isNext={item.skill_node_id === nextItem?.skill_node_id}
            />
          ))
        ) : (
          <div className="section-card">No roadmap items match this filter.</div>
        )}
        <div className="roadmap-origin roadmap-goal">{activeFilter === "desired" ? "Personal Goals" : "Target Competency State"}</div>
      </section>
    </main>
  );
}
