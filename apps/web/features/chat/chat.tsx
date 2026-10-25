'use client';
import { ContextPicker } from '../context/context-picker';
import { ChatHistoryBar } from './chat-history-bar';
import { ChatTranscript } from './chat-transcript';
import { ChatComposer } from './chat-composer';
import { useChat } from './use-chat';
import type { ChatProps } from './chat-types';

export function Chat(props: ChatProps) {
  const chat = useChat(props);
  const { notebook, count, cite, report } = props;
  const { context, changeContext, pending, loading, turns } = chat;
  return (
    <div className="chat-workspace">
      <ChatHistoryBar chat={chat} />
      <div className="chat-context-bar">
        <ContextPicker
          notebook={notebook}
          value={context}
          onChange={changeContext}
          disabled={pending || loading}
          report={report}
        />
      </div>
      <div className={`chat-layout ${!turns.length && !pending ? 'is-empty' : ''}`}>
        <ChatTranscript chat={chat} count={count} cite={cite} />
        <ChatComposer chat={chat} {...props} />
      </div>
    </div>
  );
}
