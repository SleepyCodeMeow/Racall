"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText } from "@phosphor-icons/react";
import { api, Evidence, Material } from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import { MaterialView } from "./material-view";

export function MaterialLibrary({ notebook, cite, report, navigate }: {
  notebook: string; cite: (evidence: Evidence) => void;
  report: (message: string) => void; navigate: (tab: string) => void;
}) {
  const { tr } = useI18n();
  const [selected, setSelected] = useState("");
  const query = useQuery({ queryKey: ["materials", notebook],
    queryFn: () => api<Material[]>(`/notebooks/${notebook}/materials`) });
  useEffect(() => { if (query.error) report(query.error.message); }, [query.error, report]);
  return <div className="notes-layout material-library">
    <div className="note-picker"><h2>{tr("nav.artifacts")}</h2><p className="muted material-library-hint">{tr("materials.description")}</p>
      {query.isPending && <p className="muted">{tr("common.loading")}</p>}
      {query.data?.length === 0 && <p className="muted">{tr("reports.empty")}</p>}
      <div className="note-tabs">{query.data?.map(material => <button key={material.id}
        className={selected === material.id ? "selected" : ""} onClick={() => setSelected(material.id)}>
        <FileText size={17} /><span>{material.title}</span>
      </button>)}</div>
      <button type="button" className="text-button material-create" onClick={() => navigate("studio")}>{tr("materials.create")}</button>
    </div>
    <div className="note-editor">{selected
      ? <MaterialView key={selected} notebook={notebook} id={selected} cite={cite} report={report} navigate={navigate} />
      : <div className="editor-empty"><FileText size={28} /><h3>{tr("materials.choose")}</h3><p>{tr("materials.persisted")}</p></div>}
    </div>
  </div>;
}
