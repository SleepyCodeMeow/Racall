export type Notebook = {
  id: string;
  title: string;
  sources_count: number;
  created_at: string;
};
export type Source = {
  version?: string;
  id: string;
  title: string;
  type: string;
  status: string;
  chunks: number;
  size: number;
  error?: string;
  url?: string;
  search_mode?: string;
  refresh_status?: string;
  refresh_error?: string;
};
export type Note = {
  id: string;
  title: string;
  body: string;
  revision?: string;
};
export type Location = {
  element: number;
  page?: number;
  section?: string;
  type?: string;
  line_start?: number;
  line_end?: number;
  offset_start: number;
  offset_end: number;
};
export type Evidence = {
  id: string;
  source_id: string;
  title: string;
  quote: string;
  location: Location;
  number?: number;
  version: string;
  kind?: 'source' | 'note';
  note_id?: string;
};
export type ContextSelection = { source_ids: string[] | null; note_ids: string[] };
export type ContextInfo = {
  source_count: number;
  note_count: number;
  history_turns: number;
  history_truncated?: boolean;
  evidence_truncated?: boolean;
};
export type Answer = {
  claims: { text: string; evidence_ids: string[] }[];
  citations: Evidence[];
  message: string;
  validated: boolean;
  mode: string;
};
export type ChatTurn = {
  id: string;
  question: string;
  mode: 'ask' | 'search';
  status: 'running' | 'completed' | 'failed' | 'interrupted';
  answer?: Answer;
  evidence?: Evidence[];
  context_info?: ContextInfo;
  error_code?: string;
};
export type ChatThread = {
  id: string;
  title: string;
  updated_at: string;
  turns: ChatTurn[];
  context?: ContextSelection;
};
export type GenerationKind = 'research' | 'summary' | 'study_guide' | 'review_questions';
export type GenerationJob = {
  id: string;
  request_id: string;
  kind: GenerationKind;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';
  stage: string;
  steps: { stage: string; at: string; detail?: Record<string, unknown> }[];
  question: string;
  title: string;
  language: 'en' | 'ru';
  created_at: string;
  updated_at: string;
  error?: string;
  retry_of?: string;
  cancel_requested?: boolean;
  result?: { research_id?: string; material_id?: string };
};
export type Material = {
  id: string;
  title: string;
  kind: GenerationKind;
  body: string;
  answer: Answer;
  created_at: string;
  job_id?: string;
  legacy?: boolean;
  research_id?: string;
  context_info?: Partial<ContextInfo>;
};
export type NoteDraft = { draft_id: string; note: Note; updated_at: string };
export type Research = {
  id: string;
  question: string;
  status: string;
  answer?: Answer;
  steps: {
    stage: string;
    query?: string;
    count?: number;
    accepted?: boolean;
  }[];
};
export type ProviderId =
  'openai' | 'anthropic' | 'ollama' | 'ollama_cloud' | 'llama_cpp' | 'openai_compatible';
export type EmbeddingProviderId = Exclude<ProviderId, 'anthropic' | 'ollama_cloud'>;
export type ProviderProfile = {
  base_url: string;
  model: string;
  has_key: boolean;
};
export type EmbeddingSettings = ProviderProfile & {
  provider: EmbeddingProviderId;
};
export type Settings = {
  provider: ProviderId;
  profiles: Record<ProviderId, ProviderProfile>;
  embeddings: EmbeddingSettings;
  base_url: string;
  model: string;
  embedding_model: string;
  embedding_base_url: string;
  has_key: boolean;
  vault_path: string;
};
