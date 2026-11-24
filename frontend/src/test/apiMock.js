import { vi } from "vitest";

const NAMES = ["register", "login", "logout", "me", "uploadResume", "listResumes", "deleteResume", "extractResume",
  "getExtracted", "saveExtracted", "roles", "analyzeJob", "createAnalysis", "getAnalysis", "history",
  "recommendations", "deleteAnalysis", "downloadReport", "mlInfo"];

export default async function factory() {
  const actual = await vi.importActual("../services/api");
  return { ...actual, api: Object.fromEntries(NAMES.map((n) => [n, vi.fn()])) };
}
