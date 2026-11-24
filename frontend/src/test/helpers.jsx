import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../context/AuthContext";
import { TOKEN_KEY } from "../services/api";
import loginFx from "./fixtures/login.json";

/** Render `element` at `path` inside Router + AuthProvider, with extra placeholder routes to observe navigation. */
export function renderAt(element, { path = "/", route = "/", extra = [], loggedIn = false } = {}) {
  if (loggedIn) localStorage.setItem(TOKEN_KEY, loginFx.access_token);
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path={route} element={element} />
          {extra.map((p) => <Route key={p} path={p} element={<div>{`navigated:${p}`}</div>} />)}
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}
