import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Resumes from "../pages/Resumes";
import { api } from "../services/api";
import { renderAt } from "./helpers";
import resumeFx from "./fixtures/resume.json";

vi.mock("../services/api", async () => (await import("./apiMock.js")).default());

const user = userEvent.setup({ applyAccept: false });
const pdf = (name = "my_resume.pdf", size = 2000) => new File([new Uint8Array(size)], name, { type: "application/pdf" });
const open = () => {
  api.listResumes.mockResolvedValue([]);
  renderAt(<Resumes />, { path: "/resumes", route: "/resumes", extra: ["/resumes/:id"] });
};

describe("resume upload", () => {
  it("rejects non-PDF files before any request", async () => {
    open();
    await user.upload(screen.getByLabelText("Resume PDF file"), new File(["hello"], "notes.txt", { type: "text/plain" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Only PDF files are accepted");
    expect(api.uploadResume).not.toHaveBeenCalled();
  });

  it("rejects files larger than the limit", async () => {
    open();
    await user.upload(screen.getByLabelText("Resume PDF file"), pdf("big.pdf", 6 * 1024 * 1024));
    expect(screen.getByRole("alert")).toHaveTextContent("too large");
  });

  it("shows the file name, uploads, extracts and opens the review page", async () => {
    api.uploadResume.mockResolvedValue(resumeFx);
    api.extractResume.mockResolvedValue({});
    open();
    const file = pdf();
    await user.upload(screen.getByLabelText("Resume PDF file"), file);
    expect(screen.getByText("my_resume.pdf")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /upload and analyse/i }));
    await waitFor(() => expect(screen.getByText("navigated:/resumes/:id")).toBeInTheDocument());
    expect(api.uploadResume).toHaveBeenCalledWith(file);
    expect(api.extractResume).toHaveBeenCalledWith(resumeFx.id);
  });

  it("shows the backend message for scanned/corrupt/encrypted PDFs", async () => {
    api.uploadResume.mockRejectedValue({ response: { status: 422, data: { detail: "No selectable text found. This looks like an empty or scanned PDF." } } });
    open();
    await user.upload(screen.getByLabelText("Resume PDF file"), pdf());
    await user.click(screen.getByRole("button", { name: /upload and analyse/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("empty or scanned PDF");
    expect(api.extractResume).not.toHaveBeenCalled();
  });

  it("lists uploaded resumes and deletes one", async () => {
    api.listResumes.mockResolvedValue([resumeFx]);
    api.deleteResume.mockResolvedValue({});
    renderAt(<Resumes />, { path: "/resumes", route: "/resumes" });
    expect(await screen.findByText(resumeFx.original_filename)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(api.deleteResume).toHaveBeenCalledWith(resumeFx.id));
  });
});
