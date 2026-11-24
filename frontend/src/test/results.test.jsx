import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import AnalysisResult from "../pages/AnalysisResult";
import { api } from "../services/api";
import { renderAt } from "./helpers";
import analysisFx from "./fixtures/analysis.json";
import extractedFx from "./fixtures/extracted.json";
import recsFx from "./fixtures/recommendations.json";

vi.mock("../services/api", async () => (await import("./apiMock.js")).default());

const open = (analysis = analysisFx) => {
  api.getAnalysis.mockResolvedValue(analysis);
  api.getExtracted.mockResolvedValue(extractedFx);
  api.recommendations.mockResolvedValue(recsFx);
  renderAt(<AnalysisResult />, { path: "/analysis/1", route: "/analysis/:id" });
};
const count = (s) => analysisFx.skill_matches.filter((m) => m.status === s).length;

describe("analysis dashboard", () => {
  it("shows the real scores returned by the backend (no hardcoded numbers)", async () => {
    open();
    await screen.findByText("Backend Developer");
    expect(screen.getByTestId("match-score")).toHaveTextContent(`${analysisFx.match_score.toFixed(1)}%`);
    expect(screen.getByTestId("quality-score")).toHaveTextContent(`${analysisFx.resume_quality_score.toFixed(1)}%`);
    expect(screen.getByTestId("coverage-score")).toHaveTextContent(`${analysisFx.skill_coverage_score.toFixed(1)}%`);
    expect(screen.getByTestId("matched-count")).toHaveTextContent(String(count("matched")));
    expect(screen.getByTestId("missing-count")).toHaveTextContent(String(count("missing")));
    expect(screen.getByText(/not the probability of being shortlisted or hired/i)).toBeInTheDocument();
  });

  it("renders every required chart with data", async () => {
    open();
    await screen.findByText("Backend Developer");
    for (const label of ["Match gauge", "Skill matching bar chart", "Matched vs missing skills chart",
      "Requirement category comparison chart", "Resume section completeness chart", "Match score components chart"]) {
      const chart = screen.getByRole("img", { name: label });
      await waitFor(() => expect(chart.querySelector("svg")).not.toBeNull());
    }
  });

  it("lists matched, partial and missing skills with explanations", async () => {
    open();
    await screen.findByText("Backend Developer");
    const missing = screen.getByText(/^Missing skills \(/).closest("section");
    expect(within(missing).getByText("JWT")).toBeInTheDocument();
    const matched = screen.getByText(/^Matched skills \(/).closest("section");
    expect(within(matched).getByText("Python")).toBeInTheDocument();
    const partial = screen.getByText(/^Partially matched skills \(/).closest("section");
    expect(within(partial).getByText("Django")).toBeInTheDocument();
    expect(within(partial).getAllByText(/Flask/).length).toBeGreaterThan(0);
  });

  it("shows gaps, recommendations with resource links, extracted data and project relevance", async () => {
    open();
    await screen.findByText("Backend Developer");
    expect(screen.getByText("Learn JWT")).toBeInTheDocument();
    const link = screen.getAllByRole("link", { name: /JWT/ })[0];
    expect(link).toHaveAttribute("href", expect.stringMatching(/^https:\/\//));
    expect(screen.getByText("Aarav Sharma")).toBeInTheDocument();
    expect(screen.getAllByText("Smart Attendance System").length).toBeGreaterThanOrEqual(2);   // project table + extracted info
    expect(screen.getByText(/None documented on the resume/)).toBeInTheDocument();      // student: no experience
    expect(screen.getByText("Project relevance")).toBeInTheDocument();
  });

  it("marks unknown components as unknown instead of zero", async () => {
    const unknown = structuredClone(analysisFx);
    unknown.match_score = null;
    unknown.component_scores.education = { ...unknown.component_scores.education, score: null, status: "unknown" };
    open(unknown);
    await screen.findByText("Backend Developer");
    expect(screen.getByTestId("match-score")).toHaveTextContent("Unknown");
    expect(screen.getByText(/Not scored \(information missing\): education/)).toBeInTheDocument();
  });

  it("shows an error if the analysis cannot be loaded", async () => {
    api.getAnalysis.mockRejectedValue({ response: { status: 404, data: { detail: "Analysis not found" } } });
    renderAt(<AnalysisResult />, { path: "/analysis/99", route: "/analysis/:id" });
    expect(await screen.findByRole("alert")).toHaveTextContent("Analysis not found");
  });
});

describe("predicted job category", () => {
  it("is shown when the ML classifier produced one and hidden otherwise", async () => {
    const withCat = structuredClone(analysisFx);
    withCat.details.job_category = { label: "Backend Developer", model: "linear_svm", top: [] };
    open(withCat);
    expect(await screen.findByTestId("job-category")).toHaveTextContent("Backend Developer");
  });

  it("is absent when no model is trained", async () => {
    open();
    await screen.findByText("Backend Developer");
    expect(screen.queryByTestId("job-category")).toBeNull();
  });
});

describe("PDF report download and AI explanation", () => {
  it("downloads the PDF report through the API", async () => {
    const blob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    api.downloadReport.mockResolvedValue(blob);
    URL.createObjectURL = vi.fn(() => "blob:fake");
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Download PDF report" }));
    await waitFor(() => expect(api.downloadReport).toHaveBeenCalledWith("1"));
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
    expect(click).toHaveBeenCalled();
    click.mockRestore();
  });

  it("shows a clear message when the download fails", async () => {
    api.downloadReport.mockRejectedValue({ response: { status: 500, data: { detail: "boom" } } });
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Download PDF report" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not download the report");
  });

  it("explains that Gemini is optional when it is not configured", async () => {
    open();
    api.recommendations.mockResolvedValueOnce({ ...recsFx }).mockResolvedValue({ recommendations: recsFx.recommendations, ai_summary: null, ai_status: "disabled" });
    await userEvent.click(await screen.findByRole("button", { name: "AI explanation" }));
    expect(await screen.findByText(/Gemini is not configured/)).toBeInTheDocument();
  });

  it("shows the AI summary when Gemini returns one", async () => {
    open();
    api.recommendations.mockResolvedValue({ recommendations: recsFx.recommendations, ai_summary: "Focus on JWT first.", ai_status: "ok" });
    await userEvent.click(await screen.findByRole("button", { name: "AI explanation" }));
    expect(await screen.findByText("Focus on JWT first.")).toBeInTheDocument();
  });
});
