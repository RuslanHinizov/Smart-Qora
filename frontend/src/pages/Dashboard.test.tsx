import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthProvider";
import { LanguageProvider } from "../i18n/LanguageProvider";
import { Dashboard } from "./Dashboard";

const ZONES = [
  { id: 1, name: "Outside", kind: "EXTERNAL", is_active: true, sort_order: 0, created_at: "" },
  { id: 2, name: "Main Pen", kind: "PEN", is_active: true, sort_order: 1, created_at: "" },
  { id: 3, name: "Pasture", kind: "PASTURE", is_active: true, sort_order: 2, created_at: "" },
];
const row = (zone_id: number, zone_name: string, quantity: number) => ({
  zone_id,
  zone_name,
  group_id: 1,
  group_name: "Sheep",
  species: "sheep",
  quantity,
});
// 35 sheep walked in through the gate: the boundary zone carries the mirror -35.
const INVENTORY = [row(1, "Outside", -35), row(2, "Main Pen", 35), row(3, "Pasture", 12)];

beforeEach(() => {
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const body = url.includes("/farm/zones")
      ? ZONES
      : url.includes("/inventory/summary")
        ? INVENTORY
        : {};
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
});
afterEach(() => vi.restoreAllMocks());

describe("Dashboard herd totals", () => {
  it("counts only animals on the farm, never the external boundary balance", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={qc}>
        <LanguageProvider>
          <AuthProvider>
            <MemoryRouter>
              <Dashboard />
            </MemoryRouter>
          </AuthProvider>
        </LanguageProvider>
      </QueryClientProvider>,
    );

    await screen.findByText("Main Pen");
    const herd = container.querySelector(".herd-now") as HTMLElement;
    expect(herd.querySelector(".herd-total")).toHaveTextContent("47");
    expect(herd.querySelector(".herd-place.inside strong")).toHaveTextContent("35");
    expect(herd.querySelector(".herd-place.outside strong")).toHaveTextContent("12");
    const places = container.querySelector(".location-list") as HTMLElement;
    expect(within(places).queryByText("Outside")).not.toBeInTheDocument();
    expect(container.textContent).not.toContain("-35");
  });
});
