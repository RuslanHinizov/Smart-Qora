import { languages } from "../i18n/translations";
import { useLanguage } from "../i18n/useLanguage";
import { Icon } from "./Icon";

const labels: Record<string, string> = { ru: "RU", kk: "KZ", en: "EN", tr: "TR" };

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();
  return (
    <label className="lang-select" title={t.language}>
      <Icon name="globe" size={16} />
      <select
        value={language}
        aria-label={t.language}
        onChange={(event) => setLanguage(event.target.value as (typeof languages)[number])}
      >
        {languages.map((code) => (
          <option key={code} value={code}>
            {labels[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
