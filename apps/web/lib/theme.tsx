"use client";
import {
  createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import { useI18n } from "./i18n";

export type Theme = "light" | "dark" | "system";
type ResolvedTheme = Exclude<Theme, "system">;
type Appearance = {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  saving: boolean;
  ready: boolean;
  error: "load" | "save" | null;
  setTheme: (theme: Theme) => Promise<void>;
  reload: () => Promise<void>;
  dismissError: () => void;
};
const Context = createContext<Appearance | null>(null);
export const isTheme = (value: unknown): value is Theme =>
  value === "light" || value === "dark" || value === "system";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { tr } = useI18n();
  const [theme, applyTheme] = useState<Theme>("light");
  const [systemDark, setSystemDark] = useState(false);
  const [saving, setSaving] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<Appearance["error"]>(null);
  const resolvedTheme = theme === "system" ? (systemDark ? "dark" : "light") : theme;

  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setSystemDark(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.dataset.themePreference = theme;
    document.documentElement.style.colorScheme = resolvedTheme;
    // Electron owns native window decoration; never draw a replacement title bar.
    if (ready) void window.desktop?.setTheme?.(theme).catch(() => {});
  }, [theme, resolvedTheme, ready]);

  const reload = useCallback(async () => {
    try {
      const result = await api<{ theme: unknown }>("/appearance");
      if (!isTheme(result.theme)) throw new Error("Invalid appearance preference");
      applyTheme(result.theme);
      setError(null);
    } catch {
      setError("load");
    } finally {
      setReady(true);
    }
  }, []);
  useEffect(() => { void reload(); }, [reload]);

  const setTheme = useCallback(async (next: Theme) => {
    if (!isTheme(next) || saving) return;
    setSaving(true);
    try {
      const result = await api<{ theme: unknown }>("/appearance", "PUT", { theme: next });
      if (result.theme !== next) throw new Error("Invalid appearance response");
      applyTheme(next);
      setError(null);
    } catch {
      setError("save");
    } finally {
      setSaving(false);
    }
  }, [saving]);
  const value = useMemo<Appearance>(() => ({
    theme, resolvedTheme, saving, ready, error, setTheme, reload,
    dismissError: () => setError(null),
  }), [theme, resolvedTheme, saving, ready, error, setTheme, reload]);

  return <Context.Provider value={value}>
    {error && <div className="language-error appearance-error" role="alert">
      <span>{tr(error === "load" ? "settings.themeLoadError" : "settings.themeSaveError")}</span>
      {error === "load" && <button type="button" onClick={() => void reload()}>{tr("common.retry")}</button>}
      <button type="button" aria-label={tr("common.dismissError")} onClick={value.dismissError}>×</button>
    </div>}
    {ready ? children : <div className="appearance-loading" role="status">
      <span className="appearance-loading-dot" aria-hidden="true" />
      <span>{tr("common.loadingApp")}</span>
    </div>}
  </Context.Provider>;
}

export function useTheme() {
  const value = useContext(Context);
  if (!value) throw new Error("useTheme requires ThemeProvider");
  return value;
}
