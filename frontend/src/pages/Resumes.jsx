import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Badge, Button, Card, ErrorBanner, Spinner } from "../components/ui";
import { api, errorMessage } from "../services/api";
import { fmtDate, MAX_UPLOAD_MB, validatePdf } from "../utils/format";

export default function Resumes() {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");       // "", uploading, extracting
  const [error, setError] = useState("");
  const [resumes, setResumes] = useState(null);

  const load = () => api.listResumes().then(setResumes).catch((e) => setError(errorMessage(e)));
  useEffect(() => { load(); }, []);

  function onPick(e) {
    const f = e.target.files?.[0] || null;
    setFile(f);
    setError(f ? validatePdf(f) || "" : "");
  }

  async function upload() {
    const problem = validatePdf(file);
    if (problem) return setError(problem);
    setError("");
    try {
      setStatus("uploading");
      const resume = await api.uploadResume(file);
      setStatus("extracting");
      await api.extractResume(resume.id);
      navigate(`/resumes/${resume.id}`);
    } catch (e) {
      setError(errorMessage(e));
      setStatus("");
      load();
    }
  }

  async function remove(id) {
    if (!window.confirm("Delete this resume, its extracted data and its analyses?")) return;
    try { await api.deleteResume(id); load(); } catch (e) { setError(errorMessage(e)); }
  }

  const busy = status !== "";
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Resumes</h1>
      <Card title="Upload a resume (PDF)">
        <ErrorBanner message={error} />
        <div className="flex flex-col items-start gap-3 rounded-xl border-2 border-dashed border-brand-100 bg-brand-50/40 p-6">
          <input ref={inputRef} type="file" accept="application/pdf,.pdf" onChange={onPick} disabled={busy} aria-label="Resume PDF file" className="text-sm" />
          <p className="text-xs text-slate-500">Text-based PDF only, up to {MAX_UPLOAD_MB} MB. Scanned (image-only) PDFs are not supported yet.</p>
          {file && <p className="text-sm"><span className="font-medium">Selected:</span> {file.name} <span className="text-slate-500">({(file.size / 1024).toFixed(0)} KB)</span></p>}
          <Button onClick={upload} disabled={!file || busy}>{busy ? "Working..." : "Upload and analyse"}</Button>
          {status === "uploading" && <Spinner label="Uploading..." />}
          {status === "extracting" && <Spinner label="Extracting information from your resume..." />}
        </div>
      </Card>
      <Card title="Your resumes">
        {resumes === null && <Spinner />}
        {resumes?.length === 0 && <p className="py-4 text-sm text-slate-500">No resumes uploaded yet.</p>}
        {resumes?.length > 0 && (
          <ul className="divide-y divide-slate-100">
            {resumes.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                <div>
                  <div className="font-medium">{r.original_filename}</div>
                  <div className="text-xs text-slate-500">{r.page_count} page(s) - {fmtDate(r.uploaded_at)}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={r.status === "extracted" ? "green" : "amber"}>{r.status}</Badge>
                  <Link to={`/resumes/${r.id}`}><Button variant="secondary">Review</Button></Link>
                  <Link to={`/analyze?resume=${r.id}`}><Button>Analyse</Button></Link>
                  <Button variant="danger" onClick={() => remove(r.id)}>Delete</Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
