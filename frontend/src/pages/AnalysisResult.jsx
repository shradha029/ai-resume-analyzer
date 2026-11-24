import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CategoryChart, ComponentChart, MatchedMissingPie, QualityChart, ScoreGauge, SkillCreditChart } from "../charts/Charts";
import { Badge, Button, Card, CountCard, ErrorBanner, ScoreCard, Spinner, levelTone, priorityTone } from "../components/ui";
import { api, errorMessage } from "../services/api";
import { fmtDate, isNum, pct } from "../utils/format";

function SkillTable({ rows, empty }) {
  if (rows.length === 0) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Skill</th><th>Requirement</th><th>Credit</th><th>Why</th></tr></thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.skill} className="border-t border-slate-100 align-top">
              <td className="py-2 font-medium">{m.skill}{m.custom && <span className="ml-1 text-xs text-slate-400">(custom)</span>}</td>
              <td><Badge tone={levelTone[m.level]}>{m.level}</Badge></td>
              <td>{Math.round(m.credit * 100)}%</td>
              <td className="text-slate-600">{m.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AnalysisResult() {
  const { id } = useParams();
  const [a, setA] = useState(null);
  const [resume, setResume] = useState(null);
  const [recs, setRecs] = useState([]);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [ai, setAi] = useState(null);       // { loading, text, status }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const analysis = await api.getAnalysis(id);
        const [extracted, rec] = await Promise.all([api.getExtracted(analysis.resume_id), api.recommendations(id)]);
        if (!cancelled) { setA(analysis); setResume(extracted.data); setRecs(rec.recommendations); }
      } catch (e) { if (!cancelled) setError(errorMessage(e)); }
    })();
    return () => { cancelled = true; };
  }, [id]);

  async function download() {
    setDownloading(true); setError("");
    try {
      const blob = await api.downloadReport(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url; link.download = `resume-analysis-${id}.pdf`;
      document.body.appendChild(link); link.click(); link.remove();
      URL.revokeObjectURL(url);
    } catch (e) { setError("Could not download the report. " + errorMessage(e)); } finally { setDownloading(false); }
  }

  async function explain() {
    setAi({ loading: true });
    try {
      const r = await api.recommendations(id, true);
      setAi({ text: r.ai_summary, status: r.ai_status });
    } catch (e) { setAi({ status: "error" }); }
  }

  if (!a) return error ? <ErrorBanner message={error} /> : <Spinner label="Loading analysis..." />;

  const by = (s) => a.skill_matches.filter((m) => m.status === s);
  const comps = a.component_scores;
  const unknown = Object.entries(comps).filter(([, c]) => c.status === "unknown").map(([k]) => k);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{a.target_role}</h1>
          <p className="text-sm text-slate-500">Analysed {fmtDate(a.created_at)} - method: {a.method}</p>
          {a.details.job_category && (
            <p className="mt-1 text-sm text-slate-600" data-testid="job-category">
              Closest resume category (ML): <span className="font-medium">{a.details.job_category.label}</span>
              {(a.details.job_category.top || []).length > 1 && (
                <span className="text-slate-500"> (also: {a.details.job_category.top.slice(1).map((t) => t.label).join(", ")})</span>
              )}
              <span className="block text-xs text-slate-400">The classifier ({a.details.job_category.model}) was trained on resumes, so this is indicative only.</span>
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/"><Button variant="secondary">Back</Button></Link>
          <Button variant="secondary" onClick={explain} disabled={ai?.loading}>{ai?.loading ? "Asking..." : "AI explanation"}</Button>
          <Button onClick={download} disabled={downloading}>{downloading ? "Preparing PDF..." : "Download PDF report"}</Button>
        </div>
      </div>
      <ErrorBanner message={error} />
      {ai && !ai.loading && (
        <Card title="AI explanation (Gemini)">
          {ai.text ? <p className="whitespace-pre-wrap text-sm text-slate-700">{ai.text}</p>
            : <p className="text-sm text-slate-500">{ai.status === "disabled" ? "Gemini is not configured. This optional feature needs a GEMINI_API_KEY in the backend .env file; everything else works without it." : "The AI explanation could not be generated right now."}</p>}
        </Card>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <ScoreCard testId="quality-score" label="Resume quality" value={a.resume_quality_score} hint="Structure and presentation" />
        <ScoreCard testId="match-score" label="Resume-job match" value={a.match_score} hint="Fit with this job" />
        <ScoreCard testId="coverage-score" label="Skill coverage" value={a.skill_coverage_score} hint="Demonstrated skills" />
        <ScoreCard testId="readiness-score" label="Profile readiness" value={a.profile_readiness_score} hint="Heuristic summary" />
        <CountCard testId="matched-count" label="Matched skills" value={by("matched").length} color="#2f9e44" />
        <CountCard testId="missing-count" label="Missing skills" value={by("missing").length} color="#e03131" />
      </div>
      <p className="text-xs text-slate-500">These percentages describe presentation and fit. They are not the probability of being shortlisted or hired.</p>
      {unknown.length > 0 && <p className="text-sm text-amber-700">Not scored (information missing): {unknown.join(", ")}. They are excluded rather than counted as zero.</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Match score"><ScoreGauge value={a.match_score} label="Match" /></Card>
        <Card title="Matched vs missing skills"><MatchedMissingPie matches={a.skill_matches} /></Card>
        <Card title="Requirement categories"><CategoryChart matches={a.skill_matches} /></Card>
        <Card title="Skill matching" className="lg:col-span-2"><SkillCreditChart matches={a.skill_matches} /></Card>
        <Card title="Match score components"><ComponentChart components={comps} /></Card>
        <Card title="Resume quality by section" className="lg:col-span-3"><QualityChart quality={a.quality} /></Card>
      </div>

      <Card title="Score breakdown">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Component</th><th>Score</th><th>Weight used</th><th>Notes</th></tr></thead>
            <tbody>
              {Object.entries(comps).map(([k, c]) => (
                <tr key={k} className="border-t border-slate-100 align-top">
                  <td className="py-2 font-medium capitalize">{k}</td>
                  <td>{pct(c.score)}</td>
                  <td>{(c.weight_effective * 100).toFixed(0)}%</td>
                  <td className="text-slate-600">{c.notes.join(" ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title={`Matched skills (${by("matched").length})`}><SkillTable rows={by("matched")} empty="No skills are fully matched yet." /></Card>
      <Card title={`Partially matched skills (${by("partial").length})`}><SkillTable rows={by("partial")} empty="No partial matches." /></Card>
      <Card title={`Missing skills (${by("missing").length})`}><SkillTable rows={by("missing")} empty="No missing skills. Great!" /></Card>
      {a.additional_skills.length > 0 && (
        <Card title="Additional skills (not requested by this job)">
          <div className="flex flex-wrap gap-2">{a.additional_skills.map((s) => <Badge key={s} tone="slate">{s}</Badge>)}</div>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Experience analysis">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">{comps.experience.notes.map((n) => <li key={n}>{n}</li>)}</ul>
          {a.details.experience && <p className="mt-2 text-xs text-slate-500">Documented: {a.details.experience.employment_months} month(s) of employment, {a.details.experience.internship_months} month(s) of internship.</p>}
        </Card>
        <Card title="Education analysis">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">{comps.education.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        </Card>
      </div>

      <Card title="Project relevance">
        <p className="mb-2 text-sm text-slate-600">{comps.projects.notes.join(" ")}</p>
        {(a.details.projects || []).length === 0 ? <p className="text-sm text-slate-500">No projects to evaluate.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Project</th><th>Job skills used</th><th>Relevance</th><th>TF-IDF similarity</th></tr></thead>
              <tbody>
                {a.details.projects.map((p) => (
                  <tr key={p.title} className="border-t border-slate-100">
                    <td className="py-2 font-medium">{p.title}</td>
                    <td>{p.matching_skills.join(", ") || "-"}</td>
                    <td><Badge tone={p.relevance === "high" ? "green" : p.relevance === "medium" ? "amber" : "slate"}>{p.relevance}</Badge></td>
                    <td>{isNum(p.tfidf_similarity) ? p.tfidf_similarity.toFixed(2) : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Detected gaps">
        {a.gaps.length === 0 ? <p className="text-sm text-slate-500">No gaps detected.</p> : (
          <ul className="space-y-2 text-sm">
            {a.gaps.map((g, i) => (
              <li key={i} className="flex gap-2"><Badge tone={priorityTone[g.severity === "high" ? "high" : g.severity === "medium" ? "medium" : "low"]}>{g.severity}</Badge><span><span className="font-medium">{g.title}.</span> <span className="text-slate-600">{g.description}</span></span></li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Personalized recommendations">
        {recs.length === 0 ? <p className="text-sm text-slate-500">No recommendations - nothing needs action.</p> : (
          <ol className="space-y-4">
            {recs.map((r, i) => (
              <li key={i} className="rounded-xl border border-slate-100 p-3">
                <div className="flex items-center gap-2"><Badge tone={priorityTone[r.priority]}>{r.priority}</Badge><span className="font-medium">{r.title}</span></div>
                <p className="mt-1 text-sm text-slate-700">{r.action}</p>
                <p className="mt-1 text-xs text-slate-500">Why: {r.reason}</p>
                {r.resources.length > 0 && (
                  <p className="mt-1 text-xs">{r.resources.map((x) => <a key={x.url} className="mr-3 text-brand-600 underline" href={x.url} target="_blank" rel="noreferrer">{x.name}</a>)}</p>
                )}
              </li>
            ))}
          </ol>
        )}
      </Card>

      {resume && (
        <Card title="Extracted resume information">
          <div className="grid gap-4 text-sm md:grid-cols-2">
            <div>
              <h3 className="mb-1 font-semibold">Candidate</h3>
              <p>{resume.personal.full_name || "-"}</p>
              <p className="text-slate-500">{[resume.personal.email, resume.personal.phone].filter(Boolean).join(" | ")}</p>
              <p className="text-slate-500">{[resume.personal.linkedin, resume.personal.github, resume.personal.portfolio].filter(Boolean).join(" | ")}</p>
            </div>
            <div>
              <h3 className="mb-1 font-semibold">Education</h3>
              {resume.education.map((e, i) => <p key={i}>{[e.degree, e.institution, e.graduation_year].filter(Boolean).join(", ")}</p>)}
            </div>
            <div className="md:col-span-2">
              <h3 className="mb-1 font-semibold">Technical skills</h3>
              <div className="flex flex-wrap gap-2">{resume.skills.map((s) => <Badge key={s.name} tone="blue">{s.name}</Badge>)}</div>
            </div>
            <div>
              <h3 className="mb-1 font-semibold">Projects ({resume.projects.length})</h3>
              <ul className="list-disc pl-5">{resume.projects.map((p) => <li key={p.title}>{p.title}</li>)}</ul>
            </div>
            <div>
              <h3 className="mb-1 font-semibold">Experience and internships ({resume.experience.length})</h3>
              {resume.experience.length === 0 ? <p className="text-slate-500">None documented on the resume.</p> :
                <ul className="list-disc pl-5">{resume.experience.map((e, i) => <li key={i}>{[e.title, e.organization].filter(Boolean).join(" at ")} ({e.type})</li>)}</ul>}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
