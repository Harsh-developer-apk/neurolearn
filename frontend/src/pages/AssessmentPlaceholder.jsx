import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Badge from "../components/Badge.jsx";
import ProfileSelector, { getStoredProfileId } from "../components/ProfileSelector.jsx";
import { runSampleAssessment, startAssessment, submitAssessmentAnswer } from "../services/api.js";

const confidenceLabels = {
  1: "Just guessing",
  2: "Slightly confident",
  3: "Moderately confident",
  4: "Very confident",
  5: "Completely confident"
};

function formatPercent(value) {
  if (value === null || value === undefined) return "No evidence";
  return `${Math.round(value * 100)}%`;
}

function formatSeconds(ms) {
  return `${(ms / 1000).toFixed(1)} sec`;
}

function ModelPanel({ modelState, feedback }) {
  const currentSkill = modelState?.current_skill;
  const irt = modelState?.irt;
  const question = modelState?.question;

  return (
    <aside className="rounded-lg border border-indigo bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-wide text-indigo">Model Transparency - Demo Mode</p>
      <div className="mt-4 grid gap-4 text-sm">
        <div>
          <p className="font-bold text-ink">IRT</p>
          <p className="mt-1 text-slate-700">Ability theta: {irt ? irt.theta.toFixed(2) : "0.00"}</p>
          <p className="text-slate-700">Question difficulty: {irt?.question_difficulty ?? "-"}</p>
          <p className="text-slate-700">P(correct): {irt?.estimated_probability !== null && irt?.estimated_probability !== undefined ? `${Math.round(irt.estimated_probability * 100)}%` : "-"}</p>
        </div>

        <div>
          <p className="font-bold text-ink">Current Skill</p>
          <p className="mt-1 text-slate-700">{currentSkill?.skill_name || "-"}</p>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{currentSkill?.competency_name || "-"}</p>
          <p className="mt-2 text-slate-700">BKT mastery: {formatPercent(currentSkill?.bkt_mastery)}</p>
          <p className="text-slate-700">Attempts: {currentSkill?.attempts ?? 0}</p>
          <p className="text-slate-700">Correct: {currentSkill?.correct_attempts ?? 0}</p>
        </div>

        <div>
          <p className="font-bold text-ink">Evidence</p>
          <p className="mt-1 text-slate-700">Confidence: {feedback ? `${feedback.response_evidence.confidence} / 5` : `${currentSkill?.confidence_avg || 0} / 5 avg`}</p>
          {feedback?.response_evidence.weighting_reason ? <p className="mt-1 text-xs text-slate-700">{feedback.response_evidence.weighting_reason}</p> : null}
          <p className="text-slate-700">Response time: {feedback ? formatSeconds(feedback.response_evidence.response_time_ms) : formatSeconds(currentSkill?.avg_response_time_ms || 0)}</p>
          <p className="text-slate-700">Cognitive level: {question?.cognitive_level || "-"}</p>
          <p className="text-slate-700">Question type: {question?.question_type || "-"}</p>
        </div>

        <div>
          <p className="font-bold text-ink">Decision</p>
          <p className="mt-1 rounded-lg bg-slate-50 p-3 text-slate-700">{modelState?.decision || "Begin diagnostic"}</p>
        </div>
      </div>
    </aside>
  );
}

