import { useCallback, useMemo, useState, type ReactNode } from "react";
import { LanguageContext, type LanguageContextValue } from "./context";
import { languages, translations, type Language } from "./translations";

const STORAGE_KEY = "smart-qora-language";

function readStored(): Language | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value && (languages as readonly string[]).includes(value) ? (value as Language) : null;
  } catch {
    return null;
  }
}

function detectLanguage(): Language {
  const stored = readStored();
  if (stored) return stored;
  const browser = navigator.language.toLowerCase().split("-")[0];
  return (languages as readonly string[]).includes(browser) ? (browser as Language) : "ru";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const initial = detectLanguage();
    document.documentElement.lang = initial;
    return initial;
  });

  const setLanguage = useCallback((value: Language) => {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* storage disabled — language still applies for this session */
    }
    document.documentElement.lang = value;
    setLanguageState(value);
  }, []);

  const setLanguageIfUnset = useCallback((value: Language) => {
    if (readStored() === null && (languages as readonly string[]).includes(value)) {
      document.documentElement.lang = value;
      setLanguageState(value);
    }
  }, []);

  const value = useMemo<LanguageContextValue>(
    () => ({ language, t: translations[language], setLanguage, setLanguageIfUnset }),
    [language, setLanguage, setLanguageIfUnset],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
