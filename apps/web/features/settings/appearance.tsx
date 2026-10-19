"use client";
import { Desktop, Moon, Sun } from "@phosphor-icons/react";
import { useI18n } from "../../lib/i18n";
import { useTheme, type Theme } from "../../lib/theme";

const choices = [
  { id: "light", label: "settings.themeLight", Icon: Sun },
  { id: "dark", label: "settings.themeDark", Icon: Moon },
  { id: "system", label: "settings.themeSystem", Icon: Desktop },
] as const;

export function AppearanceSettings() {
  const { tr } = useI18n();
  const { theme, setTheme, saving, ready } = useTheme();
  return <fieldset className="appearance-setting" disabled={saving || !ready}>
    <legend>{tr("settings.appearance")}</legend>
    <div className="theme-options">
      {choices.map(({ id, label, Icon }) => <label key={id} className="theme-choice">
        <input type="radio" name="interface-theme" value={id}
          checked={theme === id} onChange={() => void setTheme(id as Theme)} />
        <span><Icon size={18} aria-hidden="true" />{tr(label)}</span>
      </label>)}
    </div>
    <p aria-live="polite">{saving ? tr("common.saving") : tr("settings.themeHint")}</p>
  </fieldset>;
}
