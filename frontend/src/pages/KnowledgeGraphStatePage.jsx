import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Background, Controls, Handle, MiniMap, Position, ReactFlow, useReactFlow } from "@xyflow/react";
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

function stateFor(item) {
  if (item.target_type === "desired" && item.mastery === null) return "desired";
  if (item.mastery === null || item.evidence_status === "not_assessed") return "not-assessed";
  if (item.evidence_status === "weak" || (item.gap ?? 0) >= 0.3) return "weak";
  if (item.evidence_status === "uncertain" || item.evidence_status === "gathering_evidence") return "uncertain";
  return "strong";
}

const stateLabels = {
  strong: "Strong / On Track",
  weak: "Needs Improvement",
  uncertain: "Uncertain",
  "not-assessed": "Not Assessed",
  desired: "Desired Goal"
};

function SkillNode({ data }) {
  return (
    <button className={`kg-node kg-node-${data.state}`} type="button">
      <Handle type="target" position={Position.Top} />
      <p className="kg-node-kicker">{data.targetType === "required" ? "Required" : "Desired"}</p>
      <h3>{data.label}</h3>
      <p>Mastery: {percent(data.mastery)}</p>
      <p>Target: {percent(data.targetMastery)}</p>
      <strong>{stateLabels[data.state]}</strong>
      <Handle type="source" position={Position.Bottom} />
    </button>
  );
}

function CompetencyNode({ data }) {
  return (
    <div className={`kg-competency kg-competency-${data.targetType}`}>
      <Handle type="target" position={Position.Top} />
      <p>{data.targetType === "required" ? "Required for Role" : "Personal Goal"}</p>
      <h3>{data.label}</h3>
      <span>Target {percent(data.targetMastery)}</span>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

function DomainNode({ data }) {
  return (
    <div className="kg-domain">
      <h3>{data.label}</h3>
      <p>Current competency state</p>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = {
  domain: DomainNode,
  competency: CompetencyNode,
  skill: SkillNode
};

function profileDomain(profileId) {
  return profileId === "PROFILE002" ? "Computer Science" : "Statistics";
}

function buildFlow(graph) {
  const competencies = graph.competencies || [];
  const required = competencies.filter((item) => item.target_type === "required");
  const desired = competencies.filter((item) => item.target_type === "desired");
  const ordered = [...required, ...desired];
  const nodes = [
    {
      id: "domain",
      type: "domain",
      position: { x: 360, y: 0 },
      data: { label: profileDomain(graph.profile_id) }
    }
  ];
  const edges = [];

  ordered.forEach((competency, index) => {
    const x = index * 250;
    const compId = `competency-${competency.competency_id}-${competency.target_type}`;
    nodes.push({
      id: compId,
      type: "competency",
      position: { x, y: 150 },
      data: {
        label: competency.name,
        targetType: competency.target_type,
        targetMastery: competency.target_mastery,
        source: competency
      }
    });
    edges.push({
      id: `domain-${compId}`,
      source: "domain",
      target: compId,
      animated: true,
      className: "kg-edge-domain"
    });

    competency.skills.forEach((skill, skillIndex) => {
      const skillId = `skill-${skill.skill_node_id}-${competency.target_type}`;
      nodes.push({
        id: skillId,
        type: "skill",
        position: { x: x + (skillIndex % 2) * 118, y: 335 + Math.floor(skillIndex / 2) * 150 },
        data: {
          label: skill.name,
          state: stateFor(skill),
          targetType: skill.target_type,
          mastery: skill.mastery,
          targetMastery: skill.target_mastery,
          source: skill
        }
      });
      edges.push({
        id: `${compId}-${skillId}`,
        source: compId,
        target: skillId,
        animated: true,
        className: `kg-edge-${skill.target_type}`
      });
    });
  });

  const skillNodeByKey = new Map(nodes.filter((node) => node.type === "skill").map((node) => [node.data.source.skill_node_id, node.id]));
  nodes.filter((node) => node.type === "skill").forEach((node) => {
    node.data.source.prerequisites.forEach((prerequisiteId) => {
      const source = skillNodeByKey.get(prerequisiteId);
      if (source) {
        edges.push({
          id: `prereq-${source}-${node.id}`,
          source,
          target: node.id,
          animated: true,
          className: "kg-edge-prereq",
          label: "prerequisite"
        });
      }
    });
  });

  return { nodes, edges };
}

function DetailCard({ item, compact = false }) {
  if (!item) return null;
  const gap = item.gap === null || item.gap === undefined ? "Unknown" : `${Math.round(item.gap * 100)} percentage points`;
  const prerequisites = item.prerequisites?.length ? item.prerequisites.join(", ") : "None";
  const prerequisiteStatus = item.prerequisites?.length && item.mastery !== null && item.evidence_status !== "sufficient_mastery" ? "Needs Reinforcement" : "Ready";

  return (
    <aside className={compact ? "kg-tooltip" : "section-card kg-detail"}>
      <p className="text-xs font-bold uppercase tracking-wide text-indigo">{compact ? "Learner state" : item.skill_node_id}</p>
      <h2 className="mt-1 text-xl font-bold text-ink">{item.name}</h2>
      <div className="mt-4 grid gap-2 text-sm text-slate-700">
        <span>Current Mastery: <strong>{percent(item.mastery)}</strong></span>
        <span>Target: <strong>{percent(item.target_mastery)}</strong></span>
        {!compact ? <span>Gap: <strong>{gap}</strong></span> : null}
        <span>Status: <strong>{stateLabels[stateFor(item)]}</strong></span>
        {!compact ? <span>Required for Role: <strong>{item.required ? "YES" : "NO"}</strong></span> : null}
        {!compact ? <span>Evidence: <strong>{item.attempts} question(s)</strong></span> : null}
        {!compact ? <span>Accuracy: <strong>{item.accuracy === null ? "Not assessed" : percent(item.accuracy, "Not assessed")}</strong></span> : null}
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
          <p className="mt-1">Learn {item.name} Fundamentals</p>
        </div>
      ) : null}
    </aside>
  );
}

function FitOnLoad({ graph }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    const id = window.setTimeout(() => fitView({ padding: 0.18, duration: 700 }), 100);
    return () => window.clearTimeout(id);
  }, [fitView, graph]);
  return null;
}

