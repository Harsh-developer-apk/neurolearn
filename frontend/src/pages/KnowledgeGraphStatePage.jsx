import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Background, Controls, Handle, Position, ReactFlow, useReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import Badge from "../components/Badge.jsx";
import LoadingState from "../components/LoadingState.jsx";
import ProfileSelector, { getStoredProfileId } from "../components/ProfileSelector.jsx";
import { getLearnerKnowledgeGraph } from "../services/api.js";

function percent(value, empty = "Not assessed") {
  return value === null || value === undefined ? empty : `${Math.round(value * 100)}%`;
}

function seconds(ms) {
  return ms === null || ms === undefined ? "Not assessed" : `${(ms / 1000).toFixed(1)} sec`;
}

function profileDomain(profileId) {
  return "Data Structures and Algorithms";
}

function competencyEvidenceStatus(competency) {
  if (!competency.evidence_coverage?.assessed_skills) return "not_assessed";
  if (competency.observed_mastery === null || competency.observed_mastery === undefined) return "not_assessed";
  if (!competency.skills.some((skill) => (skill.effective_attempts ?? skill.attempts) >= 2 && ["weak", "sufficient_mastery"].includes(skill.evidence_status))) return "uncertain";
  if ((competency.gap ?? 0) >= 0.3) return "weak";
  if (competency.evidence_coverage.assessed_skills < competency.evidence_coverage.total_skills) return "uncertain";
  return "sufficient_mastery";
}

function stateFor(item) {
  const mastery = item.kind === "competency" ? item.observed_mastery : item.mastery;
  const evidenceStatus = item.evidence_status;
  if (item.target_type === "desired" && mastery === null) return "desired";
  if (mastery === null || evidenceStatus === "not_assessed") return "not-assessed";
  if (evidenceStatus === "weak" || (item.gap ?? 0) >= 0.3) return "weak";
  if (evidenceStatus === "uncertain" || evidenceStatus === "gathering_evidence" || evidenceStatus === "early") return "uncertain";
  return "strong";
}

const stateLabels = {
  strong: "Strong / On Track",
  weak: "Needs Improvement",
  uncertain: "Uncertain",
  "not-assessed": "Not Assessed",
  desired: "Desired Goal"
};

function DomainNode({ data }) {
  return (
    <button className={`kg-topic-node kg-root-node ${data.selected ? "kg-selected-node" : ""}`} type="button">
      <Handle type="source" position={Position.Right} />
      <span>{data.label}</span>
    </button>
  );
}

function TopicNode({ data }) {
  return (
    <button className={`kg-topic-node kg-topic-${data.state} ${data.targetType === "desired" ? "kg-topic-desired" : ""} ${data.selected ? "kg-selected-node" : ""} ${data.highlighted ? "kg-path-node" : ""}`} type="button">
      <Handle type="target" position={Position.Left} />
      <Handle type="target" position={Position.Top} />
      <span>{data.label}</span>
      <Handle type="source" position={Position.Right} />
      <Handle type="source" position={Position.Bottom} />
    </button>
  );
}

const nodeTypes = {
  domain: DomainNode,
  topic: TopicNode
};

function buildItems(graph) {
  const competencies = [];
  const skills = [];

  for (const competency of graph.competencies || []) {
    const competencyItem = {
      ...competency,
      id: `competency:${competency.competency_id}:${competency.target_type}`,
      kind: "competency",
      label: competency.name,
      evidence_status: competencyEvidenceStatus(competency),
      required: competency.target_type === "required",
      prerequisites: [],
      dependents: [],
      attempts: competency.skills.reduce((sum, skill) => sum + (skill.attempts || 0), 0),
      correct_attempts: competency.skills.reduce((sum, skill) => sum + (skill.correct_attempts || 0), 0),
      accuracy: null,
      confidence: null,
      avg_response_time: null,
      misconceptions: []
    };
    competencies.push(competencyItem);

    for (const skill of competency.skills || []) {
      skills.push({
        ...skill,
        id: `skill:${skill.skill_node_id}:${skill.target_type}`,
        kind: "skill",
        label: skill.name,
        parentCompetencyId: competencyItem.id,
        parentCompetencyName: competency.name
      });
    }
  }

  return {
    competencies,
    skills,
    itemById: new Map([...competencies, ...skills].map((item) => [item.id, item])),
    skillBySkillId: new Map(skills.map((skill) => [skill.skill_node_id, skill]))
  };
}

