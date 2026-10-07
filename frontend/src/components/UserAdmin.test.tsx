import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "../i18n/LanguageProvider";
import { AccountCard, UsersCard } from "./UserAdmin";

type Call = { url: string; method: string; body: unknown };
let calls: Call[] = [];

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <LanguageProvider>{node}</LanguageProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  calls = [];
  try {
    localStorage.clear();
    localStorage.setItem("smart-qora-language", "en");
  } catch {
    /* ignore */
  }
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    if (url.endsWith("/auth/change-password")) return new Response(null, { status: 204 });
    const body = url.endsWith("/auth/me")
      ? { id: 1, username: "admin", role: "admin", is_active: true }
      : [
          { id: 1, username: "admin", role: "admin", is_active: true },
          { id: 2, username: "shepherd", role: "viewer", is_active: true },
        ];
    return new Response(JSON.stringify(body), {
      status: method === "POST" ? 201 : 200,
      headers: { "Content-Type": "application/json" },
    });
  });
});
afterEach(() => vi.restoreAllMocks());

describe("AccountCard", () => {
  it("sends the current and new password, and only once the new one is long enough", async () => {
    wrap(<AccountCard />);
    const button = screen.getByRole("button", { name: /change password/i });
    await userEvent.type(screen.getByLabelText(/current password/i), "old-secret");
    await userEvent.type(screen.getByLabelText(/new password/i), "short");
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/new password/i), "-but-longer");
    await userEvent.click(button);

    expect(await screen.findByText(/password changed/i)).toBeInTheDocument();
    const call = calls.find((c) => c.url.endsWith("/auth/change-password"));
    expect(call?.body).toEqual({
      current_password: "old-secret",
      new_password: "short-but-longer",
    });
  });
});

describe("UsersCard", () => {
  it("lists users, adds one and deactivates another", async () => {
    wrap(<UsersCard />);
    expect(await screen.findByText("shepherd")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/^username$/i), "newbie");
    await userEvent.type(screen.getByLabelText(/^password$/i), "long-enough-pw");
    await userEvent.click(screen.getByRole("button", { name: /add user/i }));
    const created = calls.find((c) => c.method === "POST");
    expect(created?.url.endsWith("/api/users")).toBe(true);
    expect(created?.body).toEqual({
      username: "newbie",
      password: "long-enough-pw",
      role: "viewer",
    });

    await userEvent.click(screen.getAllByRole("button", { name: /deactivate/i })[1]);
    const updated = calls.find((c) => c.method === "PUT");
    expect(updated?.url.endsWith("/api/users/2")).toBe(true);
    expect(updated?.body).toEqual({ is_active: false });
  });
});
