import { Navigate, Route, Routes } from "react-router-dom";

import AssessmentPlaceholder from "./pages/AssessmentPlaceholder.jsx";
import AssessmentResultsPage from "./pages/AssessmentResultsPage.jsx";
import CompetencyGraphPage from "./pages/CompetencyGraphPage.jsx";
import KnowledgeGraphStatePage from "./pages/KnowledgeGraphStatePage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import RoadmapPage from "./pages/RoadmapPage.jsx";
import LessonPage from "./pages/LessonPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/profile" replace />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/competency-graph" element={<CompetencyGraphPage />} />
      <Route path="/assessment" element={<AssessmentPlaceholder />} />
      <Route path="/assessment/topic" element={<AssessmentPlaceholder />} />
      <Route path="/assessment/results" element={<AssessmentResultsPage />} />
      <Route path="/knowledge-graph" element={<KnowledgeGraphStatePage />} />
      <Route path="/roadmap" element={<RoadmapPage />} />
      <Route path="/learn/:skillNodeId" element={<LessonPage />} />
    </Routes>
  );
}
