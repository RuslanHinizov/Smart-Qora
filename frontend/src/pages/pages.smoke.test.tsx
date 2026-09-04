import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthProvider";
import { LanguageProvider } from "../i18n/LanguageProvider";
import { Cameras } from "./Cameras";
import { Dashboard } from "./Dashboard";
import { Events } from "./Events";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <LanguageProvider>
        <AuthProvider>
          <MemoryRouter>{node}</MemoryRouter>
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
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response("[]", {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Total-Count": "0" },
    }),
  );
});
afterEach(() => vi.restoreAllMocks());

describe("page smoke render", () => {
  it("Dashboard renders its metric labels", () => {
    wrap(<Dashboard />);
    expect(screen.getByText(/entered today/i)).toBeInTheDocument();
  });

  it("Cameras renders the empty state", async () => {
    wrap(<Cameras />);
    expect(await screen.findByText(/no cameras configured/i)).toBeInTheDocument();
  });

  it("Events renders the filter toolbar", () => {
    wrap(<Events />);
    expect(screen.getByLabelText(/direction/i)).toBeInTheDocument();
  });
});
