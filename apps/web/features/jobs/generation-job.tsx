'use client';
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowUpRight, ArrowClockwise, Stop } from '@phosphor-icons/react';
import { api, GenerationJob, GenerationKind } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import type { MessageKey } from '../../lib/translations';
import { isActiveJob } from './use-generation-jobs';

type Translate = ReturnType<typeof useI18n>['tr'];
const kinds: Record<GenerationKind, MessageKey> = {
  research: 'nav.research',
  summary: 'studio.summary',
  study_guide: 'studio.studyGuide',
  review_questions: 'studio.reviewQuestions',
};
export function generationKindLabel(kind: GenerationKind, tr: Translate) {
  return tr(kinds[kind] || 'nav.research');
}
const stages: Record<string, MessageKey> = {
  queued: 'jobs.queued',
  context: 'jobs.stage.context',
  retrieval: 'jobs.stage.retrieval',
  planner: 'jobs.stage.planner',
  writer: 'jobs.stage.writer',
  critic: 'jobs.stage.critic',
  revision: 'jobs.stage.revision',
  saving: 'jobs.stage.saving',
  completed: 'jobs.completed',
  cancelled: 'jobs.cancelled',
  interrupted: 'jobs.interrupted',
  failed: 'jobs.failed',
};
const statuses: Record<string, MessageKey> = {
  queued: 'jobs.queued',
  running: 'jobs.running',
  completed: 'jobs.completed',
  failed: 'jobs.failed',
  cancelled: 'jobs.cancelled',
  interrupted: 'jobs.interrupted',
};
const errors: Record<string, MessageKey> = {
  context_changed: 'jobs.error.contextChanged',
  provider_changed: 'jobs.error.providerChanged',
  no_evidence: 'jobs.error.noEvidence',
  unverified_output: 'jobs.error.unverified',
  generation_failed: 'jobs.error.failed',
  interrupted: 'jobs.error.interrupted',
};

export function GenerationJobCard({
  notebook,
  job,
  report,
  openResult,
  retried,
}: {
  notebook: string;
  job: GenerationJob;
  report: (message: string) => void;
  openResult?: (job: GenerationJob) => void;
  retried?: (job: GenerationJob) => void;
}) {
  const { tr } = useI18n();
  const client = useQueryClient();
  const [busy, setBusy] = useState<'cancel' | 'retry' | null>(null);
  const change = async (action: 'cancel' | 'retry') => {
    if (busy) return;
    setBusy(action);
    try {
      const next = await api<GenerationJob>(
        `/notebooks/${notebook}/jobs/${job.id}/${action}`,
        'POST',
        action === 'retry' ? { request_id: crypto.randomUUID() } : undefined,
      );
      client.setQueryData<GenerationJob[]>(['jobs', notebook], (old) =>
        action === 'retry'
          ? [next, ...(old || [])]
          : (old || []).map((item) => (item.id === next.id ? next : item)),
      );
      if (action === 'retry') retried?.(next);
      await client.invalidateQueries({ queryKey: ['jobs', notebook] });
    } catch (error) {
      report((error as Error).message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <article
      className={`generation-job job-${job.status}`}
      data-job-id={job.id}
      data-status={job.status}
      aria-busy={isActiveJob(job)}
    >
      <div className="generation-job-heading">
        <div>
          <small>{generationKindLabel(job.kind, tr)}</small>
          <h4>{job.title || job.question}</h4>
        </div>
        <span className="job-status" role="status">
          {tr(statuses[job.status] || 'jobs.running')}
        </span>
      </div>
      {isActiveJob(job) && (
        <p className="job-current-stage">
          <span className="pulse-dot" />
          {tr(stages[job.stage] || 'jobs.running')}
        </p>
      )}
      {job.error && <p className="job-error">{tr(errors[job.error] || 'jobs.error.failed')}</p>}
      {job.status === 'interrupted' && !job.error && (
        <p className="muted">{tr('jobs.error.interrupted')}</p>
      )}
      {!!job.steps?.length && (
        <details className="job-stages">
          <summary>{tr('jobs.steps')}</summary>
          <ol>
            {job.steps.map((step, index) => (
              <li key={`${step.at}-${index}`}>
                {tr(stages[step.stage] || 'jobs.running')}
                {typeof step.detail?.count === 'number' ? ` · ${step.detail.count}` : ''}
              </li>
            ))}
          </ol>
        </details>
      )}
      <div className="job-actions">
        {isActiveJob(job) && (
          <button
            type="button"
            className="text-button"
            disabled={!!busy || job.cancel_requested}
            onClick={() => void change('cancel')}
          >
            <Stop size={14} />
            {busy === 'cancel' || job.cancel_requested
              ? tr('jobs.cancelling')
              : tr('common.cancel')}
          </button>
        )}
        {['failed', 'cancelled', 'interrupted'].includes(job.status) && (
          <button
            type="button"
            className="text-button"
            disabled={!!busy}
            onClick={() => void change('retry')}
          >
            <ArrowClockwise size={14} />
            {busy ? tr('jobs.updating') : tr('jobs.retryCurrent')}
          </button>
        )}
        {job.status === 'completed' &&
          openResult &&
          (job.result?.material_id || job.result?.research_id) && (
            <button type="button" className="text-button" onClick={() => openResult(job)}>
              {tr('jobs.openResult')}
              <ArrowUpRight size={14} />
            </button>
          )}
      </div>
      {job.status === 'cancelled' && <p className="job-footnote">{tr('jobs.cancelHint')}</p>}
    </article>
  );
}
