import { ArrowUp, FileText, MagnifyingGlass, Plus, Sparkle } from '@phosphor-icons/react';
import { ModelPicker } from '../models/ModelPicker';
import { ChatActions } from './chat-actions';
import type { ChatProps } from './chat-types';
import type { ChatController } from './use-chat';

export function ChatComposer({
  chat,
  count,
  settings,
  openSources,
  navigate,
  report,
}: { chat: ChatController } & Pick<
  ChatProps,
  'count' | 'settings' | 'openSources' | 'navigate' | 'report'
>) {
  const { tr, question, setQuestion, hasContext, pending, loading, mode, setMode, send, turns } =
    chat;
  return (
    <div className="composer-wrap">
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <textarea
          aria-label={tr('chat.questionLabel')}
          placeholder={hasContext ? tr('chat.placeholder') : tr('chat.noSourcePlaceholder')}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={!hasContext || pending || loading}
          rows={2}
          maxLength={2000}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              e.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <div className="composer-bottom">
          <div className="composer-tools">
            <ChatActions openSources={openSources} navigate={navigate} settings={settings} />
            <div className="mode-switch">
              <button
                type="button"
                disabled={pending}
                className={mode === 'ask' ? 'active' : ''}
                onClick={() => setMode('ask')}
              >
                <Sparkle size={14} />
                {tr('chat.aiAnswer')}
              </button>
              <button
                type="button"
                disabled={pending}
                className={mode === 'search' ? 'active' : ''}
                onClick={() => setMode('search')}
              >
                <MagnifyingGlass size={14} />
                {tr('common.search')}
              </button>
            </div>
          </div>
          <div className="composer-controls">
            <ModelPicker configure={settings} report={report} disabled={pending} />
            <button
              className="send-button"
              aria-label={tr('chat.send')}
              disabled={pending || loading || !hasContext || !question.trim()}
            >
              <ArrowUp size={20} />
            </button>
          </div>
        </div>
      </form>
      {!turns.length && !pending && (
        <div className="chat-shortcuts">
          {count ? (
            <>
              <button onClick={() => setQuestion(tr('chat.suggestion'))}>
                <Sparkle size={14} />
                {tr('chat.ideas')}
              </button>
              <button onClick={() => navigate('research')}>
                <MagnifyingGlass size={14} />
                {tr('chat.research')}
              </button>
              <button onClick={() => navigate('notes')}>
                <FileText size={14} />
                {tr('chat.notes')}
              </button>
            </>
          ) : (
            <button onClick={openSources}>
              <Plus size={15} />
              {tr('source.addMaterials')}
            </button>
          )}
        </div>
      )}
      <p className="composer-caption">
        {tr('chat.sourcesOnly')} <span>·</span> {tr('chat.checkCitations')}
      </p>
    </div>
  );
}
