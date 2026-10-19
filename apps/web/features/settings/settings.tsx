"use client";
import { useI18n } from "../../lib/i18n";
import { languages, type Locale } from "../../lib/translations";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AppearanceSettings } from "./appearance";
import {
  ArrowUpRight,
  Check,
  FolderOpen,
  Key,
  PlugsConnected,
} from "@phosphor-icons/react";
import {
  api,
  type EmbeddingProviderId,
  type ProviderId,
  type ProviderProfile,
  type Settings,
} from "../../lib/api";
import { ProviderConnection } from "./provider-connection";
import { EmbeddingConnection } from "./embedding-settings";
import { emptyProfile } from "./providers";

export function SettingsPanel({
  close,
  report,
}: {
  close: () => void;
  report: (message: string) => void;
}) {
  const { tr, locale, setLanguage, savingLanguage } = useI18n();
  const client = useQueryClient();
  const [settings, setSettings] = useState<Settings>();
  const [keys, setKeys] = useState<Partial<Record<ProviderId, string>>>({});
  const [embeddingKeys, setEmbeddingKeys] = useState<Partial<Record<EmbeddingProviderId, string>>>({});
  const [embeddingDrafts, setEmbeddingDrafts] = useState<Partial<Record<EmbeddingProviderId, ProviderProfile>>>({});
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
  const editProfile = (field: "base_url" | "model", value: string) => {
    setSettings({
      ...settings,
      profiles: {
        ...settings.profiles,
        [settings.provider]: {
          ...settings.profiles[settings.provider],
          [field]: value,
          ...(field === "base_url" ? { has_key: false } : {}),
        },
      },
    });
    setSaved(false);
  };
  const selectProvider = (provider: ProviderId) => {
    setSettings({ ...settings, provider });
    setSaved(false);
  };
  const selectEmbeddingProvider = (provider: EmbeddingProviderId) => {
    setEmbeddingDrafts({ ...embeddingDrafts, [settings.embeddings.provider]: settings.embeddings });
    setSettings({
      ...settings,
      embeddings: { ...(embeddingDrafts[provider] || emptyProfile(provider)), provider },
    });
    setSaved(false);
  };
  const editEmbeddings = (field: "base_url" | "model", value: string) => {
    setSettings({
      ...settings,
      embeddings: {
        ...settings.embeddings,
        [field]: value,
        ...(field === "base_url" ? { has_key: false } : {}),
      },
    });
    setSaved(false);
  };
  const pendingOtherKeys = Object.entries(keys).some(([id, value]) => id !== settings.provider && value)
    || Object.entries(embeddingKeys).some(([id, value]) => id !== settings.embeddings.provider && value);
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
      <AppearanceSettings />
      <div className="section-heading">
        <PlugsConnected size={22} />
        <h2>{tr("settings.connection")}</h2>
      </div>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            const key = keys[settings.provider];
            const embeddingKey = embeddingKeys[settings.embeddings.provider];
            await api("/settings", "PUT", {
              provider: settings.provider,
              profiles: Object.fromEntries(Object.entries(settings.profiles).map(([id, profile]) => [id, {
                base_url: profile.base_url,
                model: profile.model,
              }])),
              embeddings: {
                provider: settings.embeddings.provider,
                base_url: settings.embeddings.base_url,
                model: settings.embeddings.model,
              },
              ...(key ? { api_key: key } : {}),
              ...(embeddingKey ? { embedding_api_key: embeddingKey } : {}),
            });
            const refreshed = await api<Settings>("/settings");
            setSettings(refreshed);
            client.setQueryData(["settings"], refreshed);
            void client.invalidateQueries({ queryKey: ["models"] });
            void client.invalidateQueries({ queryKey: ["provider"] });
            setKeys((drafts) => ({ ...drafts, [settings.provider]: "" }));
            setEmbeddingKeys((drafts) => ({ ...drafts, [settings.embeddings.provider]: "" }));
            setSaved(true);
          } catch (error) {
            report((error as Error).message);
          } finally {
            setBusy(false);
          }
        }}
        className="grid gap-5 provider-settings-form"
      >
        <ProviderConnection
          provider={settings.provider}
          profile={settings.profiles[settings.provider]}
          apiKey={keys[settings.provider] || ""}
          disabled={busy}
          selectProvider={selectProvider}
          editProfile={editProfile}
          editKey={(value) => {
            setKeys({ ...keys, [settings.provider]: value });
            setSaved(false);
          }}
        />
        <EmbeddingConnection
          settings={settings.embeddings}
          apiKey={embeddingKeys[settings.embeddings.provider] || ""}
          disabled={busy}
          selectProvider={selectEmbeddingProvider}
          editProfile={editEmbeddings}
          editKey={(value) => {
            setEmbeddingKeys({ ...embeddingKeys, [settings.embeddings.provider]: value });
            setSaved(false);
          }}
        />
        {pendingOtherKeys && <p className="pending-provider-keys" role="status">{tr("settings.pendingKeys")}</p>}
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
