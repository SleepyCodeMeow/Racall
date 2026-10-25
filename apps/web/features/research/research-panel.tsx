"use client";
import { useI18n } from "../../lib/i18n";
import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, Sparkle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ContextSelection, Evidence, GenerationJob, Research } from "../../lib/api";
import { AnswerView } from "../chat/answer-view";
import { allMaterials, ContextPicker, copySelection } from "../context/context-picker";
import { GenerationJobCard } from "../jobs/generation-job";
import { useGenerationJobs } from "../jobs/use-generation-jobs";

export function ResearchPanel({
  notebook,
  cite,
  report,
}: {
  notebook: string;
  cite: (e: Evidence) => void;
  report: (s: string) => void;
}) {
  const { tr, locale } = useI18n();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["research", notebook],
    queryFn: () => api<Research[]>(`/notebooks/${notebook}/research`),
  });
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState<Research>();
  const [saved, setSaved] = useState(false);
  const [context, setContext] = useState<ContextSelection>(allMaterials);
  const [selectedJob, setSelectedJob] = useState("");
  const submitting = useRef(false);
  const jobs = useGenerationJobs(notebook, report);
  const completed = jobs.data?.find(job => job.id === selectedJob && job.status === "completed");
  useEffect(() => {
    if (query.error) report(query.error.message);
  }, [query.error, report]);
  useEffect(() => {
    if (!completed?.result?.research_id) return;
    let active = true;
    void client.fetchQuery({ queryKey: ["research", notebook], staleTime: 0,
      queryFn: () => api<Research[]>(`/notebooks/${notebook}/research`) }).then(items => {
        if (active) { setSession(items.find(item => item.id === completed.result?.research_id)); setSaved(false); }
      }).catch(error => { if (active) report((error as Error).message); });
    void client.invalidateQueries({ queryKey: ["materials", notebook] });
    return () => { active = false; };
  }, [completed?.id, completed?.result?.research_id, notebook, client, report]);
  const accept = (job: GenerationJob) => {
    setSelectedJob(job.id); setSession(undefined); setSaved(false);
    client.setQueryData<GenerationJob[]>(["jobs", notebook], old => [job, ...(old || []).filter(item => item.id !== job.id)]);
  };
  return (
    <div className="page-content research">
      <div className="eyebrow">{tr("research.eyebrow")}</div>
      <h2>
        {tr("research.title1")}
        <br />
        {tr("research.title2")}
      </h2>
      <p className="muted">{tr("research.description")}</p>
      <form
        className="research-form"
        onSubmit={async (e) => {
          e.preventDefault();
          if (submitting.current || !question.trim()) return;
          submitting.current = true;
          setBusy(true);
          setSaved(false);
          try {
            const result = await api<GenerationJob>(
              `/notebooks/${notebook}/jobs`,
              "POST",
              { request_id: crypto.randomUUID(), kind: "research", question: question.trim(), language: locale,
                context: copySelection(context) },
            );
            accept(result);
            await client.invalidateQueries({ queryKey: ["jobs", notebook] });
          } catch (e) {
            report((e as Error).message);
          } finally {
            setBusy(false);
            submitting.current = false;
          }
        }}
      >
        <label>
          {tr("research.topic")}
          <textarea
            rows={3}
            placeholder={tr("research.placeholder")}
            required
            maxLength={2000}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={busy}
          />
        </label>
        <div className="generation-form-actions"><ContextPicker notebook={notebook} value={context}
          onChange={setContext} disabled={busy} report={report} />
        <button className="primary" disabled={busy || !question.trim() || (context.source_ids?.length === 0 && context.note_ids.length === 0)}>
          <Sparkle size={17} />
          {busy ? tr("research.busy") : tr("research.start")}
        </button>
        </div>
      </form>
      {busy && (
        <div className="research-progress">
          <span className="pulse-dot" />
          {tr("research.progress")}
        </div>
      )}
      {jobs.data?.filter(job => job.kind === "research").map(job => <GenerationJobCard
        key={job.id} notebook={notebook} job={job} report={report} retried={accept}
        openResult={item => {
          setSelectedJob(item.id);
          const existing = query.data?.find(value => value.id === item.result?.research_id);
          if (existing) { setSession(existing); setSaved(false); }
        }} />)}
      {session && (
        <div className="research-result">
          <h3>{session.question}</h3>
          <div className="step-log">
            {session.steps.map((step, i) => (
              <span key={i}>
                {
                  (
                    {
                      planner: tr("research.plan"),
                      retrieval: tr("common.search"),
                      critic: tr("research.review"),
                      revision: tr("research.revision"),
                    } as Record<string, string>
                  )[step.stage]
                }
                {step.count !== undefined ? `: ${step.count}` : ""}
              </span>
            ))}
          </div>
          {session.answer ? (
            <AnswerView answer={session.answer} cite={cite} />
          ) : (
            <p>
              {tr(
                session.status === "failed"
                  ? "research.failed"
                  : session.status === "interrupted"
                    ? "research.interruptedDetail"
                    : "research.pending",
              )}
            </p>
          )}
          {session.answer?.validated && (
            <button
              className="secondary mt-5"
              disabled={saved}
              onClick={async () => {
                try {
                  await api(
                    `/notebooks/${notebook}/research/${session.id}/save`,
                    "POST",
                  );
                  setSaved(true);
                  client.invalidateQueries({
                    queryKey: ["artifacts", notebook],
                  });
                  client.invalidateQueries({ queryKey: ["materials", notebook] });
                } catch (e) {
                  report((e as Error).message);
                }
              }}
            >
              {saved ? tr("research.saved") : tr("research.save")}
            </button>
          )}
        </div>
      )}
      <div className="section-heading mt-8">
        <h3>{tr("research.previous")}</h3>
      </div>
      {query.data?.map((s) => (
        <button
          className="research-history"
          key={s.id}
          onClick={() => {
            setSession(s);
            setSelectedJob("");
            setSaved(false);
          }}
        >
          <span>{s.question}</span>
          <small>
            {s.status === "completed"
              ? tr("common.completed")
              : s.status === "failed"
                ? tr("common.error")
                : s.status === "interrupted"
                  ? tr("research.interrupted")
                  : tr("research.pending")}
          </small>
          <ArrowUpRight size={16} />
        </button>
      ))}
    </div>
  );
}
