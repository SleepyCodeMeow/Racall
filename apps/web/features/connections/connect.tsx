"use client";
import { useI18n } from "../../lib/i18n";
import { useEffect, useState } from "react";
import { Check, Copy } from "@phosphor-icons/react";
import { api } from "../../lib/api";

export function Connect({
  notebook,
  report,
}: {
  notebook: string;
  report: (s: string) => void;
}) {
  const { tr, localize } = useI18n();
  const [config, setConfig] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    api<{ mcpServers: object }>(`/notebooks/${notebook}/connection`)
      .then((c) =>
        setConfig(JSON.stringify({ mcpServers: c.mcpServers }, null, 2)),
      )
      .catch((e) => report(e.message));
  }, [notebook, report]);
  return (
    <div className="page-content connect">
      <div className="eyebrow">{tr("connect.eyebrow")}</div>
      <h2>
        {tr("connect.title1")}
        <br />
        {tr("connect.title2")}
      </h2>
      <p className="muted">{tr("connect.description")}</p>
      <div className="permission-row">
        <Check size={18} />
        {tr("connect.search")}
      </div>
      <div className="permission-row">
        <Check size={18} />
        {tr("connect.read")}
      </div>
      <div className="permission-row muted">{tr("connect.readOnly")}</div>
      <h3 className="mt-8 mb-3">{tr("connect.config")}</h3>
      <p className="muted mb-4">{tr("connect.instructions")}</p>
      <pre className="config-block">{config || tr("connect.loading")}</pre>
      <button
        className="secondary mt-4"
        onClick={() =>
          navigator.clipboard
            .writeText(config)
            .then(() => setCopied(true))
            .catch(() => report(tr("error.clipboard")))
        }
      >
        <Copy size={17} />
        {copied ? tr("common.copied") : tr("common.copy")}
      </button>
      <div className="notice mt-8">{tr("connect.remoteNotice")}</div>
    </div>
  );
}