export default function KnowledgeGraphStatePage() {
  const [activeProfileId, setActiveProfileId] = useState(getStoredProfileId());
  const [graph, setGraph] = useState(null);
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [hoveredSkill, setHoveredSkill] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadGraph() {
      try {
        setError("");
        setGraph(null);
        setSelectedSkill(null);
        setHoveredSkill(null);
        setGraph(await getLearnerKnowledgeGraph(activeProfileId));
      } catch (err) {
        setError("Unable to load learner knowledge graph.");
      }
    }
    loadGraph();
  }, [activeProfileId]);

  const flow = useMemo(() => graph ? buildFlow(graph) : { nodes: [], edges: [] }, [graph]);

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
            <h1 className="mt-2 text-3xl font-bold text-ink">Knowledge Graph</h1>
            <p className="mt-3 text-slate-700">Explore your current competency state and the relationships between skills.</p>
            {graph.assessment_source?.assessment_mode === "sample" ? <div className="mt-3"><Badge tone="orange">Demo Sample Diagnostic</Badge></div> : null}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ProfileSelector activeProfileId={activeProfileId} onChange={setActiveProfileId} />
            <Link to="/roadmap" className="rounded-lg bg-indigo px-5 py-3 text-sm font-bold text-white">View Personalized Roadmap</Link>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="kg-shell">
          <div className="kg-legend">
            {Object.entries(stateLabels).map(([key, label]) => <span key={key} className={`legend-dot legend-${key}`}>{label}</span>)}
            <span>Prerequisite relationship</span>
          </div>
          {hoveredSkill ? <DetailCard item={hoveredSkill} compact /> : null}
          <ReactFlow
            nodes={flow.nodes}
            edges={flow.edges}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.35}
            maxZoom={1.5}
            onNodeMouseEnter={(_, node) => node.type === "skill" && setHoveredSkill(node.data.source)}
            onNodeMouseLeave={() => setHoveredSkill(null)}
            onNodeClick={(_, node) => node.type === "skill" && setSelectedSkill(node.data.source)}
            onPaneClick={() => setSelectedSkill(null)}
          >
            <FitOnLoad graph={graph} />
            <Background gap={24} color="#d8e0ee" />
            <MiniMap pannable zoomable />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>

        <DetailCard item={selectedSkill || flow.nodes.find((node) => node.type === "skill")?.data.source} />
      </section>
    </main>
  );
}
