export const isNum = (v) => typeof v === "number" && !Number.isNaN(v);
export const pct = (v) => (isNum(v) ? `${v.toFixed(1)}%` : "Unknown");
export const scoreColor = (v) => (!isNum(v) ? "#adb5bd" : v >= 75 ? "#2f9e44" : v >= 50 ? "#f08c00" : "#e03131");
export const fmtDate = (s) => (s ? new Date(s).toLocaleString() : "");
export const statusColors = { matched: "#2f9e44", partial: "#f59f00", missing: "#e03131" };
export const MAX_UPLOAD_MB = 5;

export function validatePdf(file) {
  if (!file) return "Choose a file first.";
  if (!file.name.toLowerCase().endsWith(".pdf")) return "Only PDF files are accepted.";
  if (file.size === 0) return "The selected file is empty.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `File is too large. Maximum is ${MAX_UPLOAD_MB} MB.`;
  return null;
}

export function validatePassword(pw) {
  if (pw.length < 8 || pw.length > 64) return "Password must be 8-64 characters.";
  if (!/[A-Za-z]/.test(pw) || !/\d/.test(pw)) return "Password needs at least one letter and one digit.";
  return null;
}

export const lines = (s) => s.split("\n").map((x) => x.trim()).filter(Boolean);
export const commas = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
export const numOrNull = (s) => (s === "" || s === null || s === undefined || Number.isNaN(Number(s)) ? null : Number(s));
