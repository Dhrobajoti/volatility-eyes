import { NavLink, Route, Routes } from "react-router-dom";
import { ImagesPage } from "./pages/ImagesPage";
import { NewJobPage } from "./pages/NewJobPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsListPage } from "./pages/JobsListPage";
import { InsightsListPage } from "./pages/InsightsListPage";
import { InsightSessionPage } from "./pages/InsightSessionPage";
import { useInsightsAvailable } from "./api/insights";
import { EyeMark } from "./components/EyeMark";

function App() {
  const insightsAvailable = useInsightsAvailable();

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <div>
          <span className="app-title">
            <EyeMark size={26} />
            Volatility Eyes
          </span>
          <NavLink to="/" end>
            Images
          </NavLink>
          <NavLink to="/jobs">Analysis</NavLink>
          {insightsAvailable && <NavLink to="/insights">Insights</NavLink>}
        </div>
        <span className="app-credit">Developed by Dhrobajoti Paul</span>
      </nav>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<ImagesPage />} />
          <Route path="/jobs" element={<JobsListPage />} />
          <Route path="/jobs/new" element={<NewJobPage />} />
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
          <Route path="/insights" element={<InsightsListPage />} />
          <Route path="/insights/:sessionId" element={<InsightSessionPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
