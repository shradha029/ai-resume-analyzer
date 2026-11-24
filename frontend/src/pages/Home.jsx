import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, ErrorBanner, Spinner } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import { fmtDate, pct, scoreColor } from "../utils/format";

export default function Home() {
  const { user } = useAuth();
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [ml, setMl] = useState(null);

  const load = () => api.history().then(setItems).catch((e) => setError(errorMessage(e)));
  useEffect(() => { load(); api.mlInfo().then((r) => setMl(r.role_classifier)).catch(() => setMl(null)); }, []);

  async function remove(id) {
    if (!window.confirm("Delete this analysis and its report?")) return;
    try { await api.deleteAnalysis(id); load(); } catch (e) { setError(errorMessage(e)); }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Hello, {user?.full_name}</h1>
          <p className="text-sm text-slate-500">Upload a resume, paste a job description and see exactly where the gaps are.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/resumes"><Button variant="secondary">Upload resume</Button></Link>
          <Link to="/analyze"><Button>New analysis</Button></Link>
        </div>
      </div>
      <ErrorBanner message={error} />
      <Card title="Analysis history">
        {items === null && !error && <Spinner />}
        {items?.length === 0 && (
          <p className="py-6 text-center text-sm text-slate-500">No analyses yet. <Link className="font-medium text-brand-600" to="/analyze">Create your first one.</Link></p>
        )}
        {items?.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr><th className="py-2">Role</th><th>Resume</th><th>Match</th><th>Coverage</th><th>Date</th><th /></tr>
              </thead>
              <tbody>
                {items.map((a) => (
                  <tr key={a.id} className="border-t border-slate-100">
                    <td className="py-2 font-medium"><Link className="text-brand-600" to={`/analysis/${a.id}`}>{a.target_role}</Link></td>
                    <td>{a.resume_filename}</td>
                    <td style={{ color: scoreColor(a.match_score) }}>{pct(a.match_score)}</td>
                    <td style={{ color: scoreColor(a.skill_coverage_score) }}>{pct(a.skill_coverage_score)}</td>
                    <td className="text-slate-500">{fmtDate(a.created_at)}</td>
                    <td className="text-right"><Button variant="danger" onClick={() => remove(a.id)}>Delete</Button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {ml && (
        <Card title="Job-role classifier (machine learning)">
          {ml.trained ? (
            <p className="text-sm text-slate-600" data-testid="ml-status">
              Model: <span className="font-medium">{ml.metrics.selected_model}</span> - test macro-F1 {ml.metrics.test.f1_macro.toFixed(3)},
              accuracy {ml.metrics.test.accuracy.toFixed(3)} on {ml.metrics.split.test_rows} held-out job descriptions,
              {" "}{ml.metrics.dataset.n_classes} categories (dataset: {ml.metrics.dataset.source_file}; see docs for what it was trained on).
            </p>
          ) : (
            <p className="text-sm text-slate-500" data-testid="ml-status">Not trained yet. Train it with your dataset (see datasets/README.md); no accuracy is shown until then.</p>
          )}
        </Card>
      )}
      <Card title="How it works">
        <ol className="grid gap-3 text-sm text-slate-600 sm:grid-cols-4">
          {["Upload your PDF resume", "Review the extracted data", "Paste a job description", "Get scores, gaps and a PDF report"].map((t, i) => (
            <li key={t} className="flex gap-2"><Badge tone="blue">{i + 1}</Badge>{t}</li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
