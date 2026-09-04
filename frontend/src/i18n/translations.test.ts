import { describe, expect, it } from "vitest";
import { languages, translations, type TranslationKey } from "./translations";

// `translations` is typed `Record<Language, Dictionary>`, so a missing key is a
// compile error. This guards against empty strings and stray keys at runtime.
describe("translations", () => {
  const keys = Object.keys(translations.en) as TranslationKey[];

  it("every language has every key, non-empty", () => {
    for (const lang of languages) {
      for (const key of keys) {
        expect(translations[lang][key], `${lang}.${key}`).toBeTruthy();
      }
    }
  });

  it("no language has extra keys", () => {
    for (const lang of languages) {
      expect(Object.keys(translations[lang]).sort()).toEqual([...keys].sort());
    }
  });
});
