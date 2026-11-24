import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "../pages/Home";
import { api } from "../services/api";
import { renderAt } from "./helpers";
import loginFx from "./fixtures/login.json";
import history from "./fixtures/history.json";

vi.mock("../services/api", async () => (await import("./apiMock.js")).default());

const UNTRAINED = { role_classifier: { trained: false, message: "x", metrics: null } };

describe("dashboard home", () => {
  beforeEach(() => api.mlInfo.mockResolvedValue(UNTRAINED));

  it("shows the greeting and the analysis history from the backend", async () => {
    api.history.mockResolvedValue(history);
    api.me.mockResolvedValue(loginFx.user);
    renderAt(<Home />, { path: "/", route: "/", loggedIn: true });
    expect(await screen.findByText("Backend Developer")).toBeInTheDocument();
    expect(screen.getByText(`${history[0].match_score.toFixed(1)}%`)).toBeInTheDocument();
    expect(screen.getByText(history[0].resume_filename)).toBeInTheDocument();
    expect(await screen.findByText(/Hello, Shradha/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no analyses", async () => {
    api.history.mockResolvedValue([]);
    renderAt(<Home />, { path: "/", route: "/" });
    expect(await screen.findByText(/No analyses yet/)).toBeInTheDocument();
  });

  it("deletes an analysis after confirmation", async () => {
    api.history.mockResolvedValue(history);
    api.deleteAnalysis.mockResolvedValue({});
    renderAt(<Home />, { path: "/", route: "/" });
    const row = (await screen.findByText("Backend Developer")).closest("tr");
    await userEvent.click(within(row).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(api.deleteAnalysis).toHaveBeenCalledWith(history[0].id));
  });
});

describe("ML model status card", () => {
  it("says the classifier is untrained instead of showing made-up accuracy", async () => {
    api.history.mockResolvedValue([]);
    api.mlInfo.mockResolvedValue(UNTRAINED);
    renderAt(<Home />, { path: "/", route: "/" });
    expect(await screen.findByTestId("ml-status")).toHaveTextContent("Not trained yet");
    expect(screen.getByTestId("ml-status")).not.toHaveTextContent("F1");
  });

  it("shows the real metrics returned by the backend once trained", async () => {
    api.history.mockResolvedValue([]);
    api.mlInfo.mockResolvedValue({ role_classifier: { trained: true, message: "ok", metrics: {
      selected_model: "linear_svm", test: { f1_macro: 0.8123, accuracy: 0.83 },
      split: { test_rows: 400 }, dataset: { n_classes: 12, source_file: "jobs.csv" } } } });
    renderAt(<Home />, { path: "/", route: "/" });
    const el = await screen.findByTestId("ml-status");
    expect(el).toHaveTextContent("linear_svm");
    expect(el).toHaveTextContent("0.812");
    expect(el).toHaveTextContent("400 held-out");
    expect(el).toHaveTextContent("jobs.csv");
  });
});
