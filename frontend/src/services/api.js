import axios from "axios";

export const TOKEN_KEY = "ra_token";

// Requests go to /api/... ; in development Vite proxies them to the FastAPI backend.
const http = axios.create({ baseURL: import.meta.env.VITE_API_URL || "" });

http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !String(err.config?.url).includes("/api/auth/login")) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event("auth:expired"));
    }
    return Promise.reject(err);
  }
);

/** Turn any axios/FastAPI error into one readable sentence. */
export function errorMessage(err) {
  const d = err?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (x.msg || "").replace(/^Value error, /, "")).filter(Boolean).join("; ");
  if (err?.code === "ERR_NETWORK") return "Cannot reach the server. Is the backend running on port 8000?";
  return err?.message || "Something went wrong";
}

const data = (p) => p.then((r) => r.data);

export const api = {
  register: (body) => data(http.post("/api/auth/register", body)),
  login: (body) => data(http.post("/api/auth/login", body)),
  logout: () => data(http.post("/api/auth/logout")),
  me: () => data(http.get("/api/auth/me")),

  uploadResume: (file) => {
    const form = new FormData();
    form.append("file", file);
    return data(http.post("/api/resumes/upload", form));
  },
  listResumes: () => data(http.get("/api/resumes")),
  deleteResume: (id) => http.delete(`/api/resumes/${id}`),
  extractResume: (id) => data(http.post(`/api/resumes/${id}/extract`)),
  getExtracted: (id) => data(http.get(`/api/resumes/${id}/extracted`)),
  saveExtracted: (id, body) => data(http.put(`/api/resumes/${id}/extracted`, body)),

  mlInfo: () => data(http.get("/api/ml/info")),
  roles: () => data(http.get("/api/jobs/roles")),
  analyzeJob: (body) => data(http.post("/api/jobs/analyze", body)),

  createAnalysis: (body) => data(http.post("/api/analysis/create", body)),
  getAnalysis: (id) => data(http.get(`/api/analysis/${id}`)),
  history: () => data(http.get("/api/analysis/history")),
  recommendations: (id, ai = false) => data(http.get(`/api/analysis/${id}/recommendations`, { params: { ai } })),
  deleteAnalysis: (id) => http.delete(`/api/analysis/${id}`),
  downloadReport: (id) => http.get(`/api/reports/${id}/download`, { responseType: "blob" }).then((r) => r.data),
};
