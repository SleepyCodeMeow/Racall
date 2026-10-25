import type { ProviderId } from '../../lib/api';

export type AvailableModel = {
  id: string;
  kind: 'local' | 'cloud' | 'server';
  installed: boolean;
  size_bytes?: number;
};

export type ModelCatalog = {
  provider: ProviderId;
  selected_model: string;
  models: AvailableModel[];
  can_download: boolean;
};

export type DownloadJob = {
  id: string;
  model: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';
  phase:
    | 'queued'
    | 'manifest'
    | 'downloading'
    | 'verifying'
    | 'writing'
    | 'completed'
    | 'cancelled'
    | 'interrupted'
    | 'failed';
  completed: number;
  total: number;
  error?: string;
};

export function isDownloadActive(job?: DownloadJob | null): boolean {
  return job?.status === 'queued' || job?.status === 'running';
}
