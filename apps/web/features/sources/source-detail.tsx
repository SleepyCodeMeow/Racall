"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowSquareOut, X } from "@phosphor-icons/react";
import {
  api,
  originalFile,
  locationLabel,
  type Source,
  type Evidence,
} from "../../lib/api";
import { useI18n } from "../../lib/i18n";

type DocumentData = {
  source: Source;
  document: {
    elements: { text: string; page?: number; section?: string }[];
  } | null;
};
type Version = {
  version: string;
  title: string;
  type: string;
  created_at: string;
  current: boolean;
};

export function SourceDetail({
  notebook,
  source,
  evidence,
  close,
  refresh,
  report,
}: {
  notebook: string;
  source: Source;
  evidence?: Evidence;
  close: () => void;
  refresh: () => void;
  report: (message: string) => void;
}) {
  const { tr, locale, localize } = useI18n(),
    client = useQueryClient();
  const [picked, setPicked] = useState<string | undefined>(evidence?.version);
  const [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const input = useRef<HTMLInputElement>(null),
    anchor = useRef<HTMLDivElement>(null);
  const version = picked || source.version;
  const prefix = `/notebooks/${notebook}/sources/${source.id}`;
  const processing = [source.status, source.refresh_status].some(
    (s) => s === "queued" || s === "processing",
  );
  const versions = useQuery({
    queryKey: [
      "source-versions",
      notebook,
      source.id,
      source.version,
      source.refresh_status,
    ],
    queryFn: () => api<Version[]>(prefix + "/versions"),
  });
  const document = useQuery({
    queryKey: [
      "source-document",
      notebook,
      source.id,
      version,
      source.status,
      source.refresh_status,
    ],
    queryFn: () =>
      api<DocumentData>(prefix + (version ? `/versions/${version}` : "")),
  });
  const shown = document.data?.source || source;
  const archived = !!version && version !== source.version;
  useEffect(() => {
    setFileUrl("");
  }, [version]);
  useEffect(
    () => () => {
      if (fileUrl) URL.revokeObjectURL(fileUrl);
    },
    [fileUrl],
  );
  useEffect(() => {
    anchor.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [document.data, evidence]);
  const update = async (
    action: "replace" | "refresh" | "retry",
    file?: File,
  ) => {
    setBusy(true);
    setNotice("");
    try {
      let result: Source & { unchanged?: boolean };
      if (action === "replace" && file) {
        if (file.size > 25 * 1024 * 1024)
          throw new Error(tr("source.fileSize", { name: file.name }));
        const form = new FormData();
        form.append("file", file);
        result = await api(prefix, "PUT", form);
      } else
        result = await api(
          prefix + (action === "refresh" ? "/refresh" : "/reindex"),
          "POST",
        );
      if (result.unchanged) setNotice(tr("source.unchanged"));
      refresh();
      await client.invalidateQueries({
        queryKey: ["source-versions", notebook, source.id],
      });
    } catch (e) {
      report((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };
  return (
    <aside className="source-panel detail-panel">
      <div className="panel-heading">
        <span>{tr("source.original")}</span>
        <button
          className="icon-button"
          aria-label={tr("source.close")}
          onClick={close}
        >
          <X size={18} />
        </button>
      </div>
      <div className="detail-title">
        <span className="file-type">{shown.type.toUpperCase()}</span>
        <h2>{shown.title}</h2>
        {evidence && <div className="location">{locationLabel(evidence)}</div>}
        <label className="source-version-picker">
          {tr("source.version")}
          <select
            value={version || ""}
            onChange={(e) => setPicked(e.target.value)}
            disabled={versions.isPending}
          >
            {!versions.data && (
              <option value={version}>{tr("common.loading")}</option>
            )}
            {versions.data?.map((v) => (
              <option key={v.version} value={v.version}>
                {v.current
                  ? tr("source.currentVersion")
                  : tr("source.previousVersion")}{" "}
                · {new Date(v.created_at).toLocaleString(locale)}
              </option>
            ))}
          </select>
        </label>
        {versions.error && (
          <p className="source-error" role="alert">
            {versions.error.message}
          </p>
        )}
        <div className="source-version-actions">
          <button
            className="text-button"
            disabled={document.isPending || !!document.error}
            onClick={async () => {
              try {
                setFileUrl(await originalFile(notebook, shown, version));
              } catch (e) {
                report((e as Error).message);
              }
            }}
          >
            {tr("source.openOriginal")} <ArrowSquareOut size={15} />
          </button>
          {source.url ? (
            <button
              className="text-button"
              disabled={busy || processing}
              onClick={() => void update("refresh")}
            >
              {tr("source.refreshUrl")}
            </button>
          ) : (
            <button
              className="text-button"
              disabled={busy || processing}
              onClick={() => input.current?.click()}
            >
              {tr("source.replaceFile")}
            </button>
          )}
          <input
            className="hidden"
            aria-label={tr("source.replacementFile")}
            ref={input}
            type="file"
            accept=".pdf,.md,.txt,.docx"
            onChange={(e) => {
              if (e.target.files?.[0])
                void update("replace", e.target.files[0]);
            }}
          />
        </div>
        {fileUrl && shown.type !== "pdf" && (
          <a className="text-button" href={fileUrl} download={shown.title}>
            {tr("source.download")}
          </a>
        )}
        {processing && (
          <p className="muted" role="status">
            {source.refresh_status
              ? tr("source.updating")
              : tr("source.processing")}
          </p>
        )}
        {notice && (
          <p className="muted" role="status">
            {notice}
          </p>
        )}
        {(source.error || source.refresh_error) && (
          <div className="source-error" role="alert">
            <p>
              {source.refresh_error
                ? tr("source.updateFailed")
                : tr("source.failed")}
            </p>
            <p>{localize(source.refresh_error || source.error || "")}</p>
            <button
              className="text-button"
              disabled={busy || processing}
              onClick={() => void update("retry")}
            >
              {tr("common.retry")}
            </button>
          </div>
        )}
      </div>
      {archived && (
        <div className="draft-notice">
          <strong>{tr("source.previousVersion")}</strong>
          <p>{tr("source.versionChanged")}</p>
        </div>
      )}
      {document.error && (
        <div className="source-error" role="alert">
          <p>{document.error.message}</p>
          {evidence && (
            <>
              <strong>{tr("source.savedPassage")}</strong>
              <blockquote>{evidence.quote}</blockquote>
            </>
          )}
        </div>
      )}
      {fileUrl && shown.type === "pdf" ? (
        <iframe
          title={tr("source.pdf")}
          className="pdf-preview"
          src={`${fileUrl}#page=${evidence?.location.page || 1}`}
        />
      ) : (
        <div className="source-content">
          {document.isPending ? (
            <div className="skeleton h-40" />
          ) : !document.data?.document ? (
            <p className="muted">{tr("source.processingNotice")}</p>
          ) : (
            document.data.document.elements.map((element, i) => {
              const highlighted =
                !!evidence &&
                evidence.version === shown.version &&
                evidence.location.element === i &&
                element.text.slice(
                  evidence.location.offset_start,
                  evidence.location.offset_end,
                ) === evidence.quote;
              return (
                <div
                  key={i}
                  ref={highlighted ? anchor : undefined}
                  className={`source-element ${highlighted ? "highlighted" : ""}`}
                >
                  {(element.page || element.section) && (
                    <small>
                      {element.page
                        ? tr("source.page", { page: element.page })
                        : element.section}
                    </small>
                  )}
                  <p>
                    {highlighted && evidence ? (
                      <>
                        {element.text.slice(0, evidence.location.offset_start)}
                        <mark>{evidence.quote}</mark>
                        {element.text.slice(evidence.location.offset_end)}
                      </>
                    ) : (
                      element.text
                    )}
                  </p>
                </div>
              );
            })
          )}
        </div>
      )}
    </aside>
  );
}
