import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthProvider";
import { LanguageProvider } from "../i18n/LanguageProvider";
import { Events } from "./Events";

function row(id: number) {
  return {
    id,
    camera_id: 1,
    animal_type: "sheep",
    tracking_id: id,
    crossing_sequence: 1,
    direction: "IN",
    confidence: 0.9,
    timestamp: "2026-09-03T10:00:00Z",
  };
}

function renderEvents() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <LanguageProvider>
        <AuthProvider>
          <MemoryRouter>
            <Events />
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
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(Array.from({ length: 25 }, (_, i) => row(i + 1))), {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Total-Count": "60" },
    }),
  );
});
afterEach(() => vi.restoreAllMocks());

describe("Events pager", () => {
  it("derives page count from the X-Total-Count header", async () => {
    renderEvents();
    // 60 rows / 25 per page => 3 pages
    expect(await screen.findByText(/Page 1 of 3/i)).toBeInTheDocument();
    expect(screen.getByText(/^60 /)).toBeInTheDocument(); // "60 records"
  });
});
