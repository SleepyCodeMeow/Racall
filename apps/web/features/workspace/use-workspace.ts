'use client';
import { useCallback, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Evidence, type Notebook, type Source, type Settings } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import { settlePendingEdits } from '../../lib/pending-edits';

export function useWorkspace() {
  const { tr, localize } = useI18n();
  const client = useQueryClient();
  const [ready, setReady] = useState(false);
  const [notebook, setNotebook] = useState('');
  const [tab, setTab] = useState('chat');
  const [settings, setSettings] = useState(false);
  const [apps, setApps] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [create, setCreate] = useState(false);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [noteCitation, setNoteCitation] = useState<Evidence | null>(null);
  const [selected, setSelected] = useState<{
    source: Source;
    evidence?: Evidence;
  } | null>(null);
  const report = useCallback((message: string) => setError(message), []);
  useEffect(() => {
    setNoteCitation(null);
  }, [notebook]);
  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    if (hash.has('token')) {
      sessionStorage.setItem('on-token', hash.get('token')!);
      history.replaceState(null, '', location.pathname);
    }
    setReady(true);
  }, []);
  const notebooks = useQuery({
    queryKey: ['notebooks'],
    queryFn: () => api<Notebook[]>('/notebooks'),
    enabled: ready,
  });
  const sources = useQuery({
    queryKey: ['sources', notebook],
    queryFn: () => api<Source[]>(`/notebooks/${notebook}/sources`),
    enabled: !!notebook,
    refetchInterval: (query) =>
      query.state.data?.some(
        (s) =>
          ['queued', 'processing'].includes(s.status) ||
          ['queued', 'processing'].includes(s.refresh_status || ''),
      )
        ? 1500
        : false,
  });
  useEffect(() => {
    if (notebooks.data && !notebooks.data.some((n) => n.id === notebook))
      setNotebook(notebooks.data[0]?.id || '');
  }, [notebooks.data, notebook]);
  useEffect(() => {
    if (notebooks.error || sources.error) report((notebooks.error || sources.error)!.message);
  }, [notebooks.error, sources.error, report]);
  const provider = useQuery({
    queryKey: ['settings'],
    queryFn: () => api<Settings>('/settings'),
    enabled: ready && !settings,
  });
  const active = notebooks.data?.find((n) => n.id === notebook);
  // Keep editors mounted until every pending save has succeeded. Their cleanup
  // cannot cancel a transition when an invalid or conflicted draft cannot save.
  const guardNavigation = async (changeView: () => void | Promise<void>) => {
    if (!(await settlePendingEdits())) {
      report(tr('notebook.unsaved'));
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
    client.invalidateQueries({ queryKey: ['sources', notebook] });
    client.invalidateQueries({ queryKey: ['notebooks'] });
  };
  const cite = (e: Evidence) => {
    if (e.kind === 'note' || e.note_id) {
      setNoteCitation(e);
      return;
    }
    const source = sources.data?.find((s) => s.id === e.source_id);
    if (source) {
      setSelected({ source, evidence: e });
      setShowSources(true);
    } else report(tr('error.sourceMissing'));
  };
  const openApps = () => {
    void guardNavigation(() => {
      setApps(true);
      setSettings(false);
    });
  };
  const selectNotebook = (id: string) => {
    setNotebook(id);
    setTab('chat');
    setSettings(false);
    setApps(false);
    setSelected(null);
  };
  const removedNotebook = (id: string) => {
    if (notebook === id) {
      setNotebook('');
      setSelected(null);
      setTab('chat');
      setShowSources(false);
    }
  };
  const toggleSources = () => {
    setShowSources(!(showSources || selected));
    setSelected(null);
  };
  const createNotebook = async () => {
    setBusy(true);
    try {
      await guardNavigation(async () => {
        const n = await api<Notebook>('/notebooks', 'POST', {
          title: name.trim(),
        });
        await client.invalidateQueries({ queryKey: ['notebooks'] });
        // The dialog can close while creation is in flight, letting
        // the editor acquire newer changes before this response.
        await guardNavigation(() => {
          setNotebook(n.id);
          setTab('chat');
          setSettings(false);
          setApps(false);
          setSelected(null);
          setCreate(false);
          setName('');
        });
      });
    } catch (e) {
      report((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return {
    tr,
    localize,
    notebooks,
    sources,
    provider,
    active,
    notebook,
    tab,
    settings,
    apps,
    showSources,
    create,
    name,
    busy,
    error,
    noteCitation,
    selected,
    report,
    navigate,
    openSettings,
    openCreate,
    openApps,
    openSources,
    refresh,
    cite,
    selectNotebook,
    removedNotebook,
    toggleSources,
    createNotebook,
    setSettings,
    setCreate,
    setName,
    setError,
    setNoteCitation,
    setSelected,
  };
}

export type WorkspaceController = ReturnType<typeof useWorkspace>;
