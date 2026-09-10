import Badge from "./Badge.jsx";

export default function CompetencyCard({ competency, type }) {
  const targetText = competency.target_label
    ? `${competency.target_label} (${competency.target_level})`
    : `Level ${competency.target_level}`;

  return (
    <article className="rounded-lg border border-line bg-slate-50 p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-ink">{competency.name}</h3>
          <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted">
            {competency.competency_id}
          </p>
        </div>
        <Badge tone={type === "desired" ? "orange" : "blue"}>{competency.category}</Badge>
      </div>
      <p className="text-sm leading-6 text-slate-700">{competency.description}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Badge tone={type === "desired" ? "orange" : "green"}>
          {type === "desired" ? `Target: ${targetText}` : `Required target: ${targetText}`}
        </Badge>
        {competency.source_activity_ids?.length ? (
          <Badge tone="gray">Derived from {competency.source_activity_ids.length} activity link(s)</Badge>
        ) : null}
      </div>
    </article>
  );
}
