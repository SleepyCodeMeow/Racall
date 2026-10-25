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
  SquaresFour,
  SidebarSimple,
  Notebook as NotebookIcon,
  PlugsConnected,
  Sparkle,
  Plus,
  X,
} from "@phosphor-icons/react";
import { api, Evidence, Notebook, Source, Settings } from "../lib/api";
import { NotebookList } from "../features/notebooks/notebook-list";
import { SourcePanel } from "../features/sources/source-panel";
import { Chat } from "../features/chat/chat";
import { Notes } from "../features/notes/notes";
import { ResearchPanel } from "../features/research/research-panel";
import { StudioPanel } from "../features/studio/studio-panel";
import { MaterialLibrary } from "../features/artifacts/material-library";
import { NoteCitation } from "../features/context/note-citation";
import { Connect } from "../features/connections/connect";
import { SettingsPanel } from "../features/settings/settings";
import { Apps } from "../features/apps/apps";
import { ThemeProvider } from "../lib/theme";
import { settlePendingEdits } from "../lib/pending-edits";

function Application() {
  const { tr, localize } = useI18n();
  const tabs = [
    { id: "chat", title: tr("nav.chat"), icon: ChatCircle },
    { id: "notes", title: tr("nav.notes"), icon: FileText },
    { id: "research", title: tr("nav.research"), icon: Flask },
    { id: "studio", title: tr("nav.studio"), icon: Sparkle },
    { id: "artifacts", title: tr("nav.artifacts"), icon: Folder },
  ];
  const client = useQueryClient();
  const [ready, setReady] = useState(false);
  const [notebook, setNotebook] = useState("");
  const [tab, setTab] = useState("chat");
  const [settings, setSettings] = useState(false);
  const [apps, setApps] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [create, setCreate] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [noteCitation, setNoteCitation] = useState<Evidence | null>(null);
  const [selected, setSelected] = useState<{
    source: Source;
    evidence?: Evidence;
  } | null>(null);
  const report = useCallback((message: string) => setError(message), []);
  useEffect(() => { setNoteCitation(null); }, [notebook]);
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
    queryKey: ["settings"],
    queryFn: () => api<Settings>("/settings"),
    enabled: ready && !settings,
  });
  const active = notebooks.data?.find((n) => n.id === notebook);
  // Keep editors mounted until every pending save has succeeded. Their cleanup
  // cannot cancel a transition when an invalid or conflicted draft cannot save.
  const guardNavigation = async (changeView: () => void | Promise<void>) => {
    if (!(await settlePendingEdits())) {
      report(tr("notebook.unsaved"));
      return;
    }
    await changeView();
  };
  const navigate = (id: string) => {
    // Workspace tabs hide rather than unmount Notes. In particular, a recovered
    // conflict draft must remain reachable even while it cannot be saved.
    setTab(id);
    setSettings(false);
    setApps(false);
  };
  const openSettings = () => {
    void guardNavigation(() => {
      setSettings(true);
      setApps(false);
    });
  };
  const openCreate = () => {
    void guardNavigation(() => setCreate(true));
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
    if (e.kind === "note" || e.note_id) { setNoteCitation(e); return; }
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
        <button className="new-notebook" onClick={openCreate}>
          <Plus size={17} />
          {tr("notebook.new")}
        </button>
        <nav className="global-nav" aria-label={tr("nav.application")}>
          <button className={apps ? "active" : ""} aria-current={apps ? "page" : undefined}
            onClick={() => void guardNavigation(() => { setApps(true); setSettings(false); })}>
            <SquaresFour size={18} /><span>{tr("apps.title")}</span>
          </button>
        </nav>
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
                aria-selected={!settings && !apps && tab === t.id}
                tabIndex={
                  tab === t.id ||
                  (!tabs.some((item) => item.id === tab) && t.id === "chat")
                    ? 0
                    : -1
                }
                onClick={() => navigate(t.id)}
                className={!settings && !apps && tab === t.id ? "active" : ""}
              >
                <t.icon size={18} />
                <span>{t.title}</span>
              </button>
            ))}
            <button
              className={tab === "connect" && !settings && !apps ? "active" : ""}
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
          active={settings || apps ? "" : notebook}
          report={report}
          select={(id) => {
            setNotebook(id);
            setTab("chat");
            setSettings(false);
            setApps(false);
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
            onClick={openSettings}
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
        {apps ? <Apps report={report} /> : settings ? (
          <SettingsPanel close={() => setSettings(false)} report={report} />
        ) : active ? (
          <>
            <header className="workspace-header">
              <div className="workspace-identity">
                <h1>{active.title}</h1>
                <button
                  className="provider-button"
                  onClick={openSettings}
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
                      settings={openSettings}
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
                      <MaterialLibrary
                        notebook={notebook}
                        cite={cite}
                        report={report}
                        navigate={navigate}
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
                  <div id="panel-studio" role="tabpanel" aria-labelledby="tab-studio"
                    hidden={tab !== "studio"} className="tab-content">
                    <StudioPanel notebook={notebook} cite={cite} report={report}
                      navigate={navigate} settings={openSettings} />
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
            <button className="primary" onClick={openCreate}>
              {tr("notebook.first")} <ArrowRight size={18} />
            </button>
            <p className="onboarding-footnote">{tr("welcome.ownership")}</p>
          </section>
        )}
      </main>
      {noteCitation && <NoteCitation evidence={noteCitation} close={() => setNoteCitation(null)} />}
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
                  await guardNavigation(async () => {
                    const n = await api<Notebook>("/notebooks", "POST", {
                      title: name.trim(),
                    });
                    await client.invalidateQueries({ queryKey: ["notebooks"] });
                    // The dialog can close while creation is in flight, letting
                    // the editor acquire newer changes before this response.
                    await guardNavigation(() => {
                      setNotebook(n.id);
                      setTab("chat");
                      setSettings(false);
                      setApps(false);
                      setSelected(null);
                      setCreate(false);
                      setName("");
                    });
                  });
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
        <ThemeProvider><Application /></ThemeProvider>
      </I18nProvider>
    </QueryClientProvider>
  );
}
