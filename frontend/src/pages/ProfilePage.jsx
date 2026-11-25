import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Badge from "../components/Badge.jsx";
import CompetencyCard from "../components/CompetencyCard.jsx";
import LoadingState from "../components/LoadingState.jsx";
import ProfileSelector, { getStoredProfileId } from "../components/ProfileSelector.jsx";
import { getDesiredCompetencies, getProfile, getRequiredCompetencies } from "../services/api.js";

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [required, setRequired] = useState(null);
  const [desired, setDesired] = useState(null);
  const [activeProfileId, setActiveProfileId] = useState(getStoredProfileId());
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        setProfile(null);
        setRequired(null);
        setDesired(null);
        const [profileData, requiredData, desiredData] = await Promise.all([
          getProfile(activeProfileId),
          getRequiredCompetencies(activeProfileId),
          getDesiredCompetencies(activeProfileId)
        ]);
        setProfile(profileData);
        setRequired(requiredData);
        setDesired(desiredData);
      } catch (err) {
        setError("Unable to connect to the backend. Start FastAPI on http://127.0.0.1:8000.");
      }
    }

    loadData();
  }, [activeProfileId]);

  if (error) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-6">
        <section className="section-card max-w-xl">
          <h1 className="text-2xl font-bold text-ink">Backend connection needed</h1>
          <p className="mt-3 text-slate-700">{error}</p>
        </section>
      </main>
    );
  }

  if (!profile || !required || !desired) {
    return <LoadingState />;
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <section className="mb-6 overflow-hidden rounded-lg border border-line bg-white shadow-sm">
        <div className="bg-indigo px-6 py-5 text-white">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-blue-100">Learner Profile</p>
              <h1 className="mt-2 text-3xl font-bold">Competency profile and target layer</h1>
            </div>
            <ProfileSelector activeProfileId={activeProfileId} onChange={setActiveProfileId} />
          </div>
        </div>
        <div className="grid gap-6 p-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-muted">Learner account</p>
            <h2 className="mt-2 text-4xl font-bold text-ink">{profile.full_name}</h2>
            <p className="mt-2 text-base text-muted">Profile ID: {profile.profile_id}</p>
              <p className="mt-1 text-xl text-slate-700">{profile.course_or_class || "Data Structures and Algorithms learner"}</p>
          </div>
          <div className="grid gap-3">
            <div className="rounded-lg bg-slate-50 p-4">
              <span className="text-sm font-semibold text-muted">Language</span>
              <p className="mt-1 text-2xl font-bold text-ink">{profile.preferred_language}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <section className="section-card">
          <div className="mb-4">
            <p className="text-sm font-bold uppercase tracking-wide text-muted">Learning focus</p>
            <h2 className="mt-2 text-2xl font-bold text-ink">DSA competencies</h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">The roadmap and knowledge graph use your diagnostic answers to recommend topics to learn.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            {profile.activities.map((activity) => (
              <span className="chip" key={activity.activity_id}>{activity.name}</span>
            ))}
          </div>

          <div className="mt-8 border-t border-line pt-6">
            <p className="text-sm font-bold uppercase tracking-wide text-muted">Training history</p>
            <div className="mt-4 space-y-3">
              {profile.training_history.map((training) => (
                <div className="rounded-lg border border-line bg-white p-4" key={training.training_id}>
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-semibold text-ink">{training.title}</p>
                    <Badge tone="green">{training.completion_status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted">{training.provider}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section-card">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-bold uppercase tracking-wide text-muted">Required for current role</p>
              <h2 className="mt-2 text-2xl font-bold text-ink">Required competencies</h2>
            </div>
            <Badge tone="blue">Derived from role and activities</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {required.competencies.map((competency) => (
              <CompetencyCard competency={competency} key={competency.competency_id} type="required" />
            ))}
          </div>
        </section>
      </div>

      <section className="section-card mt-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-muted">Personal development goals</p>
            <h2 className="mt-2 text-2xl font-bold text-ink">My desired competencies</h2>
          </div>
          <Badge tone="orange">Hardcoded prototype goals</Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {desired.competencies.map((competency) => (
            <CompetencyCard competency={competency} key={competency.competency_id} type="desired" />
          ))}
        </div>
      </section>

      <section className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-line bg-white p-6 shadow-sm">
        <div>
          <p className="text-sm font-bold uppercase tracking-wide text-muted">Next module</p>
          <h2 className="mt-1 text-2xl font-bold text-ink">Diagnostic assessment</h2>
          <p className="mt-2 text-sm text-slate-700">
            Start an adaptive DSA diagnostic. If you added an exam syllabus, the questions focus on its selected topics and essential prerequisites.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link to="/competency-graph" className="rounded-lg border border-indigo px-5 py-3 text-sm font-bold text-indigo">
            View Competency Graph
          </Link>
          <Link to="/assessment" className="rounded-lg bg-indigo px-5 py-3 text-sm font-bold text-white">
            Start Diagnostic Assessment
          </Link>
        </div>
      </section>
    </main>
  );
}