function defaultSelectedId(items) {
  const weakSkill = items.skills.find((skill) => skill.target_type === "required" && stateFor(skill) === "weak");
  const strongSkill = items.skills.find((skill) => skill.target_type === "required" && stateFor(skill) === "strong");
  return (weakSkill || strongSkill || items.skills[0] || items.competencies[0])?.id || "profile-root";
}

function pathToRoot(selected, items) {
  const path = new Set(["profile-root"]);
  if (!selected || selected.kind === "profile") return path;
  path.add(selected.id);
  if (selected.kind === "skill") path.add(selected.parentCompetencyId);
  return path;
}

function buildFullFlow(graph, selectedId) {
  const items = buildItems(graph);
  const selected = items.itemById.get(selectedId) || items.itemById.get(defaultSelectedId(items));
  const highlightedPath = pathToRoot(selected, items);
  const skillRowGap = 76;
  const skillsByCompetency = items.skills.reduce((groups, skill) => {
    groups[skill.parentCompetencyId] = groups[skill.parentCompetencyId] || [];
    groups[skill.parentCompetencyId].push(skill);
    return groups;
  }, {});
  let nextGroupY = 30;
  const competencyPositions = new Map(items.competencies.map((competency) => {
    const skillCount = (skillsByCompetency[competency.id] || []).length;
    const groupHeight = Math.max(104, skillCount * skillRowGap);
    const competencyY = nextGroupY + (Math.max(0, skillCount - 1) * skillRowGap) / 2;
    nextGroupY += groupHeight;
    return [competency.id, competencyY];
  }));
  const nodes = [
    {
      id: "profile-root",
      type: "domain",
      position: { x: 15, y: (32 + nextGroupY) / 2 },
      data: {
        label: profileDomain(graph.profile_id),
        item: { id: "profile-root", kind: "profile", label: profileDomain(graph.profile_id) },
        selected: selectedId === "profile-root",
        highlighted: highlightedPath.has("profile-root")
      }
    }
  ];
  const edges = [];

  items.competencies.forEach((competency) => {
    const competencyY = competencyPositions.get(competency.id);
    nodes.push({
      id: competency.id,
      type: "topic",
      position: { x: 240, y: competencyY },
      data: {
        label: competency.label,
        item: competency,
        state: stateFor(competency),
        targetType: competency.target_type,
        selected: selected?.id === competency.id,
        highlighted: highlightedPath.has(competency.id)
      }
    });
    edges.push({
      id: `root-${competency.id}`,
      source: "profile-root",
      target: competency.id,
      animated: highlightedPath.has(competency.id),
      className: highlightedPath.has(competency.id) ? "kg-edge-path" : competency.target_type === "desired" ? "kg-edge-desired" : "kg-edge-muted",
    });
  });

  items.competencies.forEach((competency) => {
    const competencyY = competencyPositions.get(competency.id);
    const skills = skillsByCompetency[competency.id] || [];
    const localStartY = competencyY - ((skills.length - 1) * skillRowGap) / 2;

    skills.forEach((skill, skillIndex) => {
      const skillY = localStartY + skillIndex * skillRowGap;
      nodes.push({
        id: skill.id,
        type: "topic",
        position: { x: 520, y: skillY },
        data: {
          label: skill.label,
          item: skill,
          state: stateFor(skill),
          targetType: skill.target_type,
          selected: selected?.id === skill.id,
          highlighted: highlightedPath.has(skill.id)
        }
      });
      edges.push({
        id: `${competency.id}-${skill.id}`,
        source: competency.id,
        target: skill.id,
        animated: highlightedPath.has(competency.id) && highlightedPath.has(skill.id),
        className: highlightedPath.has(competency.id) && highlightedPath.has(skill.id) ? "kg-edge-path" : skill.target_type === "desired" ? "kg-edge-desired" : "kg-edge-muted"
      });
    });
  });

  items.skills.forEach((skill) => {
    skill.prerequisites.forEach((prerequisiteId) => {
      const prerequisite = items.skillBySkillId.get(prerequisiteId);
      if (!prerequisite) return;
      const isSelectedPrereqPath = selected?.id === skill.id && prerequisite.id !== skill.parentCompetencyId;
      edges.push({
        id: `prereq-${prerequisite.id}-${skill.id}`,
        source: prerequisite.id,
        target: skill.id,
        animated: isSelectedPrereqPath,
        className: isSelectedPrereqPath ? "kg-edge-path kg-edge-prereq" : "kg-edge-muted kg-edge-prereq"
      });
    });
    (skill.study_predecessors || []).forEach((predecessorId) => {
      const predecessor = items.skillBySkillId.get(predecessorId);
      if (!predecessor) return;
      edges.push({
        id: `study-${predecessor.id}-${skill.id}`,
        source: predecessor.id,
        target: skill.id,
        className: "kg-edge-muted kg-edge-prereq"
      });
    });
  });

  return { nodes, edges, selected, items };
}

