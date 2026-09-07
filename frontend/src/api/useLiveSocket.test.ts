import { createElement } from "react";
import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useLiveSocket } from "./useLiveSocket";

class FakeWS {
  static instances: FakeWS[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  constructor(public url: string) {
    FakeWS.instances.push(this);
  }
  close() {
    this.onclose?.();
  }
  receive(value: unknown) {
    this.onmessage?.({ data: JSON.stringify(value) });
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  FakeWS.instances = [];
  vi.stubGlobal("WebSocket", FakeWS);
  localStorage.setItem("smart-qora-token", "test.token");
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function mount(qc = new QueryClient()) {
  const hook = renderHook(() => useLiveSocket(), {
    wrapper: ({ children }) => createElement(QueryClientProvider, { client: qc }, children),
  });
  return { ...hook, qc, ws: FakeWS.instances[0] };
}

describe("real useLiveSocket hook", () => {
  it("updates totals and ignores malformed input", () => {
    const { ws, qc, unmount } = mount();
    expect(ws.url).toMatch(/^ws:\/\/[^/]+\/ws\/live$/);
    expect(ws.url).not.toContain("token=");
    act(() => ws.onmessage?.({ data: "bad json" }));
    expect(qc.getQueryData(["stats", "today"])).toBeUndefined();
    act(() => ws.receive({ type: "statistics", in: 5, out: 2, current: 8 }));
    expect(qc.getQueryData(["stats", "today"])).toEqual({ total_in: 5, total_out: 2, current: 8 });
    unmount();
  });

  it("preserves filtered and paginated rows and batches refreshes", () => {
    const qc = new QueryClient();
    const keys = [
      ["events", { direction: "OUT" }],
      ["events", { offset: 100, limit: 20 }],
      ["events", { animal_type: "cattle", from: "2020-01-01", to: "2020-01-02" }],
    ];
    for (const key of keys) qc.setQueryData(key, { rows: [{ id: 50 }], total: 120 });
    const invalidate = vi.spyOn(qc, "invalidateQueries");
    const { ws, unmount } = mount(qc);
    act(() => {
      for (let i = 0; i < 10; i++)
        ws.receive({ type: "event", event: { id: 99, direction: "IN" } });
    });
    for (const key of keys)
      expect(qc.getQueryData(key)).toEqual({ rows: [{ id: 50 }], total: 120 });
    expect(invalidate).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(500));
    expect(invalidate).toHaveBeenCalledTimes(2);
    for (const key of keys) expect(qc.getQueryState(key)?.isInvalidated).toBe(true);
    unmount();
  });

  it("refreshes after reconnect and cancels timers on unmount", () => {
    vi.spyOn(Math, "random").mockReturnValue(0.5);
    const { ws, qc, unmount } = mount();
    const invalidate = vi.spyOn(qc, "invalidateQueries");
    act(() => ws.close());
    act(() => vi.advanceTimersByTime(1500));
    expect(FakeWS.instances).toHaveLength(2);
    act(() => FakeWS.instances[1].onopen?.());
    act(() => vi.advanceTimersByTime(500));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["events"] });
    unmount();
    act(() => vi.advanceTimersByTime(60000));
    expect(FakeWS.instances).toHaveLength(2);
  });
});
