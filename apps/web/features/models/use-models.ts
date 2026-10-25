'use client';
import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type ProviderId, type Settings } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import { type DownloadJob, isDownloadActive, type ModelCatalog } from './types';

/** Model discovery uses saved connection profiles; opening the picker never starts inference or a pull. */
export function useModels(open: boolean, providerOverride?: ProviderId) {
  const { tr } = useI18n();
  const client = useQueryClient();
  const settings = useQuery({
    queryKey: ['settings'],
    queryFn: () => api<Settings>('/settings'),
    staleTime: 15_000,
  });
  const provider = providerOverride ?? settings.data?.provider;
  const catalog = useQuery({
    queryKey: ['models', provider],
    queryFn: () => api<ModelCatalog>(`/models?provider=${encodeURIComponent(provider!)}`),
    enabled: open && !!settings.data && !!provider,
    staleTime: 30_000,
    retry: false,
  });
  const select = useMutation({
    mutationFn: async (model: string) => {
      const current = settings.data;
      if (!current || !provider) throw new Error(tr('models.notReady'));
      // A partial profile patch keeps credentials, other profiles, and embeddings intact.
      await api('/settings', 'PUT', {
        provider,
        profiles: {
          [provider]: { base_url: current.profiles[provider].base_url, model: model.trim() },
        },
      });
      return api<Settings>('/settings');
    },
    onSuccess: async (updated) => {
      client.setQueryData(['settings'], updated);
      await Promise.all([
        client.invalidateQueries({ queryKey: ['provider'] }),
        client.invalidateQueries({ queryKey: ['models'] }),
      ]);
    },
  });
  const saved = settings.data;
  const selectedCatalog = client.getQueryData<ModelCatalog>(['models', saved?.provider]);
  const selectedModelInfo = selectedCatalog?.models.find(
    (model) => model.id === saved?.profiles[saved.provider].model,
  );
  return { settings, catalog, select, provider, selectedModelInfo };
}

/** Keep polling only the active job; completed downloads do not select a model automatically. */
export function useModelDownload(open: boolean, provider?: ProviderId) {
  const client = useQueryClient();
  const [jobId, setJobId] = useState('');
  const [createdJob, setCreatedJob] = useState<DownloadJob>();
  const refreshed = useRef('');
  const recovery = useQuery({
    queryKey: ['model-download-current'],
    queryFn: () => api<{ job: DownloadJob | null }>('/models/downloads'),
    enabled: open && provider === 'ollama',
    staleTime: 0,
    retry: false,
  });
  useEffect(() => {
    // The latest job may have changed while this picker was closed or another view was open.
    if (!recovery.data || recovery.data.job?.id === jobId) return;
    setCreatedJob(recovery.data.job ?? undefined);
    setJobId(recovery.data.job?.id ?? '');
  }, [recovery.data, jobId]);
  const status = useQuery({
    queryKey: ['model-download', jobId],
    queryFn: () => api<DownloadJob>(`/models/downloads/${encodeURIComponent(jobId)}`),
    enabled: !!jobId,
    retry: false,
    refetchInterval: (query) => (isDownloadActive(query.state.data ?? createdJob) ? 1000 : false),
  });
  const job = status.data ?? createdJob;
  useEffect(() => {
    if (job?.status === 'completed' && refreshed.current !== job.id) {
      refreshed.current = job.id;
      void client.invalidateQueries({ queryKey: ['models'] });
    }
  }, [client, job]);
  const start = useMutation({
    mutationFn: (model: string) =>
      api<DownloadJob>('/models/downloads', 'POST', { model: model.trim() }),
    onMutate: () => client.cancelQueries({ queryKey: ['model-download-current'] }),
    onSuccess: (next) => {
      client.setQueryData(['model-download-current'], { job: next });
      client.setQueryData(['model-download', next.id], next);
      setCreatedJob(next);
      setJobId(next.id);
    },
  });
  const cancel = useMutation({
    mutationFn: () => api<DownloadJob>(`/models/downloads/${encodeURIComponent(jobId)}`, 'DELETE'),
    onSuccess: (next) => {
      client.setQueryData(['model-download-current'], { job: next });
      client.setQueryData(['model-download', next.id], next);
    },
  });
  return {
    job,
    start,
    cancel,
    error: status.error ?? recovery.error,
    active: isDownloadActive(job),
  };
}
