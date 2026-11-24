import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ResumeReview from "../pages/ResumeReview";
import { api } from "../services/api";
import { renderAt } from "./helpers";
import extractedFx from "./fixtures/extracted.json";

vi.mock("../services/api", async () => (await import("./apiMock.js")).default());

const open = () => {
  api.getExtracted.mockResolvedValue(structuredClone(extractedFx));
  renderAt(<ResumeReview />, { path: "/resumes/1", route: "/resumes/:id" });
};

describe("review extracted information", () => {
  it("shows what was extracted, including that there is no experience", async () => {
    open();
    expect(await screen.findByDisplayValue("Aarav Sharma")).toBeInTheDocument();
    expect(screen.getByDisplayValue("aarav.sharma@example.com")).toBeInTheDocument();
    expect(screen.getByText(/No professional experience or internship detected/)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Smart Attendance System")).toBeInTheDocument();
  });

  it("saves user corrections to the backend", async () => {
    api.saveExtracted.mockImplementation(async (_id, body) => ({ ...extractedFx, data: body, is_user_edited: true }));
    open();
    const name = await screen.findByDisplayValue("Aarav Sharma");
    await userEvent.clear(name);
    await userEvent.type(name, "Aarav K. Sharma");
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(api.saveExtracted).toHaveBeenCalled());
    const [id, body] = api.saveExtracted.mock.calls[0];
    expect(id).toBe("1");
    expect(body.personal.full_name).toBe("Aarav K. Sharma");
    expect(body.skills.length).toBe(extractedFx.data.skills.length);
    expect(await screen.findByText("Changes saved.")).toBeInTheDocument();
    expect(screen.getByText("edited by you")).toBeInTheDocument();
  });

  it("can remove and add skills", async () => {
    api.saveExtracted.mockImplementation(async (_id, body) => ({ ...extractedFx, data: body, is_user_edited: true }));
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Remove Docker" }));
    await userEvent.type(screen.getByLabelText("Add a skill"), "Kafka");
    await userEvent.click(screen.getByRole("button", { name: "Add skill" }));
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(api.saveExtracted).toHaveBeenCalled());
    const names = api.saveExtracted.mock.calls[0][1].skills.map((s) => s.name);
    expect(names).not.toContain("Docker");
    expect(names).toContain("Kafka");
  });

  it("shows validation errors returned by the backend", async () => {
    api.saveExtracted.mockRejectedValue({ response: { status: 422, data: { detail: [{ msg: "Input should be less than or equal to 100" }] } } });
    open();
    await userEvent.click(await screen.findByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("less than or equal to 100");
  });

  it("extracts automatically if the resume was never extracted", async () => {
    api.getExtracted.mockRejectedValue({ response: { status: 404, data: { detail: "not extracted" } } });
    api.extractResume.mockResolvedValue(structuredClone(extractedFx));
    renderAt(<ResumeReview />, { path: "/resumes/1", route: "/resumes/:id" });
    expect(await screen.findByDisplayValue("Aarav Sharma")).toBeInTheDocument();
    expect(api.extractResume).toHaveBeenCalledWith("1");
  });
});
