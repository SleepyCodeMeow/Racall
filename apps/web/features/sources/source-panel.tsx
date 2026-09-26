"use client";
import { useI18n } from "../../lib/i18n";
import { useRef, useState } from "react";
import { SourceDetail } from "./source-detail";
import {
  ArrowClockwise,
  CheckCircle,
  FilePdf,
  FileText,
  LinkSimple,
  Plus,
  UploadSimple,
} from "@phosphor-icons/react";
import { api, Evidence, Source } from "../../lib/api";

export function SourcePanel({
  notebook,
  sources,
  selected,
  select,
  refresh,
  report,
}: {
  notebook: string;
  sources: Source[];
  selected: { source: Source; evidence?: Evidence } | null;
  select: (s: { source: Source; evidence?: Evidence } | null) => void;
  refresh: () => void;
  report: (s: string) => void;
}) {
  const { tr, plural, localize } = useI18n();
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [showUrl, setShowUrl] = useState(false);
  const [url, setUrl] = useState("");
  const [drag, setDrag] = useState(false);
  const upload = async (files: FileList | File[]) => {
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        if (file.size > 25 * 1024 * 1024)
          throw new Error(tr("source.fileSize", { name: file.name }));
        const form = new FormData();
        form.append("file", file);
        await api(`/notebooks/${notebook}/sources`, "POST", form);
        refresh();
      }
    } catch (e) {
      report((e as Error).message);
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };
  if (selected)
    return (
      <SourceDetail
        key={`${selected.source.id}:${selected.evidence?.id || ""}`}
        notebook={notebook}
        source={
          sources.find((s) => s.id === selected.source.id) || selected.source
        }
        evidence={selected.evidence}
        close={() => select(null)}
        refresh={refresh}
        report={report}
      />
    );
  return (
    <aside
      className="source-panel"
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        if (!busy) upload(e.dataTransfer.files);
      }}
    >
      <div className="panel-heading">
        <span>
          {tr("source.title")} <span className="count">{sources.length}</span>
        </span>
        <button
          className="icon-button"
          aria-label={tr("source.add")}
          onClick={() => fileInput.current?.click()}
          disabled={busy}
        >
          <Plus size={18} />
        </button>
      </div>
      <div className="p-5">
        <button
          className={`upload-zone ${drag ? "dragging" : ""}`}
          onClick={() => fileInput.current?.click()}
          disabled={busy}
        >
          <UploadSimple size={26} />
          <strong>
            {busy ? tr("source.importing") : tr("source.addMaterials")}
          </strong>
          <span>{tr("source.drop")}</span>
          <small>{tr("source.formats")}</small>
        </button>
        <input
          ref={fileInput}
          className="hidden"
          type="file"
          multiple
          accept=".pdf,.md,.txt,.docx"
          onChange={(e) => {
            if (e.target.files) upload(e.target.files);
          }}
        />
        <button
          className="secondary w-full mt-3"
          onClick={() => setShowUrl(!showUrl)}
        >
          <LinkSimple size={17} />
          {tr("source.addLink")}
        </button>
        {showUrl && (
          <form
            className="mt-4 grid gap-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                await api(`/notebooks/${notebook}/urls`, "POST", { url });
                setUrl("");
                setShowUrl(false);
                refresh();
              } catch (e) {
                report((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              {tr("source.url")}
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                placeholder="https://…"
              />
            </label>
            <button className="primary" disabled={busy}>
              {busy ? tr("common.loading") : tr("source.import")}
            </button>
          </form>
        )}
      </div>
      <div className="source-list">
        {sources.length === 0 ? (
          <p className="empty-small">
            {tr("source.empty1")}
            <br />
            {tr("source.empty2")}
          </p>
        ) : (
          sources.map((source) => (
            <div key={source.id} className="source-row">
              <button
                className="source-open"
                onClick={() => select({ source })}
              >
                <span className="file-icon">
                  {source.type === "pdf" ? (
                    <FilePdf size={23} />
                  ) : (
                    <FileText size={23} />
                  )}
                </span>
                <span className="min-w-0">
                  <strong>{source.title}</strong>
                  <small>
                    {source.refresh_status === "queued" ||
                    source.refresh_status === "processing"
                      ? tr("source.updating")
                      : source.status === "ready"
                        ? tr("source.stats", {
                            chunks: source.chunks,
                            size: Math.max(1, Math.round(source.size / 1024)),
                          })
                        : source.status === "error"
                          ? tr("source.failed")
                          : tr("source.processing")}
                  </small>
                </span>
                {source.status === "ready" ? (
                  <CheckCircle className="ready-icon" size={15} />
                ) : source.status !== "error" ? (
                  <span className="pulse-dot" />
                ) : null}
              </button>
              {(source.error || source.refresh_error) && (
                <div className="source-error">
                  <p>{localize(source.refresh_error || source.error || "")}</p>
                  <button
                    className="text-button"
                    onClick={() =>
                      api(
                        `/notebooks/${notebook}/sources/${source.id}/reindex`,
                        "POST",
                      )
                        .then(refresh)
                        .catch((e) => report(e.message))
                    }
                  >
                    {tr("common.retry")}
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
      <div className="panel-footer">
        <span className="status-dot" />
        {plural(
          "source.ready",
          sources.filter((s) => s.status === "ready").length,
        )}
        <button
          title={tr("source.reindex")}
          aria-label={tr("source.reindex")}
          className="icon-button ml-auto"
          onClick={() =>
            api(`/notebooks/${notebook}/reindex`, "POST")
              .then(refresh)
              .catch((e) => report(e.message))
          }
        >
          <ArrowClockwise size={17} />
        </button>
      </div>
    </aside>
  );
}
