"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, Note, NoteDraft } from "../../lib/api";
import { useI18n } from "../../lib/i18n";

export function useNoteEditor(
  notebook: string,
  kind: "notes" | "artifacts",
  report: (s: string) => void,
) {
  const { tr } = useI18n();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: [kind, notebook],
    queryFn: () => api<Note[]>(`/notebooks/${notebook}/${kind}`),
  });
  const drafts = useQuery({
    queryKey: ["drafts", notebook],
    enabled: kind === "notes",
    queryFn: () => api<NoteDraft[]>(`/notebooks/${notebook}/drafts`),
  });
  const [current, setCurrent] = useState<Note | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [recovered, setRecovered] = useState(false);
  const currentRef = useRef<Note | null>(null);
  const dirtyRef = useRef(false);
  const draftId = useRef("");
  const task = useRef<Promise<boolean> | null>(null);
  const alive = useRef(true);
  const restored = useRef(false);
  const refresh = () => {
    void client.invalidateQueries({ queryKey: [kind, notebook] });
    void client.invalidateQueries({ queryKey: ["drafts", notebook] });
  };
  const select = (note: Note, draft?: NoteDraft) => {
    const changed = !!draft || (kind === "notes" && note.revision === "");
    currentRef.current = note;
    dirtyRef.current = changed;
    draftId.current = draft?.draft_id || crypto.randomUUID();
    setCurrent(note);
    setDirty(changed);
    setRecovered(!!draft);
    setBlocked(!!draft);
    setConflict(false);
  };
  useEffect(() => {
    if (kind !== "notes" || restored.current || !drafts.data || !query.data)
      return;
    restored.current = true;
    if (!currentRef.current && drafts.data.length)
      select(drafts.data[0].note, drafts.data[0]);
  }, [drafts.data, query.data, kind]);
  useEffect(() => {
    if (query.error || drafts.error)
      report((query.error || drafts.error)!.message);
  }, [query.error, drafts.error, report]);

  // Serialize saves; an older acknowledgement must never replace newer keystrokes.
  const persist = (): Promise<boolean> => {
    if (task.current) return task.current;
    if (!dirtyRef.current || !currentRef.current) return Promise.resolve(true);
    if (!currentRef.current.title.trim()) return Promise.resolve(false);
    const run = async () => {
      if (alive.current) setBusy(true);
      let attempted: Note | null = null;
      try {
        while (dirtyRef.current && currentRef.current) {
          const snapshot = currentRef.current;
          attempted = snapshot;
          if (!snapshot.title.trim()) return false;
          const result = await api<Note>(
            `/notebooks/${notebook}/notes/autosave`,
            "POST",
            {
              id: snapshot.id,
              title: snapshot.title,
              body: snapshot.body,
              revision: snapshot.revision ?? "",
              draft_id: draftId.current,
            },
          );
          const latest = currentRef.current;
          const unchanged =
            latest.title === snapshot.title && latest.body === snapshot.body;
          currentRef.current = unchanged
            ? result
            : { ...latest, revision: result.revision };
          dirtyRef.current = !unchanged;
          if (alive.current) {
            setCurrent(currentRef.current);
            setDirty(!unchanged);
            setBlocked(false);
            setConflict(false);
            setRecovered(false);
          }
          refresh();
        }
        return true;
      } catch (error) {
        if (alive.current) {
          // A failed older request must not strand text typed while it was pending.
          const newer = currentRef.current !== attempted;
          setBlocked(!newer);
          if (newer && currentRef.current)
            setCurrent({ ...currentRef.current });
          setConflict(error instanceof ApiError && error.status === 409);
        }
        report((error as Error).message);
        refresh();
        return false;
      } finally {
        task.current = null;
        if (alive.current) setBusy(false);
      }
    };
    task.current = run();
    return task.current;
  };
  const persistRef = useRef(persist);
  persistRef.current = persist;
  useEffect(() => {
    if (kind !== "notes" || !dirty || blocked || !current?.title.trim()) return;
    const timer = setTimeout(() => {
      void persistRef.current();
    }, 600);
    return () => clearTimeout(timer);
  }, [current, dirty, blocked, kind]);
  useEffect(() => {
    alive.current = true;
    const handler = (e: BeforeUnloadEvent) => {
      if (dirtyRef.current) {
        e.preventDefault();
        e.returnValue = "";
        void persistRef.current();
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => {
      alive.current = false;
      window.removeEventListener("beforeunload", handler);
    };
  }, []);
  // Navigation inside the app can unmount this editor. Flush while the service is alive.
  useEffect(
    () => () => {
      if (kind === "notes" && dirtyRef.current) void persistRef.current();
    },
    [kind],
  );
  const edit = (note: Note) => {
    currentRef.current = note;
    dirtyRef.current = true;
    setCurrent(note);
    setDirty(true);
    // Retry after a new edit, also refreshing the recovery draft on a conflict.
    // The original revision still protects the externally edited Markdown file.
    setBlocked(false);
  };
  const choose = async (note: Note, draft?: NoteDraft) => {
    if (dirtyRef.current && !(await persist())) return;
    select(note, draft);
  };
  const reload = async () => {
    if (!window.confirm(tr("notes.reloadConfirm"))) return;
    try {
      const notes = await api<Note[]>(`/notebooks/${notebook}/notes`);
      await api(`/notebooks/${notebook}/drafts/${draftId.current}`, "DELETE");
      dirtyRef.current = false;
      setDirty(false);
      setBlocked(false);
      setConflict(false);
      setRecovered(false);
      const saved = notes.find((n) => n.id === currentRef.current?.id);
      currentRef.current = saved || null;
      setCurrent(saved || null);
      refresh();
    } catch (error) {
      report((error as Error).message);
    }
  };
  const saveCopy = async () => {
    if (!currentRef.current) return;
    edit({ ...currentRef.current, id: crypto.randomUUID(), revision: "" });
    setConflict(false);
    setBlocked(false);
    await persist();
  };
  return {
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
  };
}
