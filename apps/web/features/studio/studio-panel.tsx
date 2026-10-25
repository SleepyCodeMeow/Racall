'use client';
import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Sparkle } from '@phosphor-icons/react';
import {
  api,
  ContextSelection,
  Evidence,
  GenerationJob,
  GenerationKind,
  Settings,
} from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import type { MessageKey } from '../../lib/translations';
import { allMaterials, ContextPicker, copySelection } from '../context/context-picker';
import { GenerationJobCard, generationKindLabel } from '../jobs/generation-job';
import { useGenerationJobs } from '../jobs/use-generation-jobs';
import { MaterialView } from '../artifacts/material-view';

type StudioKind = Exclude<GenerationKind, 'research'>;
const defaults: Record<StudioKind, MessageKey> = {
  summary: 'studio.defaultSummary',
  study_guide: 'studio.defaultStudyGuide',
  review_questions: 'studio.defaultReviewQuestions',
};
export function StudioPanel({
  notebook,
  cite,
  report,
  navigate,
  settings,
}: {
  notebook: string;
  cite: (evidence: Evidence) => void;
  report: (message: string) => void;
  navigate: (tab: string) => void;
  settings: () => void;
}) {
  const { tr, locale } = useI18n();
  const client = useQueryClient();
  const [kind, setKind] = useState<StudioKind>('summary');
  const [instructions, setInstructions] = useState('');
  const [context, setContext] = useState<ContextSelection>(allMaterials);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [selectedJob, setSelectedJob] = useState('');
  const [material, setMaterial] = useState('');
  const jobs = useGenerationJobs(notebook, report);
  const provider = useQuery({ queryKey: ['settings'], queryFn: () => api<Settings>('/settings') });
  useEffect(() => {
    if (provider.error) report(provider.error.message);
  }, [provider.error, report]);
  const modelMissing = !!provider.data && !provider.data.model.trim();
  const emptySelection = context.source_ids?.length === 0 && context.note_ids.length === 0;
  const completed = jobs.data?.find((job) => job.id === selectedJob && job.status === 'completed');
  useEffect(() => {
    if (!completed?.result?.material_id) return;
    setMaterial(completed.result.material_id);
    void client.invalidateQueries({ queryKey: ['materials', notebook] });
  }, [completed?.id, completed?.result?.material_id, client, notebook]);
  const accept = (job: GenerationJob) => {
    setSelectedJob(job.id);
    setMaterial('');
    client.setQueryData<GenerationJob[]>(['jobs', notebook], (old) => [
      job,
      ...(old || []).filter((item) => item.id !== job.id),
    ]);
  };
  return (
    <div className="page-content studio">
      <div className="eyebrow">{tr('nav.studio')}</div>
      <h2>{tr('studio.title')}</h2>
      <p className="muted">{tr('studio.description')}</p>
      {modelMissing && (
        <div className="studio-model-missing" role="status">
          <p>{tr('studio.modelMissing')}</p>
          <button type="button" className="secondary" onClick={settings}>
            {tr('studio.configure')}
          </button>
        </div>
      )}
      <form
        className="studio-form"
        onSubmit={async (event) => {
          event.preventDefault();
          if (
            submitting.current ||
            modelMissing ||
            emptySelection ||
            provider.isPending ||
            provider.isError
          )
            return;
          submitting.current = true;
          setBusy(true);
          try {
            const job = await api<GenerationJob>(`/notebooks/${notebook}/jobs`, 'POST', {
              request_id: crypto.randomUUID(),
              kind,
              question: instructions.trim() || tr(defaults[kind]),
              language: locale,
              context: copySelection(context),
            });
            accept(job);
            await client.invalidateQueries({ queryKey: ['jobs', notebook] });
          } catch (error) {
            report((error as Error).message);
          } finally {
            submitting.current = false;
            setBusy(false);
          }
        }}
      >
        <label>
          {tr('studio.format')}
          <select
            data-testid="studio-format"
            value={kind}
            disabled={busy}
            onChange={(event) => setKind(event.target.value as StudioKind)}
          >
            {(['summary', 'study_guide', 'review_questions'] as StudioKind[]).map((value) => (
              <option key={value} value={value}>
                {generationKindLabel(value, tr)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {tr('studio.instructions')}
          <textarea
            rows={3}
            maxLength={2000}
            value={instructions}
            disabled={busy}
            onChange={(event) => setInstructions(event.target.value)}
            placeholder={tr(defaults[kind])}
          />
        </label>
        <div className="generation-form-actions">
          <ContextPicker
            notebook={notebook}
            value={context}
            onChange={setContext}
            disabled={busy}
            report={report}
          />
          <button
            className="primary"
            data-testid="studio-generate"
            disabled={
              busy || modelMissing || emptySelection || provider.isPending || provider.isError
            }
          >
            <Sparkle size={17} />
            {busy ? tr('studio.starting') : tr('studio.generate')}
          </button>
        </div>
      </form>
      {selectedJob &&
        jobs.data
          ?.filter((job) => job.id === selectedJob)
          .map((job) => (
            <GenerationJobCard
              key={job.id}
              notebook={notebook}
              job={job}
              report={report}
              retried={accept}
              openResult={(item) => {
                if (item.result?.material_id) setMaterial(item.result.material_id);
              }}
            />
          ))}
      {material && (
        <div className="studio-result">
          <MaterialView
            key={material}
            notebook={notebook}
            id={material}
            cite={cite}
            report={report}
            navigate={navigate}
          />
        </div>
      )}
      <div className="section-heading mt-8">
        <h3>{tr('jobs.recent')}</h3>
      </div>
      {jobs.isPending && <p className="muted">{tr('common.loading')}</p>}
      {jobs.data
        ?.filter((job) => job.kind !== 'research' && job.id !== selectedJob)
        .map((job) => (
          <GenerationJobCard
            key={job.id}
            notebook={notebook}
            job={job}
            report={report}
            retried={accept}
            openResult={(item) => {
              setSelectedJob(item.id);
              if (item.result?.material_id) setMaterial(item.result.material_id);
            }}
          />
        ))}
      {jobs.data && !jobs.data.some((job) => job.kind !== 'research') && (
        <p className="muted">{tr('studio.empty')}</p>
      )}
    </div>
  );
}
