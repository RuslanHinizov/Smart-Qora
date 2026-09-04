import { createContext } from "react";
import type { Dictionary, Language } from "./translations";

export type LanguageContextValue = {
  language: Language;
  t: Dictionary;
  setLanguage: (value: Language) => void;
  setLanguageIfUnset: (value: Language) => void;
};

export const LanguageContext = createContext<LanguageContextValue | null>(null);
