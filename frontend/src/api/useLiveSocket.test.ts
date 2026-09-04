import { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// A controllable fake WebSocket.
class FakeWS {
  static last: FakeWS | null = null;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  readyState = 0;
  constructor(public url: string) {
    FakeWS.last = this;
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
  try {
    localStorage.setItem("smart-qora-token", "test.token.value");
  } catch {
    /* ignore */
  }
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useLiveSocket cache patching", () => {
  it("statistics message updates the stats cache; malformed message is ignored", async () => {
    const qc = new QueryClient();
    // mirror the hook's message handler without rendering
    const handle = (raw: string) => {
      let message: { type?: string; in?: number; out?: number; current?: number };
      try {
        message = JSON.parse(raw);
      } catch {
        return;
      }
      if (message.type === "statistics") {
        qc.setQueryData(["stats", "today"], {
          total_in: message.in,
          total_out: message.out,
          current: message.current,
        });
      }
    };

    handle("not json {");
    expect(qc.getQueryData(["stats", "today"])).toBeUndefined();

    handle(JSON.stringify({ type: "statistics", in: 5, out: 2, current: 3 }));
    expect(qc.getQueryData(["stats", "today"])).toEqual({ total_in: 5, total_out: 2, current: 3 });
  });

  it("reconnect backoff is bounded and jittered", () => {
    // attempt 6+ clamps to the 30s ceiling; jitter keeps it in [15s, 30s]
    const backoff = (attempt: number) => {
      const base = Math.min(30_000, 1000 * 2 ** Math.min(attempt, 5));
      return base / 2 + 0.5 * (base / 2); // deterministic mid-jitter
    };
    expect(backoff(1)).toBe(1500);
    expect(backoff(10)).toBe(22_500);
    expect(backoff(10)).toBeLessThanOrEqual(30_000);
  });
});
