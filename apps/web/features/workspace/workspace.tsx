'use client';
import { ArrowRight, CaretDown, SidebarSimple, X } from '@phosphor-icons/react';
import { Apps } from '../apps/apps';
import { SettingsPanel } from '../settings/settings';
import { NoteCitation } from '../context/note-citation';
import { CreateNotebookDialog } from './create-notebook-dialog';
import { WorkspaceNavigation } from './workspace-navigation';
import { WorkspacePanels } from './workspace-panels';
import { useWorkspace } from './use-workspace';

export function Workspace() {
  const workspace = useWorkspace();
  const {
    tr,
    localize,
    selected,
    error,
    setError,
    apps,
    settings,
    report,
    setSettings,
    active,
    provider,
    openSettings,
    showSources,
    toggleSources,
    sources,
    openCreate,
    noteCitation,
    setNoteCitation,
    create,
  } = workspace;
  return (
    <div className="app-shell">
      <WorkspaceNavigation workspace={workspace} />
      <main className={`main-shell ${selected ? 'with-detail' : ''}`}>
        {error && (
          <div className="error-banner" role="alert">
            <span>{localize(error)}</span>
            <button aria-label={tr('common.dismissError')} onClick={() => setError('')}>
              <X size={17} />
            </button>
          </div>
        )}
        {apps ? (
          <Apps report={report} />
        ) : settings ? (
          <SettingsPanel close={() => setSettings(false)} report={report} />
        ) : active ? (
          <>
            <header className="workspace-header">
              <div className="workspace-identity">
                <h1>{active.title}</h1>
                <button className="provider-button" onClick={openSettings}>
                  <span>{provider.data?.model || tr('settings.chooseModel')}</span>
                  <CaretDown size={12} />
                </button>
              </div>
              <button
                className={`source-toggle ${showSources || selected ? 'active' : ''}`}
                aria-expanded={showSources || !!selected}
                aria-controls="source-drawer"
                onClick={toggleSources}
              >
                <SidebarSimple size={18} />
                <span>{tr('source.title')}</span>
                <span className="source-total">{sources.data?.length || 0}</span>
              </button>
            </header>
            <WorkspacePanels workspace={workspace} />
          </>
        ) : (
          <section className="onboarding">
            <img
              className="welcome-mascot"
              src="/brand/raccoon.png"
              width="68"
              height="68"
              alt={tr('brand.mascot')}
            />
            <h1>{tr('welcome.title')}</h1>
            <p>
              {tr('welcome.description1')}
              <br />
              {tr('welcome.description2')}
            </p>
            <button className="primary" onClick={openCreate}>
              {tr('notebook.first')} <ArrowRight size={18} />
            </button>
            <p className="onboarding-footnote">{tr('welcome.ownership')}</p>
          </section>
        )}
      </main>
      {noteCitation && <NoteCitation evidence={noteCitation} close={() => setNoteCitation(null)} />}
      {create && <CreateNotebookDialog workspace={workspace} />}
    </div>
  );
}
