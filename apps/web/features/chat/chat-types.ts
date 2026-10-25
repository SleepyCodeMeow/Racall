import type { Evidence } from '../../lib/api';

export type ChatProps = {
  notebook: string;
  count: number;
  cite: (e: Evidence) => void;
  report: (s: string) => void;
  settings: () => void;
  openSources: () => void;
  navigate: (id: string) => void;
};
