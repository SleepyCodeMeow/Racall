"use client";
import { useI18n } from "../../lib/i18n";
import { languages, type Locale } from "../../lib/translations";
import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  Check,
  FolderOpen,
  Key,
  PlugsConnected,
} from "@phosphor-icons/react";
import { api, Settings } from "../../lib/api";

export function SettingsPanel({
  close,
  report,
}: {
  close: () => void;
  report: (message: string) => void;
}) {
  const { tr, locale, setLanguage, savingLanguage } = useI18n();
  const [settings, setSettings] = useState<Settings>();
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    api<Settings>("/settings")
      .then(setSettings)
      .catch((e) => report(e.message));
  }, [report]);
  if (!settings)
    return (
      <div className="p-10">
        <div className="skeleton h-12" />
      </div>
    );
  const edit = (field: keyof Settings, value: string) => {
    setSettings({ ...settings, [field]: value });
    setSaved(false);
  };
  return (
    <section className="settings page-content">
      <div className="eyebrow">{tr("settings.eyebrow")}</div>
      <h1>{tr("settings.title")}</h1>
      <p className="muted">{tr("settings.description")}</p>
      <div className="language-setting">
        <label htmlFor="interface-language">{tr("settings.language")}</label>
        <select
          id="interface-language"
          value={locale}
          disabled={savingLanguage}
          onChange={(e) => void setLanguage(e.target.value as Locale)}
        >
          {languages.map((language) => (
            <option key={language.id} value={language.id} lang={language.id}>
              {language.label}
            </option>
          ))}
        </select>
        <p aria-live="polite">
          {savingLanguage ? tr("common.saving") : tr("settings.languageHint")}
        </p>
      </div>
      <div className="section-heading">
        <PlugsConnected size={22} />
        <h2>{tr("settings.connection")}</h2>
      </div>
      <div className="segmented">
        <button
          className={!settings.base_url.includes("11434") ? "selected" : ""}
          onClick={() => edit("base_url", "https://api.openai.com/v1")}
        >
          {tr("settings.cloud")}
        </button>
        <button
          className={settings.base_url.includes("11434") ? "selected" : ""}
          onClick={() => edit("base_url", "http://127.0.0.1:11434/v1")}
        >
          Ollama
        </button>
      </div>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await api("/settings", "PUT", {
              base_url: settings.base_url,
              model: settings.model,
              embedding_model: settings.embedding_model,
              ...(key ? { api_key: key } : {}),
            });
            setKey("");
            setSaved(true);
          } catch (error) {
            report((error as Error).message);
          } finally {
            setBusy(false);
          }
        }}
        className="grid gap-5 mt-6"
      >
        <label>
          {tr("settings.apiUrl")}
          <input
            value={settings.base_url}
            required
            onChange={(e) => edit("base_url", e.target.value)}
            placeholder="https://api.openai.com/v1"
          />
          <small>{tr("settings.apiHint")}</small>
        </label>
        <label>
          {tr("settings.key")}{" "}
          <span className="optional">
            {settings.has_key
              ? tr("settings.keySaved")
              : tr("settings.keyMissing")}
          </span>
          <input
            type="password"
            value={key}
            autoComplete="off"
            onChange={(e) => {
              setKey(e.target.value);
              setSaved(false);
            }}
            placeholder={tr("settings.keyPlaceholder")}
          />
        </label>
        <div className="grid sm:grid-cols-2 gap-4">
          <label>
            {tr("settings.model")}
            <input
              value={settings.model}
              onChange={(e) => edit("model", e.target.value)}
              placeholder={tr("settings.modelPlaceholder")}
              required
            />
          </label>
          <label>
            {tr("settings.embedding")}{" "}
            <span className="optional">{tr("common.optional")}</span>
            <input
              value={settings.embedding_model}
              onChange={(e) => edit("embedding_model", e.target.value)}
              placeholder={tr("settings.embeddingPlaceholder")}
            />
          </label>
        </div>
        <p className="notice">
          <Key size={18} /> {tr("settings.cloudNotice")}
        </p>
        <div className="flex gap-3">
          <button className="primary" disabled={busy}>
            {saved ? <Check size={18} /> : null}
            {busy
              ? tr("common.saving")
              : saved
                ? tr("common.saved")
                : tr("settings.save")}
          </button>
          <button type="button" className="secondary" onClick={close}>
            {tr("common.back")}
          </button>
        </div>
      </form>
      <div className="section-heading mt-10">
        <FolderOpen size={22} />
        <h2>{tr("settings.files")}</h2>
      </div>
      <p className="muted">{tr("settings.filesDescription")}</p>
      <code className="path">{settings.vault_path}</code>
      {window.desktop && (
        <button
          className="secondary mt-4"
          onClick={() =>
            window.desktop?.openVault().then((error) => {
              if (error) report(error);
            })
          }
        >
          {tr("settings.openFolder")} <ArrowUpRight size={16} />
        </button>
      )}
    </section>
  );
}
