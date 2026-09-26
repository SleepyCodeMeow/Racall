"use client";
import { useI18n } from "../../lib/i18n";
import { Check, ArrowUpRight } from "@phosphor-icons/react";
import { Answer, Evidence, locationLabel } from "../../lib/api";

export function AnswerView({
  answer,
  cite,
}: {
  answer: Answer;
  cite: (e: Evidence) => void;
}) {
  const { tr, localize } = useI18n();
  return (
    <div className="answer-body">
      {answer.claims.map((claim, i) => (
        <p key={i}>
          {claim.text}{" "}
          <span className="citation-buttons">
            {claim.evidence_ids.map((id) => {
              const e = answer.citations.find((c) => c.id === id);
              return e ? (
                <button
                  key={id}
                  title={`${e.title} · ${locationLabel(e)}`}
                  onClick={() => cite(e)}
                >
                  {e.number}
                </button>
              ) : null;
            })}
          </span>
        </p>
      ))}
      {answer.message && <p className="muted">{localize(answer.message)}</p>}
      {answer.citations.length > 0 && (
        <div className="evidence-list">
          <div className="eyebrow">{tr("answer.sources")}</div>
          {answer.citations.map((e) => (
            <button key={e.id} onClick={() => cite(e)}>
              <span className="evidence-number">{e.number}</span>
              <span>
                <strong>{e.title}</strong>
                <small>{locationLabel(e)}</small>
              </span>
              <ArrowUpRight size={16} />
            </button>
          ))}
        </div>
      )}
      {answer.validated && (
        <div className="verification">
          <Check size={14} /> {tr("answer.verified")}
        </div>
      )}
    </div>
  );
}
