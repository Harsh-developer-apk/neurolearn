const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

async function request(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function getProfiles() {
  return request("/profiles");
}

function withProfile(path, profileId) {
  return profileId ? `${path}${path.includes("?") ? "&" : "?"}profile_id=${encodeURIComponent(profileId)}` : path;
}

export function getProfile(profileId) {
  return request(withProfile("/profile", profileId));
}

export function getRequiredCompetencies(profileId) {
  return request(withProfile("/profile/required-competencies", profileId));
}

export function getDesiredCompetencies(profileId) {
  return request(withProfile("/profile/desired-competencies", profileId));
}

export function getProfileTargetSkills(profileId) {
  return request(withProfile("/profile/target-skills", profileId));
}

export function getCompetencyGraph() {
  return request("/competency-graph");
}

export async function startAssessment(profileId) {
  const response = await fetch(`${API_BASE_URL}${withProfile("/assessment/start", profileId)}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export async function runSampleAssessment(profileId) {
  const response = await fetch(`${API_BASE_URL}${withProfile("/assessment/sample", profileId)}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export async function submitAssessmentAnswer(sessionId, payload) {
  const response = await fetch(`${API_BASE_URL}/assessment/${sessionId}/answer`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function getAssessmentResult(sessionId) {
  return request(`/assessment/${sessionId}/result`);
}

export function getLearnerCompetencyState(profileId) {
  return request(withProfile("/learner/competency-state", profileId));
}

export function getLearnerKnowledgeGraph(profileId) {
  return request(withProfile("/learner/knowledge-graph", profileId));
}

export function getLearnerRoadmap(profileId) {
  return request(withProfile("/learner/roadmap", profileId));
}
