import release from '../../../shared/release.json';
import {
  ChatCircle,
  FileText,
  Flask,
  Folder,
  GearSix,
  SquaresFour,
  PlugsConnected,
  Sparkle,
  Plus,
} from '@phosphor-icons/react';
import { NotebookList } from '../notebooks/notebook-list';
import type { WorkspaceController } from './use-workspace';

export function WorkspaceNavigation({ workspace }: { workspace: WorkspaceController }) {
  const {
    tr,
    active,
    apps,
    settings,
    tab,
    notebook,
    notebooks,
    report,
    openCreate,
    openApps,
    openSettings,
    navigate,
    selectNotebook,
    removedNotebook,
  } = workspace;
  const tabs = [
    { id: 'chat', title: tr('nav.chat'), icon: ChatCircle },
    { id: 'notes', title: tr('nav.notes'), icon: FileText },
    { id: 'research', title: tr('nav.research'), icon: Flask },
    { id: 'studio', title: tr('nav.studio'), icon: Sparkle },
    { id: 'artifacts', title: tr('nav.artifacts'), icon: Folder },
  ];
  return (
    <aside className="navigation">
      <div className="brand">
        <img src="/brand/raccoon.png" width="36" height="36" alt="" />
        <span>racall</span>
        <small>beta</small>
      </div>
      <button className="new-notebook" onClick={openCreate}>
        <Plus size={17} />
        {tr('notebook.new')}
      </button>
      <nav className="global-nav" aria-label={tr('nav.application')}>
        <button
          className={apps ? 'active' : ''}
          aria-current={apps ? 'page' : undefined}
          onClick={openApps}
        >
          <SquaresFour size={18} />
          <span>{tr('apps.title')}</span>
        </button>
      </nav>
      {active && (
        <nav
          className="workspace-nav"
          role="tablist"
          aria-label={tr('nav.sections')}
          aria-orientation="vertical"
          onKeyDown={(e) => {
            const controls = Array.from(
              e.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]'),
            );
            const index = controls.indexOf(document.activeElement as HTMLButtonElement);
            const next =
              e.key === 'ArrowDown'
                ? (index + 1) % controls.length
                : e.key === 'ArrowUp'
                  ? (index - 1 + controls.length) % controls.length
                  : e.key === 'Home'
                    ? 0
                    : e.key === 'End'
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
                tab === t.id || (!tabs.some((item) => item.id === tab) && t.id === 'chat') ? 0 : -1
              }
              onClick={() => navigate(t.id)}
              className={!settings && !apps && tab === t.id ? 'active' : ''}
            >
              <t.icon size={18} />
              <span>{t.title}</span>
            </button>
          ))}
          <button
            className={tab === 'connect' && !settings && !apps ? 'active' : ''}
            onClick={() => navigate('connect')}
          >
            <PlugsConnected size={18} />
            <span>{tr('nav.connect')}</span>
          </button>
        </nav>
      )}
      <div className="nav-label">
        {tr('nav.notebooks')} <span>{notebooks.data?.length || 0}</span>
      </div>
      <NotebookList
        items={notebooks.data}
        pending={notebooks.isPending}
        active={settings || apps ? '' : notebook}
        report={report}
        select={selectNotebook}
        removed={removedNotebook}
      />
      <div className="nav-bottom">
        <div className="local-note">
          <span className="status-dot" />
          <span>
            {tr('nav.local')}
            <small>{tr('nav.ownership')}</small>
          </span>
        </div>
        <button className={settings ? 'selected' : ''} onClick={openSettings}>
          <GearSix size={18} />
          {tr('settings.title')}
        </button>
        <div className="version">
          RACALL <span>{release.label}</span>
        </div>
      </div>
    </aside>
  );
}
