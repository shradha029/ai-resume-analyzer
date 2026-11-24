import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card, ErrorBanner, Field, inputCls, Spinner } from "../components/ui";
import { api, errorMessage } from "../services/api";

const MIN_JD = 40;

export default function NewAnalysis() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [resumes, setResumes] = useState(null);
  const [roles, setRoles] = useState([]);
  const [resumeId, setResumeId] = useState(params.get("resume") || "");
  const [roleChoice, setRoleChoice] = useState("");
  const [customRole, setCustomRole] = useState("");
  const [jd, setJd] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.listResumes().then((r) => {
      setResumes(r);
      setResumeId((cur) => cur || (r[0] ? String(r[0].id) : ""));
    }).catch((e) => setError(errorMessage(e)));
    api.roles().then(setRoles).catch(() => setRoles([]));
  }, []);

  const role = roleChoice === "__custom" ? customRole.trim() : roleChoice;

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!resumeId) return setError("Upload and select a resume first.");
    if (role.length < 2) return setError("Select a target role or enter a custom one.");
    if (jd.trim().length < MIN_JD) return setError(`Paste the full job description (at least ${MIN_JD} characters).`);
    try {
      setBusy("Analysing the job description...");
      const job = await api.analyzeJob({ target_role: role, job_description: jd.trim() });
      setBusy("Matching your resume against the job...");
      const analysis = await api.createAnalysis({ resume_id: Number(resumeId), job_id: job.id });
      navigate(`/analysis/${analysis.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy("");
    }
  }

  if (resumes === null && !error) return <Spinner />;
  return (
    <form onSubmit={submit} className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">New analysis</h1>
      <ErrorBanner message={error} />
      <Card title="1. Choose your resume">
        {resumes?.length === 0 ? (
          <p className="text-sm text-slate-500">You have no resumes yet. <Link className="font-medium text-brand-600" to="/resumes">Upload one first.</Link></p>
        ) : (
          <Field label="Resume">
            <select className={inputCls} value={resumeId} onChange={(e) => setResumeId(e.target.value)}>
              {resumes?.map((r) => <option key={r.id} value={r.id}>{r.original_filename} (#{r.id}, {r.status})</option>)}
            </select>
          </Field>
        )}
      </Card>
      <Card title="2. Target job role">
        <Field label="Role">
          <select className={inputCls} value={roleChoice} onChange={(e) => setRoleChoice(e.target.value)}>
            <option value="">Select a role...</option>
            {roles.map((r) => <option key={r} value={r}>{r}</option>)}
            <option value="__custom">Other (enter my own)</option>
          </select>
        </Field>
        {roleChoice === "__custom" && (
          <div className="mt-3"><Field label="Custom role title"><input className={inputCls} value={customRole} onChange={(e) => setCustomRole(e.target.value)} maxLength={100} /></Field></div>
        )}
      </Card>
      <Card title="3. Job description">
        <Field label="Paste the complete job description">
          <textarea className={inputCls} rows={12} value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Requirements, preferred skills, experience, education..." />
        </Field>
        <p className="mt-1 text-xs text-slate-500">{jd.trim().length} characters. Mandatory vs preferred skills are detected from headings and wording like "preferred" or "nice to have".</p>
      </Card>
      <Button type="submit" disabled={!!busy}>{busy ? "Working..." : "Run analysis"}</Button>
      {busy && <Spinner label={busy} />}
    </form>
  );
}
