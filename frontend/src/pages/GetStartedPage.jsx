import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createLearnerProfile, getProfiles, previewSyllabus } from "../services/api.js";
import { setStoredProfileId } from "../components/ProfileSelector.jsx";

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = ["pdf", "docx", "txt", "png", "jpg", "jpeg"];

function Icon({ children, className = "" }) {
  return <span aria-hidden="true" className={`inline-flex items-center justify-center ${className}`}>{children}</span>;
}

function StepMeter({ step }) {
  return (
    <div className="flex items-center gap-2" aria-label={`Step ${step} of 3`}>
      {[1, 2, 3].map((value) => <span key={value} className={`h-1.5 rounded-full transition-all duration-500 ${value <= step ? "w-10 bg-violet-300" : "w-5 bg-white/15"}`} />)}
      <span className="ml-2 text-xs text-white/45">Step {step} of 3</span>
    </div>
  );
}

function toBase64(file) {
  return file.arrayBuffer().then((buffer) => {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const chunkSize = 0x8000;
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
    }
    return btoa(binary);
  });
}

export default function GetStartedPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [course, setCourse] = useState("");
  const [language, setLanguage] = useState("English");
  const [goal, setGoal] = useState("personal");
  const [goalDetails, setGoalDetails] = useState("");
  const [file, setFile] = useState(null);
  const [pastedText, setPastedText] = useState("");
  const [preview, setPreview] = useState(null);
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getProfiles().then((data) => {
      setProfiles(data);
      if (data.length) setSelectedProfile(data[0].profile_id);
    }).catch(() => setProfiles([]));
  }, []);

  const fileSize = useMemo(() => file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : "Up to 10 MB", [file]);

  function chooseFile(nextFile) {
    setError("");
    setPreview(null);
    if (!nextFile) {
      setFile(null);
      return;
    }
    const extension = nextFile.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError("Choose a PDF, DOCX, TXT, PNG, or JPG file.");
      return;
    }
    if (nextFile.size > MAX_FILE_SIZE) {
      setError("That file is larger than 10 MB. Choose a smaller syllabus file.");
      return;
    }
    setFile(nextFile);
    setPastedText("");
  }

  async function readSyllabus() {
    if (!file && !pastedText.trim()) return;
    setLoading(true);
    setLoadingStage(file ? "Preparing your file…" : "Reading your syllabus…");
    setError("");
    try {
      const payload = file
        ? { filename: file.name, content_type: file.type, file_base64: await toBase64(file) }
        : { pasted_text: pastedText };
      setLoadingStage(file ? "Uploading and reading your file…" : "Finding syllabus topics…");
      const result = await previewSyllabus(payload);
      setPreview(result);
      setSelectedTopics(result.topics.map((topic) => topic.skill_node_id));
    } catch (err) {
      setError(err.message || "We couldn't read that syllabus. Try another file or paste the text.");
    } finally {
      setLoading(false);
      setLoadingStage("");
    }
  }

  async function finishOnboarding(skipSyllabus = false) {
    if (!name.trim() || !course.trim() || !age) {
      setError("Add your name, age, and course or class to continue.");
      setStep(1);
      return;
    }
    if (!skipSyllabus && goal === "exam" && (file || pastedText.trim()) && !preview) {
      await readSyllabus();
      return;
    }
    if (goal === "exam" && preview && selectedTopics.length === 0) {
      setError("Select at least one syllabus topic. You can also choose topics manually if the syllabus wording was different.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const created = await createLearnerProfile({
        full_name: name.trim(),
        age: Number(age),
        course_or_class: course.trim(),
        preferred_language: language,
        subject_id: "dsa",
        learning_goal: goal,
        goal_details: goalDetails.trim(),
        syllabus_filename: skipSyllabus ? null : preview?.filename || file?.name || (pastedText.trim() ? "Pasted syllabus" : null),
        syllabus_content_type: skipSyllabus ? null : preview?.content_type || (pastedText.trim() ? "text/plain" : null),
        syllabus_text: skipSyllabus ? "" : preview?.extracted_text || "",
        suggested_skill_ids: skipSyllabus ? [] : (preview?.topics || []).map((topic) => topic.skill_node_id),
        included_skill_ids: skipSyllabus ? [] : selectedTopics,
      });
      setStoredProfileId(created.profile_id);
      navigate(`/assessment?profile_id=${encodeURIComponent(created.profile_id)}`);
    } catch (err) {
      setError(err.message || "We couldn't create your learner profile.");
    } finally {
      setLoading(false);
    }
  }

  function continueExisting() {
    if (!selectedProfile) return;
    setStoredProfileId(selectedProfile);
    navigate(`/assessment?profile_id=${encodeURIComponent(selectedProfile)}`);
  }

  function toggleTopic(skillId) {
    setSelectedTopics((current) => current.includes(skillId) ? current.filter((id) => id !== skillId) : [...current, skillId]);
  }

  const stepTitle = step === 1 ? "Let's make this yours." : step === 2 ? "What are you here to learn?" : "Shape your study scope.";
  const stepDescription = step === 1
    ? "A little context helps NeuroLearn meet you at the right level."
    : step === 2
      ? "We'll use your goal to decide how broad or focused your learning path should be."
      : "For exam prep, your syllabus can keep the roadmap focused. You can skip it and add it later.";

  return (
    <main className="welcome-shell relative min-h-screen overflow-hidden bg-[#080910] text-white selection:bg-violet-400/30">
      <div className="welcome-grid pointer-events-none absolute inset-0" />
      <div className="welcome-orb welcome-orb-one pointer-events-none absolute" />
      <div className="welcome-orb welcome-orb-two pointer-events-none absolute" />
      <div className="welcome-orb welcome-orb-three pointer-events-none absolute" />

      <nav className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-10">
        <div className="flex items-center gap-3">
          <div className="brand-mark grid h-10 w-10 place-items-center rounded-2xl border border-violet-300/25 bg-violet-400/10 text-lg font-semibold text-violet-100">N</div>
          <span className="text-lg font-semibold tracking-tight">neurolearn<span className="text-violet-300">.</span></span>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3 py-2 text-xs text-white/55 sm:flex">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" /> Your learning space, built around you
        </div>
      </nav>

      <div className="relative z-10 mx-auto grid max-w-7xl items-center gap-12 px-6 pb-14 pt-6 lg:grid-cols-[1.05fr_0.95fr] lg:px-10 lg:pb-20 lg:pt-10">
        <section className="welcome-copy max-w-2xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-300/20 bg-violet-300/[0.07] px-3 py-1.5 text-xs font-medium tracking-wide text-violet-100/80">
            <Icon className="text-sm">✳</Icon> A more personal way to learn
          </div>
          <h1 className="max-w-xl text-5xl font-medium leading-[1.04] tracking-[-0.045em] text-white sm:text-6xl lg:text-[4.5rem]">
            Learn at your pace<span className="welcome-gradient-text">. Grow with purpose.</span>
          </h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-white/55 sm:text-lg sm:leading-8">
            Tell us what you’re working toward. We’ll find what you know, what to learn next, and make every step feel clear.
          </p>

          <div className="mt-10 grid max-w-lg gap-4 sm:grid-cols-3">
            {[
              ["01", "Understand", "A quick picture of what you know"],
              ["02", "Find your path", "A roadmap shaped around your goal"],
              ["03", "Keep growing", "Lessons that respond to you"],
            ].map(([number, title, description], index) => (
              <div className="welcome-feature" style={{ animationDelay: `${180 + index * 110}ms` }} key={number}>
                <span className="text-[10px] font-semibold tracking-[0.18em] text-violet-200/55">{number}</span>
                <h2 className="mt-3 text-sm font-semibold text-white/85">{title}</h2>
                <p className="mt-1.5 text-xs leading-5 text-white/40">{description}</p>
              </div>
            ))}
          </div>
          <p className="mt-8 text-xs text-white/30">Designed for curious minds and the people who teach them.</p>
        </section>

        <section className="welcome-card-wrap mx-auto w-full max-w-xl lg:ml-auto">
          <div className="welcome-card rounded-[1.65rem] border border-white/[0.11] bg-[#11121b]/85 p-5 shadow-[0_35px_100px_rgba(0,0,0,0.48)] backdrop-blur-2xl sm:p-8">
            <div className="mb-8 flex items-center justify-between gap-3">
              <StepMeter step={step} />
              <span className="hidden text-xs text-white/35 sm:inline">No password needed for this demo</span>
            </div>

            <div key={step} className="step-content">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-violet-200/65">Get started</p>
              <h2 className="mt-2 text-2xl font-medium tracking-tight text-white sm:text-3xl">{stepTitle}</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-white/45">{stepDescription}</p>

              {step === 1 ? (
                <div className="mt-7 grid gap-4 sm:grid-cols-2">
                  <label className="sm:col-span-2"><span className="field-label">Your name</span><input className="welcome-input" autoComplete="name" maxLength={100} placeholder="e.g. Aanya Sharma" value={name} onChange={(event) => setName(event.target.value)} /></label>
                  <label><span className="field-label">Age</span><input className="welcome-input" type="number" min="10" max="100" inputMode="numeric" placeholder="21" value={age} onChange={(event) => setAge(event.target.value)} /></label>
                  <label><span className="field-label">Course or class</span><input className="welcome-input" maxLength={120} placeholder="e.g. MCA, 2nd year" value={course} onChange={(event) => setCourse(event.target.value)} /></label>
                  <label className="sm:col-span-2"><span className="field-label">Preferred language</span><select className="welcome-input welcome-select" value={language} onChange={(event) => setLanguage(event.target.value)}><option>English</option><option>Hindi</option><option>Hinglish</option></select></label>
                </div>
              ) : null}

              {step === 2 ? (
                <div className="mt-7 space-y-6">
                  <div>
                    <p className="field-label mb-3">Choose a subject</p>
                    <button type="button" className="subject-choice w-full rounded-2xl border border-violet-300/35 bg-violet-300/[0.08] p-4 text-left">
                      <span className="flex items-center justify-between gap-3">
                        <span className="flex items-center gap-3">
                          <span className="grid h-11 w-11 place-items-center rounded-xl bg-violet-300/10 text-xl text-violet-100">⌘</span>
                          <span><strong className="block text-sm font-semibold text-white">Data Structures & Algorithms</strong><small className="mt-1 block text-xs text-white/40">10 connected topics · adaptive learning</small></span>
                        </span>
                        <span className="grid h-5 w-5 place-items-center rounded-full border border-violet-200/70 bg-violet-300 text-xs text-[#15121c]">✓</span>
                      </span>
                    </button>
                    <p className="mt-2 text-[11px] text-white/30">More subjects can be added as NeuroLearn grows.</p>
                  </div>

                  <div>
                    <p className="field-label mb-3">What brings you here?</p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {[{ id: "personal", title: "Learning for myself", detail: "Explore DSA at your own pace", icon: "✧" }, { id: "exam", title: "Preparing for an exam", detail: "Focus the roadmap on your syllabus", icon: "◷" }].map((option) => (
                        <button type="button" onClick={() => setGoal(option.id)} className={`goal-choice rounded-xl border p-4 text-left transition ${goal === option.id ? "border-violet-300/45 bg-violet-300/[0.09]" : "border-white/10 bg-white/[0.025] hover:border-white/20"}`} key={option.id}>
                          <span className="text-lg text-violet-100/80">{option.icon}</span><strong className="mt-3 block text-sm font-semibold text-white/90">{option.title}</strong><span className="mt-1 block text-xs leading-5 text-white/40">{option.detail}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                  {goal === "exam" ? <label><span className="field-label">Anything specific? <span className="font-normal text-white/30">(optional)</span></span><textarea className="welcome-input mt-2 min-h-20 resize-y" rows="2" maxLength={500} placeholder="Semester exam, units 1–3, focus on problem solving…" value={goalDetails} onChange={(event) => setGoalDetails(event.target.value)} /></label> : null}
                </div>
              ) : null}

              {step === 3 ? (
                <div className="mt-7 space-y-5">
                  <div className="rounded-xl border border-violet-200/15 bg-violet-200/[0.045] p-4 text-sm leading-6 text-white/60">
                    Upload or paste your syllabus. We’ll extract its topics, let you review them, then focus your diagnostic and roadmap. Your syllabus is optional.
                  </div>
                  {!preview ? (
                    <>
                      <label className={`upload-zone flex ${loading ? "cursor-wait border-violet-200/40 bg-violet-200/[0.055]" : "cursor-pointer"} flex-col items-center rounded-2xl border border-dashed border-white/20 bg-white/[0.025] px-5 py-7 text-center transition hover:border-violet-200/45 hover:bg-violet-200/[0.04]`} aria-live="polite">
                        {loading ? <><span className="upload-spinner" aria-hidden="true" /><strong className="mt-3 text-sm font-semibold text-white/85">{loadingStage || "Working on your syllabus…"}</strong><span className="mt-1 text-xs text-white/40">This can take a few seconds. Keep this page open.</span><div className="upload-progress mt-4 h-1 w-full max-w-48 overflow-hidden rounded-full bg-white/10"><span className="block h-full rounded-full bg-violet-200" /></div></> : <>
                        <span className="grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/[0.045] text-xl text-violet-100">↑</span>
                        <strong className="mt-3 text-sm font-semibold text-white/85">{file ? file.name : "Choose a syllabus file"}</strong>
                        <span className="mt-1 text-xs text-white/40">PDF, DOCX, TXT, PNG or JPG · {fileSize}</span>
                        </>}
                        <input className="sr-only" type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" disabled={loading} onChange={(event) => chooseFile(event.target.files?.[0])} />
                      </label>
                      <div className="flex items-center gap-3 text-[10px] uppercase tracking-[0.18em] text-white/25"><span className="h-px flex-1 bg-white/10" />or paste text<span className="h-px flex-1 bg-white/10" /></div>
                      <textarea className="welcome-input min-h-28 resize-y" rows="4" maxLength={100000} placeholder="Paste the syllabus or unit-wise topics here…" value={pastedText} onChange={(event) => { setPastedText(event.target.value); setFile(null); setPreview(null); }} />
                      <p className="text-right text-[11px] text-white/30">{pastedText.length.toLocaleString()} / 100,000 characters</p>
                      {file || pastedText.trim() ? <button className="welcome-primary w-full" type="button" onClick={readSyllabus} disabled={loading}>{loading ? "Reading syllabus…" : error ? "Try reading again" : "Read and review topics"}</button> : null}
                    </>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex items-start justify-between gap-3 rounded-xl border border-emerald-200/20 bg-emerald-200/[0.055] p-4">
                        <div><p className="text-sm font-semibold text-emerald-100">Syllabus read</p><p className="mt-1 text-xs text-white/45">{preview.filename} · {preview.extracted_characters.toLocaleString()} characters</p>{preview.ocr_provider ? <p className="mt-1 text-[10px] text-white/35">Image text extracted by {preview.ocr_provider} / {preview.ocr_model}</p> : null}</div>
                        <button className="text-xs text-white/45 underline underline-offset-4 hover:text-white" type="button" onClick={() => { setPreview(null); setFile(null); setPastedText(""); }}>Replace</button>
                      </div>
                      <p className="field-label">Included topics <span className="font-normal text-white/35">Select the topics you need for your exam.</span></p>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {preview.all_topics.map((topic) => {
                          const checked = selectedTopics.includes(topic.skill_node_id);
                          return <label className={`topic-choice flex cursor-pointer items-start gap-3 rounded-xl border p-3 ${checked ? "border-violet-200/30 bg-violet-200/[0.07]" : "border-white/10 bg-white/[0.02]"}`} key={topic.skill_node_id}>
                            <input className="mt-0.5 accent-violet-300" type="checkbox" checked={checked} onChange={() => toggleTopic(topic.skill_node_id)} />
                            <span><strong className="block text-xs font-medium text-white/80">{topic.name}</strong>{topic.matched_terms.length ? <small className="mt-1 block text-[10px] text-violet-100/45">Matched: {topic.matched_terms.slice(0, 2).join(", ")}</small> : <small className="mt-1 block text-[10px] text-white/25">Not detected · select if needed</small>}</span>
                          </label>;
                        })}
                      </div>
                      <details className="rounded-xl border border-white/10 bg-black/10 p-3">
                        <summary className="cursor-pointer text-xs font-medium text-white/55">Review extracted syllabus text</summary>
                        <pre className="mt-3 max-h-44 overflow-auto whitespace-pre-wrap text-[11px] leading-5 text-white/40">{preview.extracted_text}</pre>
                      </details>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {error ? <div className="mt-5 rounded-xl border border-rose-300/20 bg-rose-300/[0.07] px-4 py-3 text-sm leading-5 text-rose-100/85">{error}</div> : null}

            <div className="mt-7 flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.08] pt-5">
              {step > 1 ? <button type="button" className="welcome-secondary" onClick={() => { setError(""); setStep(step - 1); }}>Back</button> : <span />}
              {step === 1 ? <button type="button" className="welcome-primary" onClick={() => { if (!name.trim() || !age || !course.trim()) { setError("Add your name, age, and course or class to continue."); return; } setError(""); setStep(2); }}>Continue <span aria-hidden="true">→</span></button> : null}
              {step === 2 ? <button type="button" className="welcome-primary" onClick={() => { setError(""); if (goal === "exam") setStep(3); else finishOnboarding(); }} disabled={loading}>{goal === "exam" ? <>Set my scope <span aria-hidden="true">→</span></> : loading ? "Creating…" : <>Create my learning space <span aria-hidden="true">→</span></>}</button> : null}
              {step === 3 && !preview ? <button type="button" className="welcome-secondary" onClick={() => finishOnboarding(true)} disabled={loading}>Skip syllabus</button> : null}
              {step === 3 && preview ? <button type="button" className="welcome-primary" onClick={finishOnboarding} disabled={loading || !selectedTopics.length}>{loading ? "Creating…" : <>Create my learning space <span aria-hidden="true">→</span></>}</button> : null}
            </div>

            {profiles.length ? (
              <div className="mt-6 rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
                <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/35">Already have a learner profile?</p>
                <div className="mt-2 flex gap-2">
                  <select className="welcome-input welcome-select min-w-0 flex-1 py-2 text-xs" value={selectedProfile} onChange={(event) => setSelectedProfile(event.target.value)}>{profiles.map((profile) => <option value={profile.profile_id} key={profile.profile_id}>{profile.label}</option>)}</select>
                  <button type="button" className="welcome-return" onClick={continueExisting}>Continue</button>
                </div>
                <p className="mt-2 text-[10px] leading-4 text-white/25">Profiles on this demo are selected by name, not protected by a password.</p>
              </div>
            ) : null}
          </div>
          <p className="mt-4 text-center text-[11px] text-white/25">By continuing, you create a learning profile stored by this project.</p>
        </section>
      </div>
    </main>
  );
}