function LiveSkillTable({ modelState }) {
  const competencies = modelState?.competencies || [];

  return (
    <section className="rounded-lg border border-line bg-white p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-wide text-muted">Live Skill Mastery</p>
      <div className="mt-4 grid gap-5">
        {competencies.map((competency) => (
          <div key={competency.competency_id}>
            <div className="mb-2 flex items-center justify-between gap-3">
              <h3 className="font-bold text-ink">{competency.name}</h3>
              <span className="text-xs font-semibold text-muted">{competency.competency_id}</span>
            </div>
            <div className="grid gap-2">
              {competency.skills.map((skill) => {
                const percent = skill.mastery_probability === null || skill.mastery_probability === undefined ? 0 : Math.round(skill.mastery_probability * 100);
                return (
                  <div className="grid gap-2 rounded-lg bg-slate-50 p-3" key={skill.skill_node_id}>
                    <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                      <span className="font-semibold text-ink">{skill.name}</span>
                      <span className="text-xs font-semibold uppercase tracking-wide text-muted">{skill.evidence_status.replaceAll("_", " ")}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                        <div className="h-full rounded-full bg-teal" style={{ width: `${percent}%` }} />
                      </div>
                      <span className="w-16 text-right text-sm font-bold text-ink">{formatPercent(skill.mastery_probability)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function AssessmentPlaceholder() {
  const navigate = useNavigate();
  const startedAtRef = useRef(0);
  const [activeProfileId, setActiveProfileId] = useState(getStoredProfileId());
  const [sessionId, setSessionId] = useState("");
  const [question, setQuestion] = useState(null);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [displayQuestionNumber, setDisplayQuestionNumber] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(15);
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [confidence, setConfidence] = useState(3);
  const [feedback, setFeedback] = useState(null);
  const [pendingNextQuestion, setPendingNextQuestion] = useState(null);
  const [modelState, setModelState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleStart() {
    setLoading(true);
    setError("");
    try {
      const data = await startAssessment(activeProfileId);
      setSessionId(data.session_id);
      setQuestion(data.question);
      setAnsweredCount(0);
      setDisplayQuestionNumber(data.question_number);
      setTotalQuestions(data.total_questions);
      setSelectedOptions([]);
      setConfidence(3);
      setFeedback(null);
      setPendingNextQuestion(null);
      setModelState(data.model_state);
      startedAtRef.current = performance.now();
    } catch (err) {
      setError("Unable to start the diagnostic assessment. Check that the backend is running with Phase 3 routes.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSampleDiagnostic() {
    setLoading(true);
    setError("");
    try {
      const result = await runSampleAssessment(activeProfileId);
      navigate(`/assessment/results?session=${result.session_id}&profile_id=${activeProfileId}&mode=sample`);
    } catch (err) {
      setError("Unable to run sample diagnostic. Check that the backend is running with Phase 3 routes.");
    } finally {
      setLoading(false);
    }
  }

  function toggleOption(optionId) {
    if (feedback) return;
    if (question.response_mode === "multiple") {
      setSelectedOptions((current) => current.includes(optionId) ? current.filter((item) => item !== optionId) : [...current, optionId].sort());
    } else {
      setSelectedOptions([optionId]);
    }
  }

  async function handleSubmit() {
    if (!selectedOptions.length || !question) return;

    setLoading(true);
    setError("");
    try {
      const responseTimeMs = Math.round(performance.now() - startedAtRef.current);
      const payload = {
        question_id: question.question_id,
        response_time_ms: responseTimeMs,
        confidence
      };
      if (question.response_mode === "multiple") {
        payload.selected_options = selectedOptions;
      } else {
        payload.selected_option = selectedOptions[0];
      }
      const data = await submitAssessmentAnswer(sessionId, payload);

      setFeedback(data);
      setAnsweredCount(data.progress.current);
      setPendingNextQuestion(data.next_question);
      setModelState(data.model_state);
    } catch (err) {
      setError("Unable to submit answer. The question may already have been answered.");
    } finally {
      setLoading(false);
    }
  }

  function handleNext() {
    if (!pendingNextQuestion) {
      navigate(`/assessment/results?session=${sessionId}&profile_id=${activeProfileId}`);
      return;
    }
    setQuestion(pendingNextQuestion);
    setPendingNextQuestion(null);
    setDisplayQuestionNumber(answeredCount + 1);
    setSelectedOptions([]);
    setConfidence(3);
    setFeedback(null);
    startedAtRef.current = performance.now();
  }

  const progressPercent = Math.round((answeredCount / totalQuestions) * 100);
  const isMultiple = question?.response_mode === "multiple";

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-8">
      <section className="mb-6 rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-indigo">Phase 3</p>
            <h1 className="mt-2 text-3xl font-bold text-ink">DSA Diagnostic Assessment</h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ProfileSelector
              activeProfileId={activeProfileId}
              onChange={(profileId) => {
                setActiveProfileId(profileId);
                setSessionId("");
                setQuestion(null);
                setAnsweredCount(0);
                setDisplayQuestionNumber(0);
                setSelectedOptions([]);
                setFeedback(null);
                setPendingNextQuestion(null);
                setModelState(null);
              }}
            />
            <Link to="/profile" className="rounded-lg border border-indigo px-5 py-3 text-sm font-bold text-indigo">
              Back to Profile
            </Link>
          </div>
        </div>
      </section>

      {error ? (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">
          {error}
        </div>
      ) : null}

      {!sessionId ? (
        <section className="section-card">
          <Badge tone="blue">15-question adaptive evidence budget</Badge>
          <h2 className="mt-4 text-2xl font-bold text-ink">Ready to assess your DSA knowledge</h2>
          <p className="mt-3 text-slate-700">
            Answer 15 adaptive questions from a bank of 100 covering 10 DSA topics. Topics without enough evidence remain unassessed or uncertain.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              className="rounded-lg bg-indigo px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
              type="button"
              onClick={handleStart}
              disabled={loading}
            >
              {loading ? "Starting..." : "Start Diagnostic"}
            </button>
            <button
              className="rounded-lg border border-indigo bg-white px-5 py-3 text-sm font-bold text-indigo disabled:opacity-60"
              type="button"
              onClick={handleSampleDiagnostic}
              disabled={loading}
            >
              {loading ? "Running sample..." : "Run Sample Diagnostic (Demo)"}
            </button>
          </div>
        </section>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="grid gap-6">
            <section className="section-card">
              <div className="mb-6">
                <div className="mb-2 flex items-center justify-between text-sm font-semibold text-muted">
                  <span>Question {displayQuestionNumber} of {totalQuestions}</span>
                  <span>{answeredCount} / {totalQuestions}</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-indigo transition-all" style={{ width: `${progressPercent}%` }} />
                </div>
              </div>

              {question ? (
                <>
                  <div className="mb-4 flex flex-wrap gap-2">
                    <Badge tone="gray">{question.cognitive_level}</Badge>
                    <Badge tone="blue">{question.question_type}</Badge>
                    <Badge tone="orange">difficulty {question.difficulty}</Badge>
                  </div>
                  {isMultiple ? (
                    <p className="mb-3 text-sm font-bold text-indigo">Select all that apply.</p>
                  ) : null}
                  <h2 className="text-2xl font-bold leading-9 text-ink">{question.question_text}</h2>
                  <div className="mt-6 grid gap-3">
                    {Object.entries(question.options).map(([key, value]) => (
                      <label
                        className={`flex cursor-pointer gap-3 rounded-lg border p-4 text-sm ${
                          selectedOptions.includes(key) ? "border-indigo bg-blue-50" : "border-line bg-white"
                        } ${feedback ? "cursor-default opacity-80" : ""}`}
                        key={key}
                      >
                        <input
                          type={isMultiple ? "checkbox" : "radio"}
                          name="answer"
                          value={key}
                          checked={selectedOptions.includes(key)}
                          disabled={Boolean(feedback)}
                          onChange={() => toggleOption(key)}
                        />
                        <span><strong>{key}.</strong> {value}</span>
                      </label>
                    ))}
                  </div>

                  {!feedback ? (
                    <div className="mt-6 rounded-lg border border-line bg-slate-50 p-4">
                      <p className="text-sm font-bold text-ink">Confidence</p>
                      <div className="mt-3 grid gap-2 sm:grid-cols-5">
                        {[1, 2, 3, 4, 5].map((value) => (
                          <button
                            className={`rounded-lg border px-3 py-3 text-xs font-bold ${
                              confidence === value ? "border-indigo bg-indigo text-white" : "border-line bg-white text-ink"
                            }`}
                            key={value}
                            type="button"
                            onClick={() => setConfidence(value)}
                          >
                            {value}
                            <span className="mt-1 block font-semibold normal-case">{confidenceLabels[value]}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </>
              ) : (
                <div>
                  <h2 className="text-2xl font-bold text-ink">Diagnostic completed</h2>
                  <p className="mt-3 text-slate-700">All responses have been captured as learner evidence.</p>
                </div>
              )}

              {feedback ? (
                <div className={`mt-6 rounded-lg border p-4 ${feedback.correct ? "border-emerald-200 bg-emerald-50" : "border-orange-200 bg-orange-50"}`}>
                  <p className={`font-bold ${feedback.correct ? "text-emerald-800" : "text-orange-800"}`}>
                    {feedback.correct ? "Correct" : "Incorrect"}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{feedback.explanation}</p>
                  <div className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-3">
                    <span>Response time: {formatSeconds(feedback.response_evidence.response_time_ms)}</span>
                    <span>Confidence: {feedback.response_evidence.confidence} / 5</span>
                    <span>Decision: {feedback.decision}</span>
                  </div>
                </div>
              ) : null}

              <div className="mt-6 flex justify-end">
                {!feedback && question ? (
                  <button
                    className="rounded-lg bg-indigo px-5 py-3 text-sm font-bold text-white disabled:opacity-50"
                    type="button"
                    disabled={!selectedOptions.length || loading}
                    onClick={handleSubmit}
                  >
                    {loading ? "Submitting..." : "Submit Answer"}
                  </button>
                ) : (
                  <button
                    className="rounded-lg bg-indigo px-5 py-3 text-sm font-bold text-white"
                    type="button"
                    onClick={handleNext}
                  >
                    {pendingNextQuestion ? "Next Question" : "View Results"}
                  </button>
                )}
              </div>
            </section>

            <LiveSkillTable modelState={modelState} />
          </div>

          <ModelPanel modelState={modelState} feedback={feedback} />
        </div>
      )}
    </main>
  );
}
