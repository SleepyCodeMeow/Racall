import type { EmbeddingProviderId, EmbeddingSettings } from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import {
  embeddingProviders,
  needsApiKey,
  providerDefaults,
  providerNames,
} from "./providers";

export function EmbeddingConnection({
  settings,
  apiKey,
  disabled,
  selectProvider,
  editProfile,
  editKey,
}: {
  settings: EmbeddingSettings;
  apiKey: string;
  disabled: boolean;
  selectProvider: (provider: EmbeddingProviderId) => void;
  editProfile: (field: "base_url" | "model", value: string) => void;
  editKey: (value: string) => void;
}) {
  const { tr } = useI18n();
  return (
    <details className="embedding-settings">
      <summary>
        {tr("settings.semanticSearch")} <span className="optional">{tr("common.optional")}</span>
      </summary>
      <div className="grid gap-5">
        <p className="muted">{tr("settings.embeddingHint")}</p>
        <label>
          {tr("settings.embeddingProvider")}
          <select
            id="embedding-provider"
            value={settings.provider}
            disabled={disabled}
            onChange={(e) => selectProvider(e.target.value as EmbeddingProviderId)}
          >
            {embeddingProviders.map((id) => (
              <option key={id} value={id}>
                {id === "openai_compatible" ? tr("settings.customProvider") : providerNames[id]}
              </option>
            ))}
          </select>
        </label>
        <label>
          {tr("settings.embeddingApiUrl")}
          <input
            id="embedding-url"
            type="url"
            value={settings.base_url}
            disabled={disabled}
            onInvalid={(e) => e.currentTarget.closest("details")?.setAttribute("open", "")}
            onChange={(e) => editProfile("base_url", e.target.value)}
            placeholder={providerDefaults[settings.provider]}
          />
        </label>
        <label>
          {tr("settings.embedding")}
          <input
            id="embedding-model"
            value={settings.model}
            disabled={disabled}
            onChange={(e) => editProfile("model", e.target.value)}
            placeholder={tr("settings.embeddingPlaceholder")}
          />
        </label>
        <label>
          <span>
            {tr("settings.embeddingKey")} <span className="optional">{settings.has_key ? tr("settings.keySaved") : tr("settings.keyMissing")}</span>
          </span>
          <input
            id="embedding-api-key"
            type="password"
            value={apiKey}
            disabled={disabled}
            autoComplete="off"
            onChange={(e) => editKey(e.target.value)}
            placeholder={tr(needsApiKey(settings.provider) ? "settings.cloudKeyPlaceholder" : "settings.localKeyPlaceholder")}
          />
          <small>{tr("settings.embeddingKeyHint")}</small>
        </label>
      </div>
    </details>
  );
}