function itemMastery(item) {
  return item.kind === "competency" ? item.observed_mastery : item.mastery;
}

function DetailCard({ item, compact = false }) {
  if (!item || item.kind === "profile") return null;
  const mastery = itemMastery(item);
  const gap = item.gap === null || item.gap === undefined ? "Unknown" : `${Math.round(item.gap * 100)} percentage points`;
  const prerequisites = item.prerequisites?.length ? item.prerequisites.join(", ") : "None";
  const prerequisiteStatus = item.prerequisite_health?.prerequisite_health?.replaceAll("_", " ") || "No prerequisites";
  const evidenceCount = item.kind === "competency" ? `${item.evidence_coverage.assessed_skills}/${item.evidence_coverage.total_skills} skill(s)` : `${item.attempts} question(s)`;

  return (
    <aside className={compact ? "kg-tooltip" : "section-card kg-detail kg-detail-panel"}>
      <p className="text-xs font-bold uppercase tracking-wide text-indigo">{compact ? "Preview" : item.kind === "competency" ? item.competency_id : item.skill_node_id}</p>
      <h2 className="mt-1 text-xl font-bold text-ink">{item.label}</h2>
      <div className="mt-4 grid gap-2 text-sm text-slate-700">
        <span>Current Mastery: <strong>{percent(mastery)}</strong></span>
        <span>Target: <strong>{percent(item.target_mastery)}</strong></span>
        {!compact ? <span>Gap: <strong>{gap}</strong></span> : null}
        <span>Status: <strong>{stateLabels[stateFor(item)]}</strong></span>
        {!compact ? <span>Required for Role: <strong>{item.required ? "YES" : "NO"}</strong></span> : null}
        {!compact ? <span>Evidence Availability: <strong>{item.evidence_status.replaceAll("_", " ")}</strong></span> : null}
        {!compact ? <span>Evidence: <strong>{evidenceCount}</strong></span> : null}
        {!compact ? <span>Accuracy: <strong>{item.accuracy === null || item.accuracy === undefined ? "Not assessed" : percent(item.accuracy)}</strong></span> : null}
        {!compact ? <span>Confidence: <strong>{item.confidence ?? "Not assessed"} / 5</strong></span> : null}
        {!compact ? <span>Average Response Time: <strong>{seconds(item.avg_response_time)}</strong></span> : null}
        {!compact ? <span>Prerequisites: <strong>{prerequisites}</strong></span> : null}
        {!compact ? <span>Prerequisite Status: <strong>{prerequisiteStatus}</strong></span> : null}
      </div>
      {!compact && item.misconceptions?.length ? (
        <div className="mt-4 rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900">
          <p className="font-bold">Potential Misconceptions</p>
          <ul className="mt-2 list-disc pl-5">
            {item.misconceptions.map((tag) => <li key={tag}>{tag}</li>)}
          </ul>
        </div>
      ) : null}
      {!compact ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
          <strong>Recommended Action</strong>
          <p className="mt-1">{mastery === null ? `Gather evidence for ${item.label}` : `Learn ${item.label} Fundamentals`}</p>
        </div>
      ) : null}
    </aside>
  );
}

