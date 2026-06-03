import { Routes, Route } from "react-router-dom";

import LandingPage from "./routes/index";
import UploadPage from "./routes/upload";
import StatusPage from "./routes/status.$jobId";
import ResultsPage from "./routes/results.$jobId";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/status/:jobId" element={<StatusPage />} />
      <Route path="/results/:jobId" element={<ResultsPage />} />
    </Routes>
  );
}