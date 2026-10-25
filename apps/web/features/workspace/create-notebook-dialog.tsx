import { ArrowRight, Notebook as NotebookIcon, X } from '@phosphor-icons/react';
import type { WorkspaceController } from './use-workspace';

export function CreateNotebookDialog({ workspace }: { workspace: WorkspaceController }) {
  const { tr, name, busy, setCreate, setName, createNotebook } = workspace;
  return (
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
          if (e.key === 'Escape') setCreate(false);
        }}
      >
        <button
          className="modal-close icon-button"
          aria-label={tr('common.close')}
          onClick={() => setCreate(false)}
        >
          <X size={19} />
        </button>
        <NotebookIcon size={32} className="accent" />
        <h2 id="create-title">{tr('notebook.new')}</h2>
        <p className="muted">{tr('notebook.description')}</p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            await createNotebook();
          }}
        >
          <label>
            {tr('notebook.name')}
            <input
              autoFocus
              required
              maxLength={160}
              value={name}
              placeholder={tr('notebook.placeholder')}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <button className="primary w-full mt-6" disabled={busy || !name.trim()}>
            {busy ? tr('common.creating') : tr('notebook.create')}
            <ArrowRight size={17} />
          </button>
        </form>
      </section>
    </div>
  );
}
