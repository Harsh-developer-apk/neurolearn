import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import Badge from "../components/Badge.jsx";
import LoadingState from "../components/LoadingState.jsx";
import { setStoredProfileId } from "../components/ProfileSelector.jsx";
import { getAssessmentResult } from "../services/api.js";

function PercentBar({ value, label = "Mastery" }) {
  const percent = Math.round(value * 100);
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs font-semibold text-muted">
        <span>{label}</span>
        <span>{percent}%</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-teal" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function seconds(ms) {
  return `${(ms / 1000).toFixed(1)} sec`;
}

export default function AssessmentResultsPage() {
  const [params] = useSearchParams();
  const sessionId = params.get("session");
  const profileId = params.get("profile_id");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadResults() {
      if (!sessionId) {
        setError("Missing assessment session.");
        return;
      }
      try {
        if (profileId) {
          setStoredProfileId(profileId);
        }
        const resultData = await getAssessmentResult(sessionId);
        setResult(resultData);
      } catch (err) {
        setError("Unable to load assessment results.");
      }
    }

    loadResults();
  }, [sessionId, profileId]);

  if (error) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-6">
        <section className="section-card max-w-xl">
          <h1 className="text-2xl font-bold text-ink">Results unavailable</h1>
          <p className="mt-3 text-slate-700">{error}</p>
          <Link to="/assessment" className="mt-6 inline-flex rounded-lg bg-indigo px-5 py-3 text-sm font-bold text-white">
            Start assessment
          </Link>
        </section>
      </main>
    );
  }

  if (!result) {
    return <LoadingState />;
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <section className="mb-6 rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-indigo">Current learner state</p>
            <h1 className="mt-2 text-3xl font-bold text-ink">Diagnostic completed</h1>
            <p className="mt-3 text-slate-700">Estimated from diagnostic evidence. Ability theta is not a percentage.</p>
            {result.assessment_mode === "sample" ? (
              <div className="mt-3">
                <Badge tone="orange">Demo Sample Diagnostic</Badge>
              </div>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/knowledge-graph" className="rounded-lg border border-indigo px-5 py-3 text-sm font-bold text-indigo">
              View Knowledge Graph
            </Link>
            <Link to="/roadmap" className="rounded-lg bg-indigo px-5 py-3 text-sm font-bold text-white">
              View Personalized Roadmap
            </Link>
            <Link to="/profile" className="rounded-lg border border-line px-5 py-3 text-sm font-bold text-ink">
              Back to Profile
            </Link>
          </div>
        </div>
      </section>

      <section className="mb-6 grid gap-4 md:grid-cols-5">
        <article className="section-card">
          <p className="text-sm font-semibold text-muted">Questions</p>
          <p className="mt-2 text-3xl font-bold text-ink">{result.assessment.questions_answered}</p>
        </article>
        <article className="section-card">
          <p className="text-sm font-semibold text-muted">Correct</p>
          <p className="mt-2 text-3xl font-bold text-ink">{result.assessment.correct_count}</p>
        </article>
        <article className="section-card">
          <p className="text-sm font-semibold text-muted">Incorrect</p>
          <p className="mt-2 text-3xl font-bold text-ink">{result.assessment.incorrect_count}</p>
        </article>
        <article className="section-card">
          <p className="text-sm font-semibold text-muted">Accuracy</p>
          <p className="mt-2 text-3xl font-bold text-ink">{Math.round(result.assessment.accuracy * 100)}%</p>
        </article>
        <article className="section-card">
          <p className="text-sm font-semibold text-muted">IRT Ability</p>
          <p className="mt-2 text-3xl font-bold text-ink">{result.irt.ability_label}</p>
          <p className="mt-1 text-sm text-muted">Theta: {result.irt.theta}</p>
        </article>
        <article className="section-card">
          <p className="text-sm font-semibold text-muted">Avg Response Time</p>
          <p className="mt-2 text-3xl font-bold text-ink">{seconds(result.response_time.average_response_time_ms)}</p>
        </article>
      </section>

      <section className="section-card">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-muted">Competency-level mastery</p>
            <h2 className="mt-1 text-2xl font-bold text-ink">Five active diagnostic competencies</h2>
          </div>
          <Badge tone="blue">Prototype equal skill-weight average</Badge>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {result.competencies.map((competency) => (
            <article className="rounded-lg border border-line bg-slate-50 p-4" key={competency.competency_id}>
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-ink">{competency.name}</h3>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                    {competency.assessed_skill_count} assessed skill(s) - {competency.evidence_status} evidence
                  </p>
                </div>
                <Badge tone="green">{Math.round(competency.mastery * 100)}%</Badge>
              </div>
              <PercentBar value={competency.mastery} />
            </article>
          ))}
        </div>
      </section>

      <section className="section-card mt-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
          <p className="text-sm font-bold uppercase tracking-wide text-muted">Skill-level mastery</p>
          <h2 className="mt-1 text-2xl font-bold text-ink">Evidence-adjusted mastery</h2>
          </div>
          <Badge tone="gray">{result.skills.length} assessed skill(s)</Badge>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {result.skills.map((skill) => (
            <article className="rounded-lg border border-line bg-white p-4" key={skill.skill_node_id}>
              <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-ink">{skill.name}</h3>
                  <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted">
                    {skill.skill_node_id} - {skill.competency_name}
                  </p>
                </div>
                <Badge tone="orange">{skill.evidence_status.replaceAll("_", " ")}</Badge>
              </div>
              <PercentBar value={skill.mastery_probability} label="Evidence-adjusted mastery" />
              <div className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
                <span>Session evidence: {skill.attempts} question(s)</span>
                <span>{skill.correct_attempts} correct, {skill.incorrect_attempts} incorrect</span>
                <span>Confidence: {skill.confidence_avg} / 5</span>
                <span>Avg time: {seconds(skill.avg_response_time_ms)}</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-2">
        <article className="section-card">
          <p className="text-sm font-bold uppercase tracking-wide text-muted">Confidence analysis</p>
          <div className="mt-4 grid gap-3 text-sm text-slate-700">
            <p>Average confidence: <strong>{result.confidence_analysis.average_confidence} / 5</strong></p>
            <p>Correct + high confidence: <strong>{result.confidence_analysis.correct_high_confidence}</strong></p>
            <p>Correct + low confidence: <strong>{result.confidence_analysis.correct_low_confidence}</strong></p>
            <p>Incorrect + high confidence: <strong>{result.confidence_analysis.incorrect_high_confidence}</strong></p>
            <p>Incorrect + low confidence: <strong>{result.confidence_analysis.incorrect_low_confidence}</strong></p>
          </div>
        </article>

        <article className="section-card">
          <p className="text-sm font-bold uppercase tracking-wide text-muted">Potential misconception indicators</p>
          {result.misconception_signals.length ? (
            <div className="mt-4 grid gap-3">
              {result.misconception_signals.map((signal, index) => (
                <div className="rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900" key={`${signal.question_id}-${index}`}>
                  <p className="font-bold">Potential misconception signal</p>
                  <p className="mt-1">{signal.skill_node_id}: {signal.tags.join(", ")}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-700">No misconception signal was detected from incorrect responses.</p>
          )}
        </article>
      </section>

      <section className="section-card mt-6">
        <p className="text-sm font-bold uppercase tracking-wide text-muted">IRT explanation</p>
        <p className="mt-3 text-sm leading-6 text-slate-700">
          Ability estimate is based on response patterns and question difficulty. Skill mastery is estimated separately with BKT, and competency mastery is a prototype aggregation from assessed skill evidence.
        </p>
      </section>
    </main>
  );
}
