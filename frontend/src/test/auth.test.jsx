import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "../App";
import Login from "../pages/Login";
import Register from "../pages/Register";
import { api, TOKEN_KEY } from "../services/api";
import { renderAt } from "./helpers";
import loginFx from "./fixtures/login.json";

vi.mock("../services/api", async () => (await import("./apiMock.js")).default());

describe("login", () => {
  it("logs in, stores the token and navigates home", async () => {
    api.login.mockResolvedValue(loginFx);
    renderAt(<Login />, { path: "/login", route: "/login", extra: ["/"] });
    await userEvent.type(screen.getByLabelText("Email"), "s@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "Passw0rd123");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    await waitFor(() => expect(screen.getByText("navigated:/")).toBeInTheDocument());
    expect(api.login).toHaveBeenCalledWith({ email: "s@example.com", password: "Passw0rd123" });
    expect(localStorage.getItem(TOKEN_KEY)).toBe(loginFx.access_token);
  });

  it("shows the server error for wrong credentials and stays on the page", async () => {
    api.login.mockRejectedValue({ response: { status: 401, data: { detail: "Incorrect email or password" } } });
    renderAt(<Login />, { path: "/login", route: "/login" });
    await userEvent.type(screen.getByLabelText("Email"), "s@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password");
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("asks for email and password before calling the API", async () => {
    renderAt(<Login />, { path: "/login", route: "/login" });
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter your email and password");
    expect(api.login).not.toHaveBeenCalled();
  });
});

describe("register", () => {
  async function fill({ name = "Shradha", email = "s@example.com", password = "Passw0rd123", confirm = "Passw0rd123" }) {
    await userEvent.type(screen.getByLabelText("Full name"), name);
    await userEvent.type(screen.getByLabelText("Email"), email);
    await userEvent.type(screen.getByLabelText("Password"), password);
    await userEvent.type(screen.getByLabelText("Confirm password"), confirm);
    await userEvent.click(screen.getByRole("button", { name: "Register" }));
  }

  it("rejects weak passwords and mismatches without calling the API", async () => {
    renderAt(<Register />, { path: "/register", route: "/register" });
    await fill({ password: "short1", confirm: "short1" });
    expect(screen.getByRole("alert")).toHaveTextContent("8-64 characters");
    expect(api.register).not.toHaveBeenCalled();
  });

  it("rejects mismatched confirmation", async () => {
    renderAt(<Register />, { path: "/register", route: "/register" });
    await fill({ confirm: "Different123" });
    expect(screen.getByRole("alert")).toHaveTextContent("do not match");
  });

  it("registers, logs in and goes to the dashboard", async () => {
    api.register.mockResolvedValue(loginFx.user);
    api.login.mockResolvedValue(loginFx);
    renderAt(<Register />, { path: "/register", route: "/register", extra: ["/"] });
    await fill({});
    await waitFor(() => expect(screen.getByText("navigated:/")).toBeInTheDocument());
    expect(api.register).toHaveBeenCalledWith({ full_name: "Shradha", email: "s@example.com", password: "Passw0rd123" });
  });

  it("shows duplicate-email errors from the server", async () => {
    api.register.mockRejectedValue({ response: { status: 409, data: { detail: "Email already registered" } } });
    renderAt(<Register />, { path: "/register", route: "/register" });
    await fill({});
    expect(await screen.findByRole("alert")).toHaveTextContent("Email already registered");
  });
});

describe("protected routes", () => {
  it("redirects visitors without a token to the login page", async () => {
    renderAt(<App />, { path: "/resumes", route: "/*" });
    expect(await screen.findByText("Welcome back")).toBeInTheDocument();
  });

  it("logs out: calls the API, clears the token and returns to login", async () => {
    api.me.mockResolvedValue(loginFx.user);
    api.mlInfo.mockResolvedValue({ role_classifier: { trained: false, metrics: null } });
    api.history.mockResolvedValue([]);
    renderAt(<App />, { path: "/", route: "/*", loggedIn: true });
    await userEvent.click(await screen.findByRole("button", { name: "Log out" }));
    await waitFor(() => expect(api.logout).toHaveBeenCalled());
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(await screen.findByText("Welcome back")).toBeInTheDocument();
  });
});
