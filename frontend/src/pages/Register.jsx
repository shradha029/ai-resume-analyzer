import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, ErrorBanner, Field, inputCls } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../services/api";
import { validatePassword } from "../utils/format";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (form.name.trim().length < 2) return setError("Enter your full name.");
    if (!form.email.trim()) return setError("Enter your email.");
    const pwError = validatePassword(form.password);
    if (pwError) return setError(pwError);
    if (form.password !== form.confirm) return setError("Passwords do not match.");
    setBusy(true);
    try {
      await register(form.name.trim(), form.email.trim(), form.password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-white px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-brand-600">Create account</h1>
          <p className="text-sm text-slate-500">Your resumes stay private to your account.</p>
        </div>
        <ErrorBanner message={error} />
        <Field label="Full name"><input className={inputCls} value={form.name} onChange={set("name")} /></Field>
        <Field label="Email"><input className={inputCls} type="email" value={form.email} onChange={set("email")} /></Field>
        <Field label="Password"><input className={inputCls} type="password" value={form.password} onChange={set("password")} /></Field>
        <Field label="Confirm password"><input className={inputCls} type="password" value={form.confirm} onChange={set("confirm")} /></Field>
        <Button type="submit" className="w-full" disabled={busy}>{busy ? "Creating..." : "Register"}</Button>
        <p className="text-center text-sm text-slate-500">Already registered? <Link className="font-medium text-brand-600" to="/login">Log in</Link></p>
      </form>
    </div>
  );
}
