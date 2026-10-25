import { locationLabel } from '../../lib/api';
import { AnswerView } from './answer-view';
import type { ChatProps } from './chat-types';
import type { ChatController } from './use-chat';

export function ChatTranscript({
  chat,
  count,
  cite,
}: { chat: ChatController } & Pick<ChatProps, 'count' | 'cite'>) {
  const { tr, turns, pending, loading, end, retryTurn } = chat;
  return (
    <div className="chat-scroll">
      {loading ? (
        <p className="muted">{tr('common.loading')}</p>
      ) : (
        !turns.length &&
        !pending && (
          <div className="chat-welcome">
            <div className="welcome-heading">
              <img src="/brand/raccoon.png" width="46" height="46" alt="" />
              <h2>{tr('chat.title')}</h2>
            </div>
            <p>{count ? tr('chat.description') : tr('chat.start')}</p>
          </div>
        )
      )}
      {turns.map((turn) => (
        <article className="turn" key={turn.id}>
          <div className="question-label">{tr('chat.you')}</div>
          <h3>{turn.question}</h3>
          <div className="assistant-label">
            <img className="answer-mascot" src="/brand/raccoon.png" width="26" height="26" alt="" />{' '}
            Racall
          </div>
          {turn.answer && <AnswerView answer={turn.answer} cite={cite} />}
          {turn.context_info && (
            <p className="context-turn-hint">
              {tr('context.turnSummary', {
                sources: turn.context_info.source_count,
                notes: turn.context_info.note_count,
                turns: turn.context_info.history_turns,
              })}
            </p>
          )}
          {turn.context_info?.history_truncated && (
            <p className="context-turn-hint">{tr('context.historyTrimmed')}</p>
          )}
          {turn.context_info?.evidence_truncated && (
            <p className="context-turn-hint">{tr('context.evidenceTrimmed')}</p>
          )}
          {turn.evidence && (
            <div className="search-results">
              {turn.evidence.length === 0 ? (
                <p>{tr('chat.noMatches')}</p>
              ) : (
                turn.evidence.map((e) => (
                  <button key={e.id} onClick={() => cite(e)}>
                    <strong>{e.title}</strong>
                    <small>{locationLabel(e)}</small>
                    <p>
                      {e.quote.slice(0, 550)}
                      {e.quote.length > 550 ? '…' : ''}
                    </p>
                  </button>
                ))
              )}
            </div>
          )}
          {turn.status === 'running' && (
            <div className="answer-loading" aria-live="polite">
              <span>{turn.mode === 'ask' ? tr('chat.thinking') : tr('chat.searching')}</span>
              <div className="skeleton" />
            </div>
          )}
          {(turn.status === 'failed' || turn.status === 'interrupted') && (
            <div className="turn-failure">
              <p>
                {turn.error_code === 'context_changed'
                  ? tr('context.changed')
                  : tr(turn.status === 'failed' ? 'chat.failed' : 'chat.interrupted')}
              </p>
              <button className="text-button" disabled={pending} onClick={() => retryTurn(turn)}>
                {tr('chat.tryAgain')}
              </button>
            </div>
          )}
        </article>
      ))}
      <div ref={end} />
    </div>
  );
}
