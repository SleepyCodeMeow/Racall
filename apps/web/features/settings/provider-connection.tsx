import type { ProviderId, ProviderProfile } from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import {
  needsApiKey,
  providerDefaults,
  providerHints,
  providerMode,
} from "./providers";

export function ProviderConnection({
  provider,
  profile,
  apiKey,
  disabled,
  selectProvider,
  editProfile,
  editKey,
}: {
  provider: ProviderId;
  profile: ProviderProfile;
  apiKey: string;
  disabled: boolean;
  selectProvider: (provider: ProviderId) => void;
  editProfile: (field: "base_url" | "model", value: string) => void;
  editKey: (value: string) => void;
}) {
  const { tr } = useI18n();
  const isOllama = provider === "ollama" || provider === "ollama_cloud";
  return (
    <>
      <div className="segmented provider-picker" role="group" aria-label={tr("settings.provider")}>
        {([
          ["openai", "OpenAI"],
          ["anthropic", "Claude"],
          ["ollama", "Ollama"],
          ["llama_cpp", "llama.cpp"],
        ] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            disabled={disabled}
            aria-pressed={id === "ollama" ? isOllama : provider === id}
            className={(id === "ollama" ? isOllama : provider === id) ? "selected" : ""}
            onClick={() => selectProvider(id === "ollama" && isOllama ? provider : id)}
          >
            {label}
          </button>
        ))}
      </div>
      <button
        className="text-button custom-provider"
        type="button"
        disabled={disabled}
        aria-pressed={provider === "openai_compatible"}
        onClick={() => selectProvider("openai_compatible")}
      >
        {tr("settings.customProvider")}
      </button>
      {isOllama && (
        <div className="segmented ollama-mode" role="group" aria-label={tr("settings.ollamaMode")}>
          {(["ollama", "ollama_cloud"] as const).map((id) => (
            <button
              key={id}
              type="button"
              disabled={disabled}
              aria-pressed={provider === id}
              className={provider === id ? "selected" : ""}
              onClick={() => selectProvider(id)}
            >
              {tr(id === "ollama" ? "settings.local" : "settings.cloud")}
            </button>
          ))}
        </div>
      )}
      <p className="provider-hint">
        <span className="connection-kind">{tr(providerMode(provider))}</span>
        {tr(providerHints[provider])}
      </p>
      <label>
        {tr("settings.apiUrl")}
        <input
          id="provider-url"
          type="url"
          value={profile.base_url}
          required
          disabled={disabled}
          onChange={(e) => editProfile("base_url", e.target.value)}
          placeholder={providerDefaults[provider]}
        />
      </label>
      <label>
        {tr("settings.model")}
        <input
          id="answer-model"
          value={profile.model}
          disabled={disabled}
          onChange={(e) => editProfile("model", e.target.value)}
          placeholder={tr("settings.modelPlaceholder")}
          required
        />
      </label>
      <label>
        <span>
          {tr("settings.key")} <span className="optional">{profile.has_key ? tr("settings.keySaved") : tr("settings.keyMissing")}</span>
        </span>
        <input
          id="provider-api-key"
          type="password"
          value={apiKey}
          autoComplete="off"
          disabled={disabled}
          onChange={(e) => editKey(e.target.value)}
          placeholder={tr(needsApiKey(provider) ? "settings.cloudKeyPlaceholder" : "settings.localKeyPlaceholder")}
        />
        <small>{tr("settings.keyKeepHint")}</small>
      </label>
    </>
  );
}
