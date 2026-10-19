"use client";
import { Check, Copy, TerminalWindow, X } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { useI18n } from "../../lib/i18n";
import { launchCommand, launchers } from "./catalog";

export function Apps({ report }: { report: (message: string) => void }) {
  const { tr } = useI18n();
  const [copied, setCopied] = useState<(typeof launchers)[number] | null>(null);
  const [copyFailure, setCopyFailure] = useState<(typeof launchers)[number] | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  async function copy(app: (typeof launchers)[number]) {
    clearTimeout(timer.current);
    setCopied(null);
    try {
      if (window.desktop?.copyLaunchCommand) await window.desktop.copyLaunchCommand(app.id);
      else await navigator.clipboard.writeText(launchCommand(app.id));
      setCopyFailure(null);
      setCopied(app);
      timer.current = setTimeout(() => setCopied(null), 6000);
    } catch {
      setCopyFailure(app);
      report(tr("apps.copyError"));
    }
  }
  return <section className="apps-page">
    <header className="workspace-header"><h1>{tr("apps.title")}</h1></header>
    <div className="apps-content">
      <div className="eyebrow">{tr("apps.withOllama")}</div>
      <h2>{tr("apps.heading")}</h2>
      <p className="apps-description">{tr("apps.description")}</p>
      <div className="launcher-grid">
        {launchers.map(app => <button key={app.id} type="button"
          className="launcher-button" title={launchCommand(app.id)}
          onClick={() => void copy(app)}>
          <span className={`launcher-mark ${app.color}`} aria-hidden="true">{app.mark}</span>
          <span>{app.name}</span>
          <Copy size={16} className="launcher-copy" aria-hidden="true" />
        </button>)}
      </div>
      {copyFailure && <div className="launch-command-fallback">
        <label>{tr("apps.command", { app: copyFailure.name })}<input readOnly spellCheck={false} value={launchCommand(copyFailure.id)} /></label>
        <p>{tr("apps.copyFallback")}</p>
      </div>}
      <p className="apps-hint"><TerminalWindow size={16} aria-hidden="true" />{tr("apps.hint")}</p>
      <p className="apps-prerequisite">{tr("apps.prerequisite")} <a href="https://docs.ollama.com/integrations" target="_blank" rel="noreferrer">{tr("apps.setup")}</a></p>
    </div>
    {copied && <aside className="launch-toast" role="status">
      <Check size={21} aria-hidden="true" />
      <div><strong>{tr("apps.copied")}</strong><span>{tr("apps.paste")}</span><code>{launchCommand(copied.id)}</code></div>
      <button type="button" className="icon-button" aria-label={tr("common.close")} onClick={() => setCopied(null)}><X size={16} /></button>
    </aside>}
  </section>;
}
