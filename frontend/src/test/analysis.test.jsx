import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import NewAnalysis from "../pages/NewAnalysis";
import { api } from "../services/api";
import { renderAt } from "./helpers";
import analysisFx from "./fixtures/analysis.json";
import jobFx from "./fixtures/job.json";
import resumeFx from "./fixtures/resume.json";
import roles from "./fixtures/roles.json";

vi.mock("../services/api", async () => (await import("./apiMock.js")).default());

const JD = "Requirements: Strong proficiency in Python and FastAPI. Experience with PostgreSQL and REST APIs. Bachelor's degree.";
const open = () => {
  api.listResumes.mockResolvedValue([resumeFx]);
  api.roles.mockResolvedValue(roles);
  renderAt(<NewAnalysis />, { path: "/analyze", route: "/analyze", extra: ["/analysis/:id"] });
};

describe("job targeting form", () => {
  it("offers the predefined roles and a custom option", async () => {
    open();
    const select = await screen.findByLabelText("Role");
    for (const r of ["Software Developer", "Data Scientist", "Machine Learning Engineer", "Java Developer"]) {
      expect(screen.getByRole("option", { name: r })).toBeInTheDocument();
    }
    await userEvent.selectOptions(select, "__custom");
    expect(screen.getByLabelText("Custom role title")).toBeInTheDocument();
  });

  it("validates role and job description length before calling the API", async () => {
    open();
    await screen.findByLabelText("Role");
    await userEvent.click(screen.getByRole("button", { name: "Run analysis" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Select a target role");
    await userEvent.selectOptions(screen.getByLabelText("Role"), "Backend Developer");
    await userEvent.type(screen.getByLabelText(/paste the complete job description/i), "too short");
    await userEvent.click(screen.getByRole("button", { name: "Run analysis" }));
    expect(screen.getByRole("alert")).toHaveTextContent("at least 40 characters");
    expect(api.analyzeJob).not.toHaveBeenCalled();
  });

  it("analyses the job, creates the analysis and opens the results", async () => {
    api.analyzeJob.mockResolvedValue(jobFx);
    api.createAnalysis.mockResolvedValue(analysisFx);
    open();
    await screen.findByLabelText("Role");
    await userEvent.selectOptions(screen.getByLabelText("Role"), "Backend Developer");
    await userEvent.click(screen.getByLabelText(/paste the complete job description/i));
    await userEvent.paste(JD);
    await userEvent.click(screen.getByRole("button", { name: "Run analysis" }));
    await waitFor(() => expect(screen.getByText("navigated:/analysis/:id")).toBeInTheDocument());
    expect(api.analyzeJob).toHaveBeenCalledWith({ target_role: "Backend Developer", job_description: JD });
    expect(api.createAnalysis).toHaveBeenCalledWith({ resume_id: resumeFx.id, job_id: jobFx.id });
  });

  it("supports a completely custom job title", async () => {
    api.analyzeJob.mockResolvedValue(jobFx);
    api.createAnalysis.mockResolvedValue(analysisFx);
    open();
    await userEvent.selectOptions(await screen.findByLabelText("Role"), "__custom");
    await userEvent.type(screen.getByLabelText("Custom role title"), "Quantum Plumber");
    await userEvent.click(screen.getByLabelText(/paste the complete job description/i));
    await userEvent.paste(JD);
    await userEvent.click(screen.getByRole("button", { name: "Run analysis" }));
    await waitFor(() => expect(api.analyzeJob).toHaveBeenCalledWith({ target_role: "Quantum Plumber", job_description: JD }));
  });

  it("shows API errors (e.g. resume not extracted) instead of failing silently", async () => {
    api.analyzeJob.mockResolvedValue(jobFx);
    api.createAnalysis.mockRejectedValue({ response: { status: 409, data: { detail: "Extract the resume first" } } });
    open();
    await userEvent.selectOptions(await screen.findByLabelText("Role"), "Backend Developer");
    await userEvent.click(screen.getByLabelText(/paste the complete job description/i));
    await userEvent.paste(JD);
    await userEvent.click(screen.getByRole("button", { name: "Run analysis" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Extract the resume first");
  });
});
