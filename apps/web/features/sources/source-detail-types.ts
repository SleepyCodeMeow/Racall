import type { Source, Evidence } from '../../lib/api';

export type DocumentData = {
  source: Source;
  document: {
    elements: { text: string; page?: number; section?: string }[];
  } | null;
};
export type Version = {
  version: string;
  title: string;
  type: string;
  created_at: string;
  current: boolean;
};

export type SourceDetailProps = {
  notebook: string;
  source: Source;
  evidence?: Evidence;
  close: () => void;
  refresh: () => void;
  report: (message: string) => void;
};
