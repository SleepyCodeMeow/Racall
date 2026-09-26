"use client";
import { useI18n } from "../../lib/i18n";
import { useEffect, useRef, useState } from "react";
import {
  ArrowClockwise,
  ArrowSquareOut,
  CheckCircle,
  FilePdf,
  FileText,
  LinkSimple,
  Plus,
  UploadSimple,
  X,
} from "@phosphor-icons/react";
import {
  api,
  Evidence,
  locationLabel,
  originalFile,
  Source,
} from "../../lib/api";

type DocumentData = {
  source: Source;
  document: {
    elements: { text: string; page?: number; section?: string; type: string }[];
  } | null;
};
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
  const [document, setDocument] = useState<DocumentData>();
  const [fileUrl, setFileUrl] = useState("");
  const [drag, setDrag] = useState(false);
  const anchor = useRef<HTMLDivElement>(null);
  useEffect(() => {
    setDocument(undefined);
    setFileUrl("");
    if (!selected) return;
    let active = true;
    api<DocumentData>(`/notebooks/${notebook}/sources/${selected.source.id}`)
      .then((d) => {
        if (active) setDocument(d);
      })
      .catch((e) => report(e.message));
    return () => {
      active = false;
    };
  }, [selected?.source.id, notebook, report]);
  useEffect(() => {
    anchor.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [document, selected?.evidence]);
  useEffect(
    () => () => {
      if (fileUrl) URL.revokeObjectURL(fileUrl);
    },
    [fileUrl],
  );
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
      <aside className="source-panel detail-panel">
        <div className="panel-heading">
          <span>{tr("source.original")}</span>
          <button
            className="icon-button"
            aria-label={tr("source.close")}
            onClick={() => select(null)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="detail-title">
          <span className="file-type">
            {selected.source.type.toUpperCase()}
          </span>
          <h2>{selected.source.title}</h2>
          {selected.evidence && (
            <div className="location">{locationLabel(selected.evidence)}</div>
          )}
          <button
            className="text-button"
            onClick={async () => {
              try {
                setFileUrl(await originalFile(notebook, selected.source));
              } catch (e) {
                report((e as Error).message);
              }
            }}
          >
            {tr("source.openOriginal")} <ArrowSquareOut size={15} />
          </button>
          {fileUrl && selected.source.type !== "pdf" && (
            <a
              className="text-button"
              href={fileUrl}
              download={selected.source.title}
            >
              {tr("source.download")}
            </a>
          )}
        </div>
        {selected.evidence &&
          selected.evidence.version !==
            (document?.source.version || selected.source.version) && (
            <div className="draft-notice">
              <strong>{tr("source.savedPassage")}</strong>
              <p>{tr("source.versionChanged")}</p>
              <blockquote>{selected.evidence.quote}</blockquote>
            </div>
          )}
        {fileUrl && selected.source.type === "pdf" ? (
          <iframe
            title={tr("source.pdf")}
            className="pdf-preview"
            src={`${fileUrl}#page=${selected.evidence?.location.page || 1}`}
          />
        ) : (
          <div className="source-content">
            {!document ? (
              <div className="skeleton h-40" />
            ) : !document.document ? (
              <p className="muted">{tr("source.processingNotice")}</p>
            ) : (
              document.document.elements.map((element, i) => {
                const e = selected.evidence;
                const highlighted =
                  e?.version === document.source.version &&
                  e?.location.element === i;
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
                      {highlighted && e ? (
                        <>
                          {element.text.slice(0, e.location.offset_start)}
                          <mark>
                            {element.text.slice(
                              e.location.offset_start,
                              e.location.offset_end,
                            )}
                          </mark>
                          {element.text.slice(e.location.offset_end)}
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
                    {source.status === "ready"
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
              {source.error && (
                <div className="source-error">
                  <p>{localize(source.error)}</p>
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
