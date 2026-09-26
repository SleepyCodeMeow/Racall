import { translate as tr, localizeMessage } from "./translations";
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
  mode: "ask" | "search";
  status: "running" | "completed" | "failed" | "interrupted";
  answer?: Answer;
  evidence?: Evidence[];
};
export type ChatThread = {
  id: string;
  title: string;
  updated_at: string;
  turns: ChatTurn[];
};
export type NoteDraft = { draft_id: string; note: Note; updated_at: string };
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
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
export type Settings = {
  base_url: string;
  model: string;
  embedding_model: string;
  has_key: boolean;
  vault_path: string;
};
declare global {
  interface Window {
    desktop?: {
      connection: () => Promise<{ origin: string }>;
      openVault: () => Promise<string>;
    };
  }
}

let connection: Promise<string> | undefined;
export async function origin() {
  if (!connection)
    connection = window.desktop
      ? window.desktop.connection().then((c) => c.origin)
      : Promise.resolve(window.location.origin);
  return connection;
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const token = sessionStorage.getItem("on-token");
  const headers: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};
  if (body && !(body instanceof FormData))
    headers["Content-Type"] = "application/json";
  const response = await fetch((await origin()) + "/api" + path, {
    method,
    headers,
    body:
      body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  }).catch(() => {
    throw new Error(tr("error.network"));
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      typeof error.detail === "string"
        ? localizeMessage(error.detail)
        : response.status === 422
          ? tr("error.validation")
          : tr("error.request", { status: response.status }),
      response.status,
    );
  }
  return response.json();
}
export async function originalFile(
  notebook: string,
  source: Source,
  version?: string,
): Promise<string> {
  const token = sessionStorage.getItem("on-token");
  const response = await fetch(
    (await origin()) +
      `/api/notebooks/${notebook}/sources/${source.id}${version ? `/versions/${version}` : ""}/original`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  ).catch(() => {
    throw new Error(tr("error.network"));
  });
  if (!response.ok) throw new Error(tr("error.original"));
  const data = await response.blob();
  return URL.createObjectURL(
    new Blob([data], {
      type: source.type === "pdf" ? "application/pdf" : data.type,
    }),
  );
}
export function locationLabel(e: Evidence) {
  return (
    [
      e.location.page && tr("source.pageShort", { page: e.location.page }),
      e.location.section,
      !e.location.page &&
        e.location.line_start &&
        tr("source.lines", {
          start: e.location.line_start,
          end: e.location.line_end || e.location.line_start,
        }),
    ]
      .filter(Boolean)
      .join(" · ") || tr("source.passage")
  );
}
