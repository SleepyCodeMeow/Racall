'use client';
import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type ChatThread, type ChatTurn, type ContextSelection } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import { allMaterials, copySelection } from '../context/context-picker';
import type { ChatProps } from './chat-types';

export function useChat({
  notebook,
  count,
  report,
}: Pick<ChatProps, 'notebook' | 'count' | 'report'>) {
  const { tr } = useI18n();
  const client = useQueryClient();
  const [thread, setThread] = useState('');
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<'ask' | 'search'>('ask');
  const [rename, setRename] = useState<string | null>(null);
  const [context, setContext] = useState<ContextSelection>(allMaterials);
  const contextRef = useRef(context);
  const [contextSaving, setContextSaving] = useState(false);
  const savingContext = useRef(false);
  const [contextThread, setContextThread] = useState('');
  const threadsKey = ['chats', notebook];
  const threadKey = ['chat', notebook, thread];
  const threads = useQuery({
    queryKey: threadsKey,
    queryFn: () => api<ChatThread[]>(`/notebooks/${notebook}/chats`),
  });
  const selected = useQuery({
    queryKey: threadKey,
    enabled: !!thread,
    queryFn: () => api<ChatThread>(`/notebooks/${notebook}/chats/${thread}`),
    refetchInterval: (q) =>
      q.state.data?.turns.some((t) => t.status === 'running') ? 1000 : false,
  });
  useEffect(() => {
    if (!thread && threads.data?.length) setThread(threads.data[0].id);
  }, [thread, threads.data]);
  useEffect(() => {
    if (threads.error || selected.error) report((threads.error || selected.error)!.message);
  }, [threads.error, selected.error, report]);
  useEffect(() => {
    if (
      !thread ||
      selected.data?.id !== thread ||
      contextThread === thread ||
      savingContext.current
    )
      return;
    const restored = copySelection(selected.data.context || allMaterials());
    contextRef.current = restored;
    setContext(restored);
    setContextThread(thread);
  }, [thread, selected.data, contextThread]);
  const turns = selected.data?.turns || [];
  const pending = busy || contextSaving || turns.some((t) => t.status === 'running');
  const loading =
    threads.isPending || (!!thread && (selected.isPending || contextThread !== thread));
  const hasContext =
    (context.source_ids === null ? count : context.source_ids.length) > 0 ||
    context.note_ids.length > 0;
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [turns.length, pending]);
  const refresh = () => client.invalidateQueries({ queryKey: threadsKey });
  const changeContext = async (next: ContextSelection) => {
    if (savingContext.current) return;
    const previous = contextRef.current;
    const selection = copySelection(next);
    savingContext.current = true;
    setContextSaving(true);
    contextRef.current = selection;
    setContext(selection);
    try {
      if (thread) {
        // Stop an older GET from replacing the acknowledged selection in cache.
        await client.cancelQueries({ queryKey: threadKey });
        const item = await api<ChatThread>(
          `/notebooks/${notebook}/chats/${thread}/context`,
          'PUT',
          selection,
        );
        client.setQueryData(threadKey, item);
      }
    } catch (error) {
      contextRef.current = previous;
      setContext(previous);
      throw error;
    } finally {
      savingContext.current = false;
      setContextSaving(false);
    }
  };
  const create = async (title: string, selection: ContextSelection = allMaterials()) => {
    const item = await api<ChatThread>(`/notebooks/${notebook}/chats`, 'POST', {
      title,
      context: selection,
    });
    client.setQueryData(['chat', notebook, item.id], item);
    contextRef.current = copySelection(item.context || selection);
    setContext(contextRef.current);
    setContextThread(item.id);
    setThread(item.id);
    setRename(null);
    await refresh();
    return item.id;
  };
  const send = async () => {
    if (!question.trim() || pending || loading || savingContext.current || !hasContext) return;
    setBusy(true);
    const q = question.trim();
    const selection = copySelection(contextRef.current);
    let id = thread;
    try {
      if (!id) id = await create(q.slice(0, 160), selection);
      const key = ['chat', notebook, id];
      const request_id = crypto.randomUUID();
      const optimistic: ChatTurn = {
        id: request_id,
        question: q,
        mode,
        status: 'running',
      };
      client.setQueryData<ChatThread>(key, (old) =>
        old ? { ...old, turns: [...old.turns, optimistic] } : old,
      );
      await api<ChatTurn>(`/notebooks/${notebook}/chats/${id}/turns`, 'POST', {
        question: q,
        mode,
        request_id,
        context: selection,
      });
      setQuestion('');
    } catch (error) {
      report((error as Error).message);
    } finally {
      if (id) await client.invalidateQueries({ queryKey: ['chat', notebook, id] });
      await refresh();
      setBusy(false);
    }
  };
  const selectThread = (id: string) => {
    setThread(id);
    setContextThread('');
    setRename(null);
    setQuestion('');
  };
  const newChat = async () => {
    setBusy(true);
    try {
      await create(tr('chat.new'));
      setQuestion('');
    } catch (e) {
      report((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const deleteChat = async () => {
    if (!window.confirm(tr('chat.deleteConfirm'))) return;
    setBusy(true);
    try {
      await api(`/notebooks/${notebook}/chats/${thread}`, 'DELETE');
      client.removeQueries({ queryKey: threadKey });
      await refresh();
      setThread('');
      setContextThread('');
      contextRef.current = allMaterials();
      setContext(contextRef.current);
      setQuestion('');
      setRename(null);
    } catch (e) {
      report((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const renameChat = async (title: string) => {
    try {
      const item = await api<ChatThread>(`/notebooks/${notebook}/chats/${thread}`, 'PUT', {
        title: title.trim(),
      });
      client.setQueryData(threadKey, item);
      setRename(null);
      await refresh();
    } catch (error) {
      report((error as Error).message);
    }
  };
  const retryTurn = (turn: ChatTurn) => {
    setQuestion(turn.question);
    setMode(turn.mode);
  };
  return {
    tr,
    thread,
    threads,
    selected,
    question,
    setQuestion,
    mode,
    setMode,
    rename,
    setRename,
    context,
    pending,
    loading,
    hasContext,
    turns,
    end,
    send,
    changeContext,
    selectThread,
    newChat,
    deleteChat,
    renameChat,
    retryTurn,
  };
}

export type ChatController = ReturnType<typeof useChat>;
