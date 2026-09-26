"use client";
import { useState } from "react";
import { FileText, Plus } from "@phosphor-icons/react";
import { useI18n } from "../../lib/i18n";
import { Markdown } from "../../components/markdown";
import { useNoteEditor } from "./use-note-editor";

export function Notes({
  notebook,
  kind,
  report,
}: {
  notebook: string;
  kind: "notes" | "artifacts";
  report: (s: string) => void;
}) {
  const { tr } = useI18n();
  const [preview, setPreview] = useState(false);
  const {
    query,
    drafts,
    current,
    dirty,
    busy,
    blocked,
    conflict,
    recovered,
    draftId,
    choose,
    edit,
    persist,
    reload,
    saveCopy,
  } = useNoteEditor(notebook, kind, report);
  return (
    <div className="notes-layout">
      <div className="note-picker">
        <div className="flex justify-between items-center mb-5">
          <h2>{kind === "notes" ? tr("notes.title") : tr("nav.artifacts")}</h2>
          {kind === "notes" && (
            <button
              className="secondary"
              disabled={busy || drafts.isPending || query.isPending}
              onClick={() =>
                void choose({
                  id: crypto.randomUUID(),
                  title: tr("notes.new"),
                  body: "",
                  revision: "",
                })
              }
            >
              <Plus size={16} />
              {tr("common.create")}
            </button>
          )}
        </div>
        {query.isPending && <div className="skeleton h-20" />}
        {query.data?.length === 0 && (
          <p className="muted">
            {kind === "notes" ? tr("notes.empty") : tr("reports.empty")}
          </p>
        )}
        <div className="note-tabs">
          {query.data?.map((note) => (
            <button
              key={note.id}
              disabled={busy}
              className={current?.id === note.id ? "selected" : ""}
              onClick={() => {
                if (current?.id !== note.id) void choose(note);
              }}
            >
              <FileText size={17} />
              {note.title}
            </button>
          ))}
        </div>
        {kind === "notes" && !!drafts.data?.length && (
          <div className="note-tabs recovered-drafts">
            {drafts.data.map((d) => (
              <button
                key={d.draft_id}
                disabled={busy}
                onClick={() => {
                  if (draftId.current !== d.draft_id) void choose(d.note, d);
                }}
              >
                {tr("notes.recoveredTitle", { title: d.note.title })}
              </button>
            ))}
          </div>
        )}
      </div>
      {current ? (
        <div className="note-editor">
          {kind === "notes" && (conflict || recovered || blocked) && (
            <div className="draft-notice" role="status">
              <p>
                {tr(
                  conflict
                    ? "notes.conflict"
                    : recovered
                      ? "notes.recovered"
                      : "notes.saveFailed",
                )}
              </p>
              <div>
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => void saveCopy()}
                >
                  {tr("notes.saveCopy")}
                </button>
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => void reload()}
                >
                  {tr("notes.reload")}
                </button>
              </div>
            </div>
          )}
          <div className="editor-toolbar">
            {kind === "notes" ? (
              <>
                <button
                  className="text-button"
                  onClick={() => setPreview(!preview)}
                >
                  {preview ? tr("common.edit") : tr("common.preview")}
                </button>
                <span className="save-status" aria-live="polite">
                  {busy
                    ? tr("common.saving")
                    : dirty
                      ? tr(
                          blocked
                            ? "notes.needsAttention"
                            : "notes.unsavedStatus",
                        )
                      : tr("notes.autosave")}
                </span>
                <button
                  className="primary"
                  disabled={busy || !current.title.trim()}
                  onClick={() => void persist()}
                >
                  {busy
                    ? tr("common.saving")
                    : !dirty && !!current.revision
                      ? tr("common.saved")
                      : tr("common.save")}
                </button>
              </>
            ) : (
              <span className="eyebrow">{tr("research.report")}</span>
            )}
          </div>
          {preview || kind === "artifacts" ? (
            <Markdown
              text={`# ${current.title}\n\n${current.body}`}
              onWiki={(title) => {
                const note = query.data?.find((n) => n.title === title);
                if (note) void choose(note);
                else report(tr("notes.notFound", { title }));
              }}
            />
          ) : (
            <>
              <input
                className="note-title"
                aria-label={tr("notes.titleLabel")}
                maxLength={160}
                value={current.title}
                onChange={(e) => edit({ ...current, title: e.target.value })}
              />
              <textarea
                className="markdown-editor"
                aria-label={tr("notes.bodyLabel")}
                maxLength={1000000}
                value={current.body}
                placeholder={tr("notes.placeholder")}
                onChange={(e) => edit({ ...current, body: e.target.value })}
              />
            </>
          )}
        </div>
      ) : (
        <div className="editor-empty">
          <FileText size={40} weight="light" />
          <p>
            {kind === "notes"
              ? tr("notes.emptySelection")
              : tr("reports.emptySelection")}
          </p>
        </div>
      )}
    </div>
  );
}
