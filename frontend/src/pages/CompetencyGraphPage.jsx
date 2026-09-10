import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Badge from "../components/Badge.jsx";
import LoadingState from "../components/LoadingState.jsx";
import ProfileSelector, { getStoredProfileId } from "../components/ProfileSelector.jsx";
import { getProfileTargetSkills } from "../services/api.js";

const difficultyLabels = {
  1: "Basic",
  2: "Intermediate",
  3: "Advanced"
};

function SkillNodeItem({ skill }) {
  return (
    <li className="rounded-lg border border-line bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-ink">{skill.name}</p>
          <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted">{skill.skill_node_id}</p>
        </div>
        <Badge tone={skill.difficulty_level === 3 ? "orange" : "gray"}>
          {difficultyLabels[skill.difficulty_level]}
        </Badge>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{skill.description}</p>
      <div className="mt-3 grid gap-2 text-xs text-muted">
        <span>
          Prerequisites:{" "}
          <strong className="text-ink">
            {skill.prerequisites.length ? skill.prerequisites.join(", ") : "None"}
          </strong>
        </span>
        <span>
          Unlocks:{" "}
          <strong className="text-ink">
            {skill.next_skills.length ? skill.next_skills.join(", ") : "None"}
          </strong>
        </span>
      </div>
    </li>
  );
}

function CompetencyGroup({ group, type }) {
  return (
    <article className="rounded-lg border border-line bg-slate-50 p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold text-ink">{group.competency_name}</h3>
          <p className="mt-1 text-sm font-semibold uppercase tracking-wide text-muted">{group.competency_id}</p>
        </div>
        <Badge tone={type === "required" ? "blue" : "orange"}>
          {type === "required" ? "Required for Role" : "Personal Development Goal"}
        </Badge>
      </div>
      <p className="mb-4 text-sm text-slate-700">
        Target level: <strong>{group.target_label || group.target_level}</strong>
      </p>
      <ul className="space-y-3">
        {group.skill_nodes.map((skill) => (
          <SkillNodeItem key={skill.skill_node_id} skill={skill} />
        ))}
      </ul>
    </article>
  );
}

export default function CompetencyGraphPage() {
  const [targetSkills, setTargetSkills] = useState(null);
  const [activeProfileId, setActiveProfileId] = useState(getStoredProfileId());
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadTargetSkills() {
      try {
        setTargetSkills(null);
        setTargetSkills(await getProfileTargetSkills(activeProfileId));
      } catch (err) {
        setError("Unable to load competency graph data from the backend.");
      }
    }

    loadTargetSkills();
  }, [activeProfileId]);

  if (error) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-6">
        <section className="section-card max-w-xl">
          <h1 className="text-2xl font-bold text-ink">Competency graph unavailable</h1>
          <p className="mt-3 text-slate-700">{error}</p>
        </section>
      </main>
    );
  }

  if (!targetSkills) {
    return <LoadingState />;
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <section className="mb-6 rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-indigo">Phase 2</p>
            <h1 className="mt-2 text-3xl font-bold text-ink">Competency Graph and Skill Decomposition</h1>
            <p className="mt-3 max-w-3xl text-base leading-7 text-slate-700">
              Required and desired competency targets are expanded into assessable skill nodes. These nodes and
              prerequisites will become the input for the diagnostic assessment module in the next phase.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ProfileSelector activeProfileId={activeProfileId} onChange={setActiveProfileId} />
            <Link to="/profile" className="rounded-lg border border-indigo px-5 py-3 text-sm font-bold text-indigo">
              Back to Profile
            </Link>
          </div>
        </div>
      </section>

      <section className="mb-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-muted">Derived from role and activities</p>
            <h2 className="mt-1 text-2xl font-bold text-ink">Required Competencies</h2>
          </div>
          <Badge tone="blue">{targetSkills.required.length} competency target(s)</Badge>
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          {targetSkills.required.map((group) => (
            <CompetencyGroup key={group.competency_id} group={group} type="required" />
          ))}
        </div>
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-muted">Chosen by prototype profile</p>
            <h2 className="mt-1 text-2xl font-bold text-ink">Desired Competencies</h2>
          </div>
          <Badge tone="orange">{targetSkills.desired.length} competency target(s)</Badge>
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          {targetSkills.desired.map((group) => (
            <CompetencyGroup key={group.competency_id} group={group} type="desired" />
          ))}
        </div>
      </section>
    </main>
  );
}
