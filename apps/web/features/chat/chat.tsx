"use client";
import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  FileText,
  MagnifyingGlass,
  Plus,
  Sparkle,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  ChatThread,
  ChatTurn,
  Evidence,
  locationLabel,
} from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import { AnswerView } from "./answer-view";
import { ChatActions } from "./chat-actions";

type Props = {
  notebook: string;
  count: number;
  cite: (e: Evidence) => void;
  report: (s: string) => void;
  settings: () => void;
  openSources: () => void;
  navigate: (id: string) => void;
};
export function Chat({
  notebook,
  count,
  cite,
  report,
  settings,
  openSources,
  navigate,
}: Props) {
  const { tr } = useI18n();
  const client = useQueryClient();
  const [thread, setThread] = useState("");
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"ask" | "search">("ask");
  const [rename, setRename] = useState<string | null>(null);
  const threadsKey = ["chats", notebook];
  const threadKey = ["chat", notebook, thread];
  const threads = useQuery({
    queryKey: threadsKey,
    queryFn: () => api<ChatThread[]>(`/notebooks/${notebook}/chats`),
  });
  const selected = useQuery({
    queryKey: threadKey,
    enabled: !!thread,
    queryFn: () => api<ChatThread>(`/notebooks/${notebook}/chats/${thread}`),
    refetchInterval: (q) =>
      q.state.data?.turns.some((t) => t.status === "running") ? 1000 : false,
  });
  useEffect(() => {
    if (!thread && threads.data?.length) setThread(threads.data[0].id);
  }, [thread, threads.data]);
  useEffect(() => {
    if (threads.error || selected.error)
      report((threads.error || selected.error)!.message);
  }, [threads.error, selected.error, report]);
  const turns = selected.data?.turns || [];
  const pending = busy || turns.some((t) => t.status === "running");
  const loading = threads.isPending || (!!thread && selected.isPending);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, pending]);
  const refresh = () => client.invalidateQueries({ queryKey: threadsKey });
  const create = async (title: string) => {
    const item = await api<ChatThread>(`/notebooks/${notebook}/chats`, "POST", {
      title,
    });
    client.setQueryData(["chat", notebook, item.id], item);
    setThread(item.id);
    setRename(null);
    await refresh();
    return item.id;
  };
  const send = async () => {
    if (!question.trim() || pending || loading) return;
    setBusy(true);
    const q = question.trim();
    let id = thread;
    try {
      if (!id) id = await create(q.slice(0, 160));
      const key = ["chat", notebook, id];
      const request_id = crypto.randomUUID();
      const optimistic: ChatTurn = {
        id: request_id,
        question: q,
        mode,
        status: "running",
      };
      client.setQueryData<ChatThread>(key, (old) =>
        old ? { ...old, turns: [...old.turns, optimistic] } : old,
      );
      await api<ChatTurn>(`/notebooks/${notebook}/chats/${id}/turns`, "POST", {
        question: q,
        mode,
        request_id,
      });
      setQuestion("");
    } catch (error) {
      report((error as Error).message);
    } finally {
      if (id)
        await client.invalidateQueries({ queryKey: ["chat", notebook, id] });
      await refresh();
      setBusy(false);
    }
  };
  return (
    <div className="chat-workspace">
      <div className="chat-history-bar">
        <select
          aria-label={tr("chat.history")}
          value={thread}
          disabled={pending || loading}
          onChange={(e) => {
            setThread(e.target.value);
            setRename(null);
            setQuestion("");
          }}
        >
          {!threads.data?.length && <option value="">{tr("chat.new")}</option>}
          {threads.data?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.title}
            </option>
          ))}
        </select>
        <button
          className="text-button"
          disabled={pending || loading}
          onClick={async () => {
            setBusy(true);
            try {
              await create(tr("chat.new"));
              setQuestion("");
            } catch (e) {
              report((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Plus size={15} />
          {tr("chat.new")}
        </button>
        {!!thread && (
          <>
            <button
              className="text-button"
              disabled={pending || loading}
              onClick={() => setRename(selected.data?.title || "")}
            >
              {tr("common.rename")}
            </button>
            <button
              className="text-button"
              disabled={pending || loading}
              onClick={async () => {
                if (!window.confirm(tr("chat.deleteConfirm"))) return;
                setBusy(true);
                try {
                  await api(`/notebooks/${notebook}/chats/${thread}`, "DELETE");
                  client.removeQueries({ queryKey: threadKey });
                  await refresh();
                  setThread("");
                  setQuestion("");
                  setRename(null);
                } catch (e) {
                  report((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {tr("common.delete")}
            </button>
          </>
        )}
      </div>
      {rename !== null && (
        <form
          className="chat-rename"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              const item = await api<ChatThread>(
                `/notebooks/${notebook}/chats/${thread}`,
                "PUT",
                { title: rename.trim() },
              );
              client.setQueryData(threadKey, item);
              setRename(null);
              await refresh();
            } catch (error) {
              report((error as Error).message);
            }
          }}
        >
          <input
            autoFocus
            aria-label={tr("chat.name")}
            maxLength={160}
            value={rename}
            onChange={(e) => setRename(e.target.value)}
          />
          <button className="secondary" disabled={!rename.trim()}>
            {tr("common.save")}
          </button>
          <button
            type="button"
            className="text-button"
            onClick={() => setRename(null)}
          >
            {tr("common.cancel")}
          </button>
        </form>
      )}
      <div
        className={`chat-layout ${!turns.length && !pending ? "is-empty" : ""}`}
      >
        <div className="chat-scroll">
          {loading ? (
            <p className="muted">{tr("common.loading")}</p>
          ) : (
            !turns.length &&
            !pending && (
              <div className="chat-welcome">
                <div className="welcome-heading">
                  <img src="/brand/raccoon.png" width="46" height="46" alt="" />
                  <h2>{tr("chat.title")}</h2>
                </div>
                <p>{count ? tr("chat.description") : tr("chat.start")}</p>
              </div>
            )
          )}
          {turns.map((turn) => (
            <article className="turn" key={turn.id}>
              <div className="question-label">{tr("chat.you")}</div>
              <h3>{turn.question}</h3>
              <div className="assistant-label">
                <img
                  className="answer-mascot"
                  src="/brand/raccoon.png"
                  width="26"
                  height="26"
                  alt=""
                />{" "}
                Racall
              </div>
              {turn.answer && <AnswerView answer={turn.answer} cite={cite} />}
              {turn.evidence && (
                <div className="search-results">
                  {turn.evidence.length === 0 ? (
                    <p>{tr("chat.noMatches")}</p>
                  ) : (
                    turn.evidence.map((e) => (
                      <button key={e.id} onClick={() => cite(e)}>
                        <strong>{e.title}</strong>
                        <small>{locationLabel(e)}</small>
                        <p>
                          {e.quote.slice(0, 550)}
                          {e.quote.length > 550 ? "…" : ""}
                        </p>
                      </button>
                    ))
                  )}
                </div>
              )}
              {turn.status === "running" && (
                <div className="answer-loading" aria-live="polite">
                  <span>
                    {turn.mode === "ask"
                      ? tr("chat.thinking")
                      : tr("chat.searching")}
                  </span>
                  <div className="skeleton" />
                </div>
              )}
              {(turn.status === "failed" || turn.status === "interrupted") && (
                <div className="turn-failure">
                  <p>
                    {tr(
                      turn.status === "failed"
                        ? "chat.failed"
                        : "chat.interrupted",
                    )}
                  </p>
                  <button
                    className="text-button"
                    disabled={pending}
                    onClick={() => {
                      setQuestion(turn.question);
                      setMode(turn.mode);
                    }}
                  >
                    {tr("chat.tryAgain")}
                  </button>
                </div>
              )}
            </article>
          ))}
          <div ref={end} />
        </div>
        <div className="composer-wrap">
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <textarea
              aria-label={tr("chat.questionLabel")}
              placeholder={
                count ? tr("chat.placeholder") : tr("chat.noSourcePlaceholder")
              }
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={!count || pending || loading}
              rows={2}
              maxLength={2000}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className="composer-bottom">
              <div className="composer-tools">
                <ChatActions
                  openSources={openSources}
                  navigate={navigate}
                  settings={settings}
                />
                <div className="mode-switch">
                  <button
                    type="button"
                    disabled={pending}
                    className={mode === "ask" ? "active" : ""}
                    onClick={() => setMode("ask")}
                  >
                    <Sparkle size={14} />
                    {tr("chat.aiAnswer")}
                  </button>
                  <button
                    type="button"
                    disabled={pending}
                    className={mode === "search" ? "active" : ""}
                    onClick={() => setMode("search")}
                  >
                    <MagnifyingGlass size={14} />
                    {tr("common.search")}
                  </button>
                </div>
              </div>
              <button
                className="send-button"
                aria-label={tr("chat.send")}
                disabled={pending || loading || !count || !question.trim()}
              >
                <ArrowUp size={20} />
              </button>
            </div>
          </form>
          {!turns.length && !pending && (
            <div className="chat-shortcuts">
              {count ? (
                <>
                  <button onClick={() => setQuestion(tr("chat.suggestion"))}>
                    <Sparkle size={14} />
                    {tr("chat.ideas")}
                  </button>
                  <button onClick={() => navigate("research")}>
                    <MagnifyingGlass size={14} />
                    {tr("chat.research")}
                  </button>
                  <button onClick={() => navigate("notes")}>
                    <FileText size={14} />
                    {tr("chat.notes")}
                  </button>
                </>
              ) : (
                <button onClick={openSources}>
                  <Plus size={15} />
                  {tr("source.addMaterials")}
                </button>
              )}
            </div>
          )}
          <p className="composer-caption">
            {tr("chat.sourcesOnly")} <span>·</span> {tr("chat.checkCitations")}
          </p>
        </div>
      </div>
    </div>
  );
}