function FitOnChange({ focusKey }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    let timer = window.setTimeout(() => fitView({ padding: 0.16, duration: 420 }), 100);
    const fitOnResize = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => fitView({ padding: 0.16, duration: 280 }), 140);
    };
    window.addEventListener("resize", fitOnResize);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("resize", fitOnResize);
    };
  }, [fitView, focusKey]);
  return null;
}

export default function KnowledgeGraphStatePage() {
  const [activeProfileId, setActiveProfileId] = useState(getStoredProfileId());
  const [graph, setGraph] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [hoveredItem, setHoveredItem] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadGraph() {
      try {
        setError("");
        setGraph(null);
        setHoveredItem(null);
        const nextGraph = await getLearnerKnowledgeGraph(activeProfileId);
        const items = buildItems(nextGraph);
        setGraph(nextGraph);
        setSelectedId(defaultSelectedId(items));
      } catch (err) {
        setError("Unable to load learner knowledge graph.");
      }
    }
    loadGraph();
  }, [activeProfileId]);

  const flow = useMemo(() => graph ? buildFullFlow(graph, selectedId) : { nodes: [], edges: [], selected: null }, [graph, selectedId]);

  if (error) {
    return <main className="mx-auto max-w-5xl px-6 py-8"><section className="section-card">{error}</section></main>;
  }
  if (!graph) return <LoadingState />;

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <section className="mb-6 rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-indigo">Phase 4 - State</p>
            <h1 className="mt-2 text-3xl font-bold text-ink">DSA Knowledge Graph</h1>
            <p className="mt-3 text-slate-700">Explore evidence for 10 DSA topics and their prerequisites. Unassessed topics remain visible for future learning.</p>
            {graph.assessment_source?.assessment_mode === "sample" ? <div className="mt-3"><Badge tone="orange">Demo Sample Diagnostic</Badge></div> : null}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ProfileSelector activeProfileId={activeProfileId} onChange={setActiveProfileId} />
            <Link to="/roadmap" className="rounded-lg bg-indigo px-5 py-3 text-sm font-bold text-white">View Personalized Roadmap</Link>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="kg-shell kg-shell-allnodes">
          <div className="kg-legend kg-legend-focused">
            {Object.entries(stateLabels).map(([key, label]) => <span key={key} className={`legend-dot legend-${key}`}>{label}</span>)}
            <span className="kg-edge-legend"><i className="kg-edge-swatch" /> Learning path</span>
            <span className="kg-edge-legend"><i className="kg-edge-swatch kg-edge-swatch-prerequisite" /> Prerequisite / study order</span>
            <span className="kg-legend-hint">Select a topic to inspect its evidence and highlight its path.</span>
          </div>
          {hoveredItem ? <DetailCard item={hoveredItem} compact /> : null}
          <ReactFlow
            nodes={flow.nodes}
            edges={flow.edges}
            nodeTypes={nodeTypes}
            style={{ background: "#0d0e16" }}
            fitView
            minZoom={0.45}
            maxZoom={1.6}
            onNodeMouseEnter={(_, node) => node.data?.item && setHoveredItem(node.data.item)}
            onNodeMouseLeave={() => setHoveredItem(null)}
            onNodeClick={(_, node) => {
              if (node.data?.item?.kind !== "profile") setSelectedId(node.data.item.id);
            }}
          >
            <FitOnChange focusKey={flow.selected?.id} />
            <Background gap={28} size={1.1} color="#343447" />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>

        <DetailCard item={flow.selected} />
      </section>
    </main>
  );
}
