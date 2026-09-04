import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  AppSettings,
  Camera,
  CameraInput,
  EventQuery,
  EventRow,
  HistoryRow,
  Me,
  SettingsInput,
  SystemStatus,
  Totals,
  WorkerInfo,
} from "./types";

export const keys = {
  me: ["me"] as const,
  status: ["status"] as const,
  worker: ["worker"] as const,
  statsToday: ["stats", "today"] as const,
  events: (query: EventQuery) => ["events", query] as const,
  cameras: ["cameras"] as const,
  settings: ["settings"] as const,
  history: (from: string, to: string, group: string) => ["history", from, to, group] as const,
};

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: async () => (await apiFetch<Me>("/auth/me")).data,
    retry: false,
    staleTime: 5 * 60_000,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: keys.status,
    queryFn: async () => (await apiFetch<SystemStatus>("/status")).data,
    refetchInterval: 15_000,
  });
}

export function useWorkerInfo() {
  return useQuery({
    queryKey: keys.worker,
    queryFn: async () => (await apiFetch<WorkerInfo>("/worker")).data,
    refetchInterval: 10_000,
  });
}

export function useStatsToday() {
  return useQuery({
    queryKey: keys.statsToday,
    queryFn: async () => (await apiFetch<Totals>("/statistics/today")).data,
  });
}

export type EventsPage = { rows: EventRow[]; total: number };

export function useEvents(query: EventQuery) {
  return useQuery({
    queryKey: keys.events(query),
    queryFn: async () => {
      const { data, response } = await apiFetch<EventRow[]>("/events", { params: query });
      return { rows: data, total: Number(response.headers.get("X-Total-Count") ?? data.length) };
    },
    placeholderData: (previous) => previous,
  });
}

export function useCameras() {
  return useQuery({
    queryKey: keys.cameras,
    queryFn: async () => (await apiFetch<Camera[]>("/cameras")).data,
  });
}

export function useSettings() {
  return useQuery({
    queryKey: keys.settings,
    queryFn: async () => (await apiFetch<AppSettings>("/settings")).data,
  });
}

export function useHistory(from: string, to: string, group: "day" | "week" | "month") {
  return useQuery({
    queryKey: keys.history(from, to, group),
    queryFn: async () =>
      (await apiFetch<HistoryRow[]>("/statistics/history", { params: { from, to, group } })).data,
    enabled: Boolean(from && to),
  });
}

export function useCameraMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: keys.cameras });

  const create = useMutation({
    mutationFn: (input: CameraInput) =>
      apiFetch<Camera>("/cameras", { method: "POST", body: input }),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, input }: { id: number; input: CameraInput }) =>
      apiFetch<Camera>(`/cameras/${id}`, { method: "PUT", body: input }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/cameras/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
  return { create, update, remove };
}

export function useSettingsMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: SettingsInput) =>
      apiFetch<AppSettings>("/settings", { method: "PUT", body: input }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.settings }),
  });
}

export function useCalibrateHerd() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (current_inside: number) =>
      apiFetch<{ current_inside: number }>("/herd/calibrate", {
        method: "POST",
        body: { current_inside },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.statsToday }),
  });
}

export function useRestartWorker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ restarting: boolean }>("/worker/restart", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.worker }),
  });
}
