import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthProvider";
import { LanguageProvider } from "../i18n/LanguageProvider";
import { Login } from "./Login";

function renderLogin() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <LanguageProvider>
        <AuthProvider>
          <MemoryRouter>
            <Login />
          </MemoryRouter>
        </AuthProvider>
      </LanguageProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
});
afterEach(() => vi.restoreAllMocks());

describe("Login", () => {
  it("stores the token returned by /api/auth/login", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: "abc.def.ghi", token_type: "bearer", role: "admin" }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    renderLogin();
    await userEvent.type(screen.getByLabelText(/user/i), "admin");
    await userEvent.type(screen.getByLabelText(/pass/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(localStorage.getItem("smart-qora-token")).toBe("abc.def.ghi"));
  });

  it("shows an error on bad credentials", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Incorrect username or password" }), { status: 401 }),
    );

    renderLogin();
    await userEvent.type(screen.getByLabelText(/user/i), "admin");
    await userEvent.type(screen.getByLabelText(/pass/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/incorrect username or password/i)).toBeInTheDocument();
  });
});
