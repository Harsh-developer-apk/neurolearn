import { Navigate, Route, Routes } from "react-router-dom";

import AssessmentPlaceholder from "./pages/AssessmentPlaceholder.jsx";
import AssessmentResultsPage from "./pages/AssessmentResultsPage.jsx";
import CompetencyGraphPage from "./pages/CompetencyGraphPage.jsx";
import KnowledgeGraphStatePage from "./pages/KnowledgeGraphStatePage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import RoadmapPage from "./pages/RoadmapPage.jsx";
import LessonPage from "./pages/LessonPage.jsx";
import GetStartedPage from "./pages/GetStartedPage.jsx";

export default function App() {
  return (
    <div className="app-theme-dark">
      <Routes>
        <Route path="/" element={<Navigate to="/get-started" replace />} />
        <Route path="/get-started" element={<GetStartedPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/competency-graph" element={<CompetencyGraphPage />} />
        <Route path="/assessment" element={<AssessmentPlaceholder />} />
        <Route path="/assessment/topic" element={<AssessmentPlaceholder />} />
        <Route path="/assessment/results" element={<AssessmentResultsPage />} />
        <Route path="/knowledge-graph" element={<KnowledgeGraphStatePage />} />
        <Route path="/roadmap" element={<RoadmapPage />} />
        <Route path="/learn/:skillNodeId" element={<LessonPage />} />
      </Routes>
    </div>
  );
}
