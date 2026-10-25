import { Plus } from '@phosphor-icons/react';
import type { ChatController } from './use-chat';

export function ChatHistoryBar({ chat }: { chat: ChatController }) {
  const {
    tr,
    thread,
    threads,
    pending,
    loading,
    selected,
    rename,
    setRename,
    selectThread,
    newChat,
    deleteChat,
    renameChat,
  } = chat;
  return (
    <>
      <div className="chat-history-bar">
        <select
          aria-label={tr('chat.history')}
          value={thread}
          disabled={pending || loading}
          onChange={(e) => selectThread(e.target.value)}
        >
          {!threads.data?.length && <option value="">{tr('chat.new')}</option>}
          {threads.data?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.title}
            </option>
          ))}
        </select>
        <button className="text-button" disabled={pending || loading} onClick={newChat}>
          <Plus size={15} />
          {tr('chat.new')}
        </button>
        {!!thread && (
          <>
            <button
              className="text-button"
              disabled={pending || loading}
              onClick={() => setRename(selected.data?.title || '')}
            >
              {tr('common.rename')}
            </button>
            <button className="text-button" disabled={pending || loading} onClick={deleteChat}>
              {tr('common.delete')}
            </button>
          </>
        )}
      </div>
      {rename !== null && (
        <form
          className="chat-rename"
          onSubmit={async (e) => {
            e.preventDefault();
            await renameChat(rename);
          }}
        >
          <input
            autoFocus
            aria-label={tr('chat.name')}
            maxLength={160}
            value={rename}
            onChange={(e) => setRename(e.target.value)}
          />
          <button className="secondary" disabled={!rename.trim()}>
            {tr('common.save')}
          </button>
          <button type="button" className="text-button" onClick={() => setRename(null)}>
            {tr('common.cancel')}
          </button>
        </form>
      )}
    </>
  );
}
