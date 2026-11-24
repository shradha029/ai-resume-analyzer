import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge, Button, Card, ErrorBanner, Field, inputCls, Spinner } from "../components/ui";
import { api, errorMessage } from "../services/api";
import { commas, lines, numOrNull } from "../utils/format";

const CATEGORIES = ["language", "framework", "library", "database", "tool", "cloud", "ml", "concept"];
const text = (v) => (v === null || v === undefined ? "" : String(v));

function Row({ children }) {
  return <div className="grid gap-3 sm:grid-cols-2">{children}</div>;
}

export default function ResumeReview() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [edited, setEdited] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [saving, setSaving] = useState(false);
  const [newSkill, setNewSkill] = useState({ name: "", category: "tool" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        let res;
        try { res = await api.getExtracted(id); } catch (e) {
          if (e.response?.status !== 404) throw e;
          res = await api.extractResume(id);      // not extracted yet
        }
        if (!cancelled) { setData(res.data); setEdited(res.is_user_edited); }
      } catch (e) { if (!cancelled) setError(errorMessage(e)); }
    })();
    return () => { cancelled = true; };
  }, [id]);

  const change = (fn) => { setData((d) => fn(structuredClone(d))); setSaved(""); };
  const setPersonal = (k, v) => change((d) => { d.personal[k] = v; return d; });
  const setItem = (list, i, patch) => change((d) => { Object.assign(d[list][i], patch); return d; });
  const addItem = (list, blank) => change((d) => { d[list].push(blank); return d; });
  const removeItem = (list, i) => change((d) => { d[list].splice(i, 1); return d; });

  async function save() {
    setSaving(true); setError(""); setSaved("");
    try {
      const payload = structuredClone(data);
      Object.keys(payload.personal).forEach((k) => { payload.personal[k] = (payload.personal[k] || "").trim() || null; });
      const res = await api.saveExtracted(id, payload);
      setData(res.data); setEdited(true); setSaved("Changes saved.");
    } catch (e) { setError(errorMessage(e)); } finally { setSaving(false); }
  }

  if (!data) return error ? <ErrorBanner message={error} /> : <Spinner label="Reading your resume..." />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Review extracted information</h1>
          <p className="text-sm text-slate-500">Automatic extraction can make mistakes. Fix anything that is wrong before you analyse.</p>
        </div>
        <div className="flex items-center gap-2">
          {edited && <Badge tone="violet">edited by you</Badge>}
          <Button variant="secondary" onClick={save} disabled={saving}>{saving ? "Saving..." : "Save changes"}</Button>
          <Link to={`/analyze?resume=${id}`}><Button>Continue to job target</Button></Link>
        </div>
      </div>
      <ErrorBanner message={error} />
      {saved && <div role="status" className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{saved}</div>}
      {data.warnings.length > 0 && (
        <Card title="Extraction notes">
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-700">{data.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </Card>
      )}

      <Card title="Personal information">
        <Row>
          {[["full_name", "Full name"], ["email", "Email"], ["phone", "Phone"], ["linkedin", "LinkedIn"], ["github", "GitHub"], ["portfolio", "Portfolio"]].map(([k, label]) => (
            <Field key={k} label={label}><input className={inputCls} value={text(data.personal[k])} onChange={(e) => setPersonal(k, e.target.value)} /></Field>
          ))}
        </Row>
      </Card>

      <Card title="Education" right={<Button variant="secondary" onClick={() => addItem("education", { degree: "", institution: "", graduation_year: null, cgpa: null, cgpa_scale: null, percentage: null, coursework: [] })}>Add</Button>}>
        {data.education.length === 0 && <p className="text-sm text-slate-500">No education detected.</p>}
        {data.education.map((e, i) => (
          <div key={i} className="mb-4 space-y-3 rounded-xl border border-slate-100 p-3">
            <Row>
              <Field label="Degree"><input className={inputCls} value={text(e.degree)} onChange={(ev) => setItem("education", i, { degree: ev.target.value })} /></Field>
              <Field label="College / university"><input className={inputCls} value={text(e.institution)} onChange={(ev) => setItem("education", i, { institution: ev.target.value })} /></Field>
              <Field label="Graduation year"><input className={inputCls} type="number" value={text(e.graduation_year)} onChange={(ev) => setItem("education", i, { graduation_year: numOrNull(ev.target.value) })} /></Field>
              <Field label="CGPA"><input className={inputCls} type="number" step="0.01" value={text(e.cgpa)} onChange={(ev) => setItem("education", i, { cgpa: numOrNull(ev.target.value) })} /></Field>
              <Field label="Percentage"><input className={inputCls} type="number" step="0.1" value={text(e.percentage)} onChange={(ev) => setItem("education", i, { percentage: numOrNull(ev.target.value) })} /></Field>
              <Field label="Relevant coursework (comma separated)"><input className={inputCls} value={e.coursework.join(", ")} onChange={(ev) => setItem("education", i, { coursework: commas(ev.target.value) })} /></Field>
            </Row>
            <Button variant="danger" onClick={() => removeItem("education", i)}>Remove</Button>
          </div>
        ))}
      </Card>

      <Card title={`Technical skills (${data.skills.length})`}>
        <div className="flex flex-wrap gap-2">
          {data.skills.map((s, i) => (
            <span key={s.name} className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700">
              {s.name} <span className="text-xs text-slate-400">{s.category}</span>
              <button aria-label={`Remove ${s.name}`} className="ml-1 text-slate-400 hover:text-red-600" onClick={() => removeItem("skills", i)}>x</button>
            </span>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-end gap-2">
          <Field label="Add a skill"><input className={inputCls} value={newSkill.name} onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })} /></Field>
          <Field label="Category"><select className={inputCls} value={newSkill.category} onChange={(e) => setNewSkill({ ...newSkill, category: e.target.value })}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select></Field>
          <Button variant="secondary" onClick={() => {
            const name = newSkill.name.trim();
            if (!name || data.skills.some((s) => s.name.toLowerCase() === name.toLowerCase())) return;
            addItem("skills", { name, category: newSkill.category, found_in: ["skills"] });
            setNewSkill({ ...newSkill, name: "" });
          }}>Add skill</Button>
        </div>
      </Card>

      <Card title="Experience and internships" right={<Button variant="secondary" onClick={() => addItem("experience", { organization: "", title: "", duration: "", type: "internship", responsibilities: [], technologies: [] })}>Add</Button>}>
        {data.experience.length === 0 && <p className="text-sm text-slate-500">No professional experience or internship detected. Academic projects are listed separately below.</p>}
        {data.experience.map((e, i) => (
          <div key={i} className="mb-4 space-y-3 rounded-xl border border-slate-100 p-3">
            <Row>
              <Field label="Organization"><input className={inputCls} value={text(e.organization)} onChange={(ev) => setItem("experience", i, { organization: ev.target.value })} /></Field>
              <Field label="Job title"><input className={inputCls} value={text(e.title)} onChange={(ev) => setItem("experience", i, { title: ev.target.value })} /></Field>
              <Field label="Duration"><input className={inputCls} value={text(e.duration)} onChange={(ev) => setItem("experience", i, { duration: ev.target.value })} /></Field>
              <Field label="Type"><select className={inputCls} value={e.type} onChange={(ev) => setItem("experience", i, { type: ev.target.value })}><option value="internship">internship</option><option value="employment">employment</option></select></Field>
              <Field label="Technologies (comma separated)"><input className={inputCls} value={e.technologies.join(", ")} onChange={(ev) => setItem("experience", i, { technologies: commas(ev.target.value) })} /></Field>
            </Row>
            <Field label="Responsibilities (one per line)"><textarea className={inputCls} rows={3} value={e.responsibilities.join("\n")} onChange={(ev) => setItem("experience", i, { responsibilities: lines(ev.target.value) })} /></Field>
            <Button variant="danger" onClick={() => removeItem("experience", i)}>Remove</Button>
          </div>
        ))}
      </Card>

      <Card title="Projects" right={<Button variant="secondary" onClick={() => addItem("projects", { title: "", description: "", technologies: [] })}>Add</Button>}>
        {data.projects.length === 0 && <p className="text-sm text-slate-500">No projects detected.</p>}
        {data.projects.map((p, i) => (
          <div key={i} className="mb-4 space-y-3 rounded-xl border border-slate-100 p-3">
            <Row>
              <Field label="Project title"><input className={inputCls} value={p.title} onChange={(ev) => setItem("projects", i, { title: ev.target.value })} /></Field>
              <Field label="Technologies (comma separated)"><input className={inputCls} value={p.technologies.join(", ")} onChange={(ev) => setItem("projects", i, { technologies: commas(ev.target.value) })} /></Field>
            </Row>
            <Field label="Description (one bullet per line)"><textarea className={inputCls} rows={3} value={p.description} onChange={(ev) => setItem("projects", i, { description: ev.target.value })} /></Field>
            <Button variant="danger" onClick={() => removeItem("projects", i)}>Remove</Button>
          </div>
        ))}
      </Card>

      <Card title="Certifications" right={<Button variant="secondary" onClick={() => addItem("certifications", { name: "", issuer: "", date: "" })}>Add</Button>}>
        {data.certifications.length === 0 && <p className="text-sm text-slate-500">No certifications detected.</p>}
        {data.certifications.map((c, i) => (
          <div key={i} className="mb-3 grid items-end gap-3 sm:grid-cols-[2fr_2fr_1fr_auto]">
            <Field label="Name"><input className={inputCls} value={c.name} onChange={(ev) => setItem("certifications", i, { name: ev.target.value })} /></Field>
            <Field label="Issuer"><input className={inputCls} value={text(c.issuer)} onChange={(ev) => setItem("certifications", i, { issuer: ev.target.value || null })} /></Field>
            <Field label="Date"><input className={inputCls} value={text(c.date)} onChange={(ev) => setItem("certifications", i, { date: ev.target.value || null })} /></Field>
            <Button variant="danger" onClick={() => removeItem("certifications", i)}>Remove</Button>
          </div>
        ))}
      </Card>

      <Card title="Achievements, publications and activities">
        <div className="grid gap-3 md:grid-cols-3">
          {[["achievements", "Achievements"], ["publications", "Publications"], ["extracurricular", "Extracurricular"]].map(([k, label]) => (
            <Field key={k} label={`${label} (one per line)`}><textarea className={inputCls} rows={4} value={data[k].join("\n")} onChange={(ev) => change((d) => { d[k] = lines(ev.target.value); return d; })} /></Field>
          ))}
        </div>
      </Card>
    </div>
  );
}
