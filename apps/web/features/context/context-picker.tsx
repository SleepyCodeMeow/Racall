"use client";
import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CaretDown, Files } from "@phosphor-icons/react";
import { api, ContextSelection, Note, Source } from "../../lib/api";
import { useI18n } from "../../lib/i18n";

export const allMaterials = (): ContextSelection => ({ source_ids: null, note_ids: [] });
export const copySelection = (value: ContextSelection): ContextSelection => ({
  source_ids: value.source_ids === null ? null : [...value.source_ids],
  note_ids: [...value.note_ids],
});

export function ContextPicker({ notebook, value, onChange, disabled = false, report }: {
  notebook: string;
  value: ContextSelection;
  onChange: (selection: ContextSelection) => void | Promise<void>;
  disabled?: boolean;
  report: (message: string) => void;
}) {
  const { tr } = useI18n();
  const root = useRef<HTMLDetailsElement>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const changing = useRef(false);
  const sources = useQuery({ queryKey: ["sources", notebook], enabled: open,
    queryFn: () => api<Source[]>(`/notebooks/${notebook}/sources`) });
  const notes = useQuery({ queryKey: ["notes", notebook], enabled: open,
    queryFn: () => api<Note[]>(`/notebooks/${notebook}/notes`) });
  const ready = sources.data?.filter(source => source.status === "ready") || [];
  const selectedCount = value.source_ids === null ? ready.length : value.source_ids.length;
  const locked = disabled || saving;
  const change = async (selection: ContextSelection) => {
    if (disabled || changing.current) return;
    changing.current = true;
    setSaving(true);
    try { await onChange(selection); }
    catch (error) { report((error as Error).message); }
    finally { changing.current = false; setSaving(false); }
  };
  return <details className="context-picker" ref={root}
    onToggle={event => setOpen(event.currentTarget.open)}
    onKeyDown={event => {
      if (event.key === "Escape") {
        event.preventDefault(); event.stopPropagation();
        if (root.current) root.current.open = false;
        root.current?.querySelector("summary")?.focus();
      }
    }}>
    <summary aria-label={tr("context.configure")} aria-disabled={disabled}
      onClick={event => { if (disabled) event.preventDefault(); }}>
      <Files size={15} />
      <span>{value.source_ids === null
        ? tr("context.allSummary", { notes: value.note_ids.length })
        : tr("context.summary", { sources: selectedCount, notes: value.note_ids.length })}</span>
      <CaretDown size={12} />
    </summary>
    <div className="context-menu" aria-busy={saving}>
      <div className="context-menu-heading"><strong>{tr("context.title")}</strong>
        <button type="button" className="text-button" disabled={locked}
          onClick={() => void change({ source_ids: [], note_ids: [] })}>{tr("context.clear")}</button></div>
      <p className="muted">{tr("context.hint")}</p>
      {sources.error || notes.error ? <p role="alert" className="context-error">
        {tr("context.loadError")} <button type="button" className="text-button"
          onClick={() => { void sources.refetch(); void notes.refetch(); }}>{tr("common.retry")}</button>
      </p> : null}
      <fieldset disabled={locked}>
        <legend>{tr("context.sources")}</legend>
        <label className="context-choice context-all"><input type="checkbox" checked={value.source_ids === null}
          onChange={event => void change({ ...copySelection(value), source_ids: event.target.checked ? null : [] })} />
          <span>{tr("context.allSources")}</span></label>
        {sources.isPending ? <p className="muted">{tr("common.loading")}</p> : !ready.length
          ? <p className="muted">{tr("context.noSources")}</p>
          : ready.map(source => <label className="context-choice" key={source.id}>
            <input type="checkbox" data-source-id={source.id} checked={value.source_ids === null || value.source_ids.includes(source.id)}
              onChange={event => {
                const ids = value.source_ids === null ? ready.map(item => item.id) : value.source_ids;
                void change({ ...copySelection(value), source_ids: event.target.checked
                  ? [...new Set([...ids, source.id])] : ids.filter(id => id !== source.id) });
              }} /><span>{source.title}</span>
          </label>)}
      </fieldset>
      <fieldset disabled={locked}>
        <legend>{tr("context.notes")}</legend>
        {notes.isPending ? <p className="muted">{tr("common.loading")}</p> : !notes.data?.length
          ? <p className="muted">{tr("context.noNotes")}</p>
          : notes.data.map(note => <label className="context-choice" key={note.id}>
            <input type="checkbox" data-note-id={note.id} checked={value.note_ids.includes(note.id)}
              onChange={event => void change({ ...copySelection(value), note_ids: event.target.checked
                ? [...value.note_ids, note.id] : value.note_ids.filter(id => id !== note.id) })} />
            <span>{note.title}</span>
          </label>)}
      </fieldset>
      {value.source_ids?.length === 0 && value.note_ids.length === 0
        ? <p className="context-empty" role="status">{tr("context.empty")}</p> : null}
      <p className="context-footnote">{saving ? tr("common.saving") : tr("context.savedNotesOnly")}</p>
      <button type="button" className="secondary context-done" disabled={saving}
        onClick={() => { if (root.current) root.current.open = false; root.current?.querySelector("summary")?.focus(); }}>
        {tr("common.close")}
      </button>
    </div>
  </details>;
}
