"use client";
import release from "../../shared/release.json";
import { useI18n, I18nProvider } from "../lib/i18n";
import { useCallback, useEffect, useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowRight,
  CaretDown,
  ChatCircle,
  FileText,
  Flask,
  Folder,
  GearSix,
  SidebarSimple,
  Notebook as NotebookIcon,
  PlugsConnected,
  Plus,
  X,
} from "@phosphor-icons/react";
import { api, Evidence, Notebook, Source, Settings } from "../lib/api";
import { NotebookList } from "../features/notebooks/notebook-list";
import { SourcePanel } from "../features/sources/source-panel";
import { Chat } from "../features/chat/chat";
import { Notes } from "../features/notes/notes";
import { ResearchPanel } from "../features/research/research-panel";
import { Connect } from "../features/connections/connect";
import { SettingsPanel } from "../features/settings/settings";

function Application() {
  const { tr, localize } = useI18n();
  const tabs = [
    { id: "chat", title: tr("nav.chat"), icon: ChatCircle },
    { id: "notes", title: tr("nav.notes"), icon: FileText },
    { id: "research", title: tr("nav.research"), icon: Flask },
    { id: "artifacts", title: tr("nav.artifacts"), icon: Folder },
  ];
  const client = useQueryClient();
  const [ready, setReady] = useState(false);
  const [notebook, setNotebook] = useState("");
  const [tab, setTab] = useState("chat");
  const [settings, setSettings] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [create, setCreate] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<{
    source: Source;
    evidence?: Evidence;
  } | null>(null);
  const report = useCallback((message: string) => setError(message), []);
  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    if (hash.has("token")) {
      sessionStorage.setItem("on-token", hash.get("token")!);
      history.replaceState(null, "", location.pathname);
    }
    setReady(true);
  }, []);
  const notebooks = useQuery({
    queryKey: ["notebooks"],
    queryFn: () => api<Notebook[]>("/notebooks"),
    enabled: ready,
  });
  const sources = useQuery({
    queryKey: ["sources", notebook],
    queryFn: () => api<Source[]>(`/notebooks/${notebook}/sources`),
    enabled: !!notebook,
    refetchInterval: (query) =>
      query.state.data?.some(
        (s) =>
          ["queued", "processing"].includes(s.status) ||
          ["queued", "processing"].includes(s.refresh_status || ""),
      )
        ? 1500
        : false,
  });
  useEffect(() => {
    if (notebooks.data && !notebooks.data.some((n) => n.id === notebook))
      setNotebook(notebooks.data[0]?.id || "");
  }, [notebooks.data, notebook]);
  useEffect(() => {
    if (notebooks.error || sources.error)
      report((notebooks.error || sources.error)!.message);
  }, [notebooks.error, sources.error, report]);
  const provider = useQuery({
    queryKey: ["provider", settings],
    queryFn: () => api<Settings>("/settings"),
    enabled: ready && !settings,
  });
  const active = notebooks.data?.find((n) => n.id === notebook);
  const navigate = (id: string) => {
    setTab(id);
    setSettings(false);
  };
  const openSources = () => {
    setSelected(null);
    setShowSources(true);
  };
  const refresh = () => {
    client.invalidateQueries({ queryKey: ["sources", notebook] });
    client.invalidateQueries({ queryKey: ["notebooks"] });
  };
  const cite = (e: Evidence) => {
    const source = sources.data?.find((s) => s.id === e.source_id);
    if (source) {
      setSelected({ source, evidence: e });
      setShowSources(true);
    } else report(tr("error.sourceMissing"));
  };
  return (
    <div className="app-shell">
      <aside className="navigation">
        <div className="brand">
          <img src="/brand/raccoon.png" width="36" height="36" alt="" />
          <span>racall</span>
          <small>beta</small>
        </div>
        <button className="new-notebook" onClick={() => setCreate(true)}>
          <Plus size={17} />
          {tr("notebook.new")}
        </button>
        {active && (
          <nav
            className="workspace-nav"
            role="tablist"
            aria-label={tr("nav.sections")}
            aria-orientation="vertical"
            onKeyDown={(e) => {
              const controls = Array.from(
                e.currentTarget.querySelectorAll<HTMLButtonElement>(
                  '[role="tab"]',
                ),
              );
              const index = controls.indexOf(
                document.activeElement as HTMLButtonElement,
              );
              const next =
                e.key === "ArrowDown"
                  ? (index + 1) % controls.length
                  : e.key === "ArrowUp"
                    ? (index - 1 + controls.length) % controls.length
                    : e.key === "Home"
                      ? 0
                      : e.key === "End"
                        ? controls.length - 1
                        : -1;
              if (next >= 0) {
                e.preventDefault();
                controls[next].focus();
                controls[next].click();
              }
            }}
          >
            {tabs.map((t) => (
              <button
                key={t.id}
                id={`tab-${t.id}`}
                role="tab"
                aria-controls={`panel-${t.id}`}
                aria-selected={!settings && tab === t.id}
                tabIndex={
                  tab === t.id ||
                  (!tabs.some((item) => item.id === tab) && t.id === "chat")
                    ? 0
                    : -1
                }
                onClick={() => navigate(t.id)}
                className={!settings && tab === t.id ? "active" : ""}
              >
                <t.icon size={18} />
                <span>{t.title}</span>
              </button>
            ))}
            <button
              className={tab === "connect" && !settings ? "active" : ""}
              onClick={() => navigate("connect")}
            >
              <PlugsConnected size={18} />
              <span>{tr("nav.connect")}</span>
            </button>
          </nav>
        )}
        <div className="nav-label">
          {tr("nav.notebooks")} <span>{notebooks.data?.length || 0}</span>
        </div>
        <NotebookList
          items={notebooks.data}
          pending={notebooks.isPending}
          active={settings ? "" : notebook}
          report={report}
          select={(id) => {
            setNotebook(id);
            setTab("chat");
            setSettings(false);
            setSelected(null);
          }}
          removed={(id) => {
            if (notebook === id) {
              setNotebook("");
              setSelected(null);
              setTab("chat");
              setShowSources(false);
            }
          }}
        />
        <div className="nav-bottom">
          <div className="local-note">
            <span className="status-dot" />
            <span>
              {tr("nav.local")}
              <small>{tr("nav.ownership")}</small>
            </span>
          </div>
          <button
            className={settings ? "selected" : ""}
            onClick={() => setSettings(true)}
          >
            <GearSix size={18} />
            {tr("settings.title")}
          </button>
          <div className="version">
            RACALL <span>{release.label}</span>
          </div>
        </div>
      </aside>
      <main className={`main-shell ${selected ? "with-detail" : ""}`}>
        {error && (
          <div className="error-banner" role="alert">
            <span>{localize(error)}</span>
            <button
              aria-label={tr("common.dismissError")}
              onClick={() => setError("")}
            >
              <X size={17} />
            </button>
          </div>
        )}
        {settings ? (
          <SettingsPanel close={() => setSettings(false)} report={report} />
        ) : active ? (
          <>
            <header className="workspace-header">
              <div className="workspace-identity">
                <h1>{active.title}</h1>
                <button
                  className="provider-button"
                  onClick={() => setSettings(true)}
                >
                  <span>
                    {provider.data?.model || tr("settings.chooseModel")}
                  </span>
                  <CaretDown size={12} />
                </button>
              </div>
              <button
                className={`source-toggle ${showSources || selected ? "active" : ""}`}
                aria-expanded={showSources || !!selected}
                aria-controls="source-drawer"
                onClick={() => {
                  setShowSources(!(showSources || selected));
                  setSelected(null);
                }}
              >
                <SidebarSimple size={18} />
                <span>{tr("source.title")}</span>
                <span className="source-total">
                  {sources.data?.length || 0}
                </span>
              </button>
            </header>
            <div
              className={`workspace-body ${showSources || selected ? "sources-open" : ""}`}
            >
              <section className="center-panel">
                <div key={notebook} className="workspace-content">
                  <div
                    id="panel-chat"
                    role="tabpanel"
                    aria-labelledby="tab-chat"
                    hidden={tab !== "chat"}
                    className="tab-content"
                  >
                    <Chat
                      notebook={notebook}
                      count={
                        sources.data?.filter((s) => s.status === "ready")
                          .length || 0
                      }
                      cite={cite}
                      report={report}
                      settings={() => setSettings(true)}
                      openSources={openSources}
                      navigate={navigate}
                    />
                  </div>
                  <div
                    id="panel-notes"
                    role="tabpanel"
                    aria-labelledby="tab-notes"
                    hidden={tab !== "notes"}
                    className="tab-content"
                  >
                    <Notes notebook={notebook} kind="notes" report={report} />
                  </div>
                  {tab === "artifacts" && (
                    <div
                      id="panel-artifacts"
                      role="tabpanel"
                      aria-labelledby="tab-artifacts"
                      className="tab-content"
                    >
                      <Notes
                        notebook={notebook}
                        kind="artifacts"
                        report={report}
                      />
                    </div>
                  )}
                  <div
                    id="panel-research"
                    role="tabpanel"
                    aria-labelledby="tab-research"
                    hidden={tab !== "research"}
                    className="tab-content"
                  >
                    <ResearchPanel
                      notebook={notebook}
                      cite={cite}
                      report={report}
                    />
                  </div>
                  {tab === "connect" && (
                    <Connect notebook={notebook} report={report} />
                  )}
                </div>
              </section>
              <div
                id="source-drawer"
                className="source-drawer"
                hidden={!showSources && !selected}
              >
                <SourcePanel
                  key={notebook}
                  notebook={notebook}
                  sources={sources.data || []}
                  selected={selected}
                  select={setSelected}
                  refresh={refresh}
                  report={report}
                />
              </div>
            </div>
          </>
        ) : (
          <section className="onboarding">
            <img
              className="welcome-mascot"
              src="/brand/raccoon.png"
              width="68"
              height="68"
              alt={tr("brand.mascot")}
            />
            <h1>{tr("welcome.title")}</h1>
            <p>
              {tr("welcome.description1")}
              <br />
              {tr("welcome.description2")}
            </p>
            <button className="primary" onClick={() => setCreate(true)}>
              {tr("notebook.first")} <ArrowRight size={18} />
            </button>
            <p className="onboarding-footnote">{tr("welcome.ownership")}</p>
          </section>
        )}
      </main>
      {create && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setCreate(false);
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-title"
            onKeyDown={(e) => {
              if (e.key === "Escape") setCreate(false);
            }}
          >
            <button
              className="modal-close icon-button"
              aria-label={tr("common.close")}
              onClick={() => setCreate(false)}
            >
              <X size={19} />
            </button>
            <NotebookIcon size={32} className="accent" />
            <h2 id="create-title">{tr("notebook.new")}</h2>
            <p className="muted">{tr("notebook.description")}</p>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                try {
                  const n = await api<Notebook>("/notebooks", "POST", {
                    title: name.trim(),
                  });
                  await client.invalidateQueries({ queryKey: ["notebooks"] });
                  setNotebook(n.id);
                  setTab("chat");
                  setSettings(false);
                  setSelected(null);
                  setCreate(false);
                  setName("");
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
                  autoFocus
                  required
                  maxLength={160}
                  value={name}
                  placeholder={tr("notebook.placeholder")}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <button
                className="primary w-full mt-6"
                disabled={busy || !name.trim()}
              >
                {busy ? tr("common.creating") : tr("notebook.create")}
                <ArrowRight size={17} />
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

export default function Page() {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <I18nProvider>
        <Application />
      </I18nProvider>
    </QueryClientProvider>
  );
}
