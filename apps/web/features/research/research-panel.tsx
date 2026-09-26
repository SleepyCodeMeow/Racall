"use client";
import { useI18n } from "../../lib/i18n";
import { useEffect, useState } from "react";
import { ArrowUpRight, Sparkle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Evidence, Research } from "../../lib/api";
import { AnswerView } from "../chat/answer-view";

export function ResearchPanel({
  notebook,
  cite,
  report,
}: {
  notebook: string;
  cite: (e: Evidence) => void;
  report: (s: string) => void;
}) {
  const { tr, localize } = useI18n();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["research", notebook],
    queryFn: () => api<Research[]>(`/notebooks/${notebook}/research`),
  });
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState<Research>();
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (query.error) report(query.error.message);
  }, [query.error, report]);
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
          setBusy(true);
          setSaved(false);
          try {
            const result = await api<Research>(
              `/notebooks/${notebook}/research`,
              "POST",
              { question },
            );
            setSession(result);
            client.invalidateQueries({ queryKey: ["research", notebook] });
          } catch (e) {
            report((e as Error).message);
          } finally {
            setBusy(false);
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
          />
        </label>
        <button className="primary" disabled={busy}>
          <Sparkle size={17} />
          {busy ? tr("research.busy") : tr("research.start")}
        </button>
      </form>
      {busy && (
        <div className="research-progress">
          <span className="pulse-dot" />
          {tr("research.progress")}
        </div>
      )}
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
            setSaved(false);
          }}
        >
          <span>{s.question}</span>
          <small>
            {s.status === "completed"
              ? tr("common.completed")
              : s.status === "failed"
                ? tr("common.error")
                : tr("research.interrupted")}
          </small>
          <ArrowUpRight size={16} />
        </button>
      ))}
    </div>
  );
}
