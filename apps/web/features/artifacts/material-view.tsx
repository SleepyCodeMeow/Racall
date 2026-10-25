"use client";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, NotePencil } from "@phosphor-icons/react";
import { api, Evidence, Material, Note } from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import { Markdown } from "../../components/markdown";
import { AnswerView } from "../chat/answer-view";
import { generationKindLabel } from "../jobs/generation-job";

export function MaterialView({ notebook, id, cite, report, navigate }: {
  notebook: string; id: string; cite: (evidence: Evidence) => void;
  report: (message: string) => void; navigate?: (tab: string) => void;
}) {
  const { tr } = useI18n();
  const client = useQueryClient();
  const [copying, setCopying] = useState(false);
  const [copied, setCopied] = useState(false);
  const query = useQuery({ queryKey: ["material", notebook, id], enabled: !!id,
    queryFn: () => api<Material>(`/notebooks/${notebook}/materials/${encodeURIComponent(id)}`) });
  useEffect(() => { setCopied(false); }, [id]);
  useEffect(() => { if (query.error) report(query.error.message); }, [query.error, report]);
  const material = query.data;
  if (query.isPending) return <p className="muted" role="status">{tr("common.loading")}</p>;
  if (!material) return <p className="muted">{tr("materials.unavailable")}</p>;
  const download = () => {
    const url = URL.createObjectURL(new Blob([material.body], { type: "text/markdown;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `Racall-${material.kind}-${material.id.replace(/[^a-zA-Z0-9_-]/g, "_")}.md`;
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <article className="material-view" data-material-id={material.id}>
    <div className="material-heading"><div>
      <small>{generationKindLabel(material.kind, tr)}{material.legacy ? ` · ${tr("materials.legacy")}` : ""}</small>
      <h2>{material.title}</h2>
    </div><div className="material-actions">
      <button type="button" className="secondary" data-testid="material-export" onClick={download}><ArrowDown size={15} />{tr("materials.export")}</button>
      <button type="button" className="secondary" data-testid="material-copy" disabled={copying || copied} onClick={async () => {
        if (copying || copied) return;
        setCopying(true);
        try {
          await api<Note>(`/notebooks/${notebook}/materials/${encodeURIComponent(id)}/copy`, "POST");
          await client.invalidateQueries({ queryKey: ["notes", notebook] });
          setCopied(true);
        } catch (error) { report((error as Error).message); }
        finally { setCopying(false); }
      }}><NotePencil size={15} />{copied ? tr("materials.copied") : tr("materials.copy")}</button>
    </div></div>
    {copied && <p className="material-feedback" role="status">{tr("materials.copyHint")}
      {navigate && <button type="button" className="text-button" onClick={() => navigate("notes")}>{tr("materials.openNotes")}</button>}
    </p>}
    {material.context_info?.evidence_truncated && <p className="muted" role="status">{tr("materials.partialContext")}</p>}
    <div className="note-preview material-markdown"><Markdown text={material.body} /></div>
    {!!material.answer?.citations.length && <AnswerView answer={{ ...material.answer, claims: [], message: "", validated: false }} cite={cite} />}
  </article>;
}
