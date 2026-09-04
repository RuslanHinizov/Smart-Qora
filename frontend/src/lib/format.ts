import type { Dictionary, Language } from "../i18n/translations";

const LOCALE: Record<Language, string> = { ru: "ru-RU", kk: "kk-KZ", en: "en-US", tr: "tr-TR" };

export function statusLabel(t: Dictionary, value: string): string {
  const map: Record<string, string> = {
    ONLINE: t.statusOnline,
    OFFLINE: t.statusOffline,
    RECONNECTING: t.statusReconnecting,
    IDLE: t.statusIdle,
    ACTIVE: t.statusActive,
    running: t.statusActive,
    stopped: t.statusStopped,
    starting: t.statusReconnecting,
    restarting: t.statusReconnecting,
    failed: t.statusOffline,
  };
  return map[value] ?? value;
}

export function animalLabel(t: Dictionary, value: string): string {
  const map: Record<string, string> = {
    sheep: t.animalSheep,
    cattle: t.animalCattle,
    goat: t.animalGoat,
    horse: t.animalHorse,
  };
  return map[value.toLowerCase()] ?? value;
}

export function formatTime(iso: string, language: Language): string {
  return new Date(iso).toLocaleTimeString(LOCALE[language], { hour: "2-digit", minute: "2-digit" });
}

export function formatDateTime(iso: string, language: Language): string {
  return new Date(iso).toLocaleString(LOCALE[language], {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export function formatDate(value: string, language: Language): string {
  return new Date(value).toLocaleDateString(LOCALE[language], { month: "short", day: "numeric" });
}

export function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export function daysAgoISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}
