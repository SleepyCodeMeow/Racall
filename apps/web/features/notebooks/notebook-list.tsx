"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  DotsThree,
  Notebook as NotebookIcon,
  Trash,
} from "@phosphor-icons/react";
import { api, type Notebook } from "../../lib/api";
import { settlePendingEdits } from "../../lib/pending-edits";
import { useI18n } from "../../lib/i18n";
import { Modal } from "../../components/modal";

export function NotebookList({
  items,
  pending,
  active,
  select,
  removed,
  report,
}: {
  items?: Notebook[];
  pending: boolean;
  active: string;
  select: (id: string) => void;
  removed: (id: string) => void;
  report: (message: string) => void;
}) {
  const { tr } = useI18n(),
    client = useQueryClient();
  const [editing, setEditing] = useState<Notebook | null>(null);
  const [title, setTitle] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [trash, setTrash] = useState(false);
  const [busy, setBusy] = useState(false);
  const deleted = useQuery({
    queryKey: ["notebook-trash"],
    queryFn: () => api<Notebook[]>("/notebooks/trash"),
    enabled: trash,
  });
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ["notebooks"] });
    await client.invalidateQueries({ queryKey: ["notebook-trash"] });
  };
  const guard = async () => {
    if (await settlePendingEdits()) return true;
    report(tr("notebook.unsaved"));
    return false;
  };
  return (
    <>
      <nav className="notebook-list" aria-label={tr("nav.notebooks")}>
        {pending ? (
          <div className="skeleton h-10 m-3" />
        ) : (
          items?.map((n) => (
            <div className="notebook-entry" key={n.id}>
              <button
                className={active === n.id ? "selected" : ""}
                onClick={async () => {
                  if (await guard()) select(n.id);
                }}
              >
                <NotebookIcon size={16} />
                <span>{n.title}</span>
              </button>
              <button
                className="notebook-options"
                aria-label={tr("notebook.manage", { title: n.title })}
                onClick={() => {
                  setEditing(n);
                  setTitle(n.title);
                  setConfirm(false);
                }}
              >
                <DotsThree size={20} />
              </button>
            </div>
          ))
        )}
      </nav>
      <button
        className="notebook-trash-link text-button"
        onClick={() => setTrash(true)}
      >
        <Trash size={15} />
        {tr("notebook.trash")}
      </button>
      {editing && (
        <Modal
          title={
            confirm ? tr("notebook.deleteTitle") : tr("notebook.manageTitle")
          }
          close={() => setEditing(null)}
          busy={busy}
        >
          {confirm ? (
            <>
              <p className="muted">
                {tr("notebook.deleteDescription", { title: editing.title })}
              </p>
              <div className="management-actions">
                <button
                  className="secondary"
                  data-initial-focus
                  disabled={busy}
                  onClick={() => setConfirm(false)}
                >
                  {tr("common.cancel")}
                </button>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      if (!(await guard())) return;
                      await api(`/notebooks/${editing.id}`, "DELETE");
                      client.setQueryData<Notebook[]>(["notebooks"], (old) =>
                        old?.filter((n) => n.id !== editing.id),
                      );
                      removed(editing.id);
                      // Remove queries carrying content from the now-trashed notebook.
                      client.removeQueries({
                        predicate: (q) => q.queryKey.includes(editing.id),
                      });
                      await refresh();
                      setEditing(null);
                    } catch (e) {
                      report((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  {tr("notebook.moveToTrash")}
                </button>
              </div>
            </>
          ) : (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                try {
                  await api(`/notebooks/${editing.id}`, "PUT", {
                    title: title.trim(),
                  });
                  await refresh();
                  setEditing(null);
                } catch (e) {
                  report((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label>
                {tr("notebook.name")}
                <input
                  data-initial-focus
                  required
                  maxLength={160}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <div className="management-actions">
                <button
                  type="button"
                  className="text-button"
                  disabled={busy}
                  onClick={() => setConfirm(true)}
                >
                  {tr("notebook.moveToTrash")}
                </button>
                <button className="primary" disabled={busy || !title.trim()}>
                  {tr("common.save")}
                </button>
              </div>
            </form>
          )}
        </Modal>
      )}
      {trash && (
        <Modal
          title={tr("notebook.trash")}
          close={() => setTrash(false)}
          busy={busy}
        >
          <p className="muted">{tr("notebook.trashDescription")}</p>
          {deleted.isPending && <p>{tr("common.loading")}</p>}
          {deleted.error && <p role="alert">{deleted.error.message}</p>}
          {deleted.data?.length === 0 && (
            <p className="muted">{tr("notebook.trashEmpty")}</p>
          )}
          <div className="trash-list">
            {deleted.data?.map((n) => (
              <div key={n.id}>
                <span>{n.title}</span>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      if (!(await guard())) return;
                      await api(`/notebooks/${n.id}/restore`, "POST");
                      await refresh();
                      select(n.id);
                      setTrash(false);
                    } catch (e) {
                      report((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  {tr("notebook.restore")}
                </button>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </>
  );
}
