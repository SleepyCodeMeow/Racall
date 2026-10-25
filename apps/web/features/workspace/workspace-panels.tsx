import { Chat } from '../chat/chat';
import { Notes } from '../notes/notes';
import { ResearchPanel } from '../research/research-panel';
import { StudioPanel } from '../studio/studio-panel';
import { MaterialLibrary } from '../artifacts/material-library';
import { Connect } from '../connections/connect';
import { SourcePanel } from '../sources/source-panel';
import type { WorkspaceController } from './use-workspace';

export function WorkspacePanels({ workspace }: { workspace: WorkspaceController }) {
  const {
    notebook,
    tab,
    sources,
    selected,
    showSources,
    setSelected,
    cite,
    report,
    openSettings,
    openSources,
    navigate,
    refresh,
  } = workspace;
  return (
    <div className={`workspace-body ${showSources || selected ? 'sources-open' : ''}`}>
      <section className="center-panel">
        <div key={notebook} className="workspace-content">
          <div
            id="panel-chat"
            role="tabpanel"
            aria-labelledby="tab-chat"
            hidden={tab !== 'chat'}
            className="tab-content"
          >
            <Chat
              notebook={notebook}
              count={sources.data?.filter((s) => s.status === 'ready').length || 0}
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
            hidden={tab !== 'notes'}
            className="tab-content"
          >
            <Notes notebook={notebook} kind="notes" report={report} />
          </div>
          {tab === 'artifacts' && (
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
            hidden={tab !== 'research'}
            className="tab-content"
          >
            <ResearchPanel notebook={notebook} cite={cite} report={report} />
          </div>
          <div
            id="panel-studio"
            role="tabpanel"
            aria-labelledby="tab-studio"
            hidden={tab !== 'studio'}
            className="tab-content"
          >
            <StudioPanel
              notebook={notebook}
              cite={cite}
              report={report}
              navigate={navigate}
              settings={openSettings}
            />
          </div>
          {tab === 'connect' && <Connect notebook={notebook} report={report} />}
        </div>
      </section>
      <div id="source-drawer" className="source-drawer" hidden={!showSources && !selected}>
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
  );
}
