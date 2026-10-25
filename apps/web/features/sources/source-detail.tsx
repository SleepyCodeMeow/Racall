'use client';
import { ArrowSquareOut, X } from '@phosphor-icons/react';
import { locationLabel } from '../../lib/api';
import { SourceDocument } from './source-document';
import { useSourceDetail } from './use-source-detail';
import type { SourceDetailProps } from './source-detail-types';

export function SourceDetail(props: SourceDetailProps) {
  const { source, evidence, close } = props;
  const detail = useSourceDetail(props);
  const {
    tr,
    locale,
    localize,
    shown,
    version,
    archived,
    busy,
    notice,
    fileUrl,
    input,
    processing,
    versions,
    document,
    setPicked,
    update,
    openOriginal,
  } = detail;
  return (
    <aside className="source-panel detail-panel">
      <div className="panel-heading">
        <span>{tr('source.original')}</span>
        <button className="icon-button" aria-label={tr('source.close')} onClick={close}>
          <X size={18} />
        </button>
      </div>
      <div className="detail-title">
        <span className="file-type">{shown.type.toUpperCase()}</span>
        <h2>{shown.title}</h2>
        {evidence && <div className="location">{locationLabel(evidence)}</div>}
        <label className="source-version-picker">
          {tr('source.version')}
          <select
            value={version || ''}
            onChange={(e) => setPicked(e.target.value)}
            disabled={versions.isPending}
          >
            {!versions.data && <option value={version}>{tr('common.loading')}</option>}
            {versions.data?.map((v) => (
              <option key={v.version} value={v.version}>
                {v.current ? tr('source.currentVersion') : tr('source.previousVersion')} ·{' '}
                {new Date(v.created_at).toLocaleString(locale)}
              </option>
            ))}
          </select>
        </label>
        {versions.error && (
          <p className="source-error" role="alert">
            {versions.error.message}
          </p>
        )}
        <div className="source-version-actions">
          <button
            className="text-button"
            disabled={document.isPending || !!document.error}
            onClick={openOriginal}
          >
            {tr('source.openOriginal')} <ArrowSquareOut size={15} />
          </button>
          {source.url ? (
            <button
              className="text-button"
              disabled={busy || processing}
              onClick={() => void update('refresh')}
            >
              {tr('source.refreshUrl')}
            </button>
          ) : (
            <button
              className="text-button"
              disabled={busy || processing}
              onClick={() => input.current?.click()}
            >
              {tr('source.replaceFile')}
            </button>
          )}
          <input
            className="hidden"
            aria-label={tr('source.replacementFile')}
            ref={input}
            type="file"
            accept=".pdf,.md,.txt,.docx"
            onChange={(e) => {
              if (e.target.files?.[0]) void update('replace', e.target.files[0]);
            }}
          />
        </div>
        {fileUrl && shown.type !== 'pdf' && (
          <a className="text-button" href={fileUrl} download={shown.title}>
            {tr('source.download')}
          </a>
        )}
        {processing && (
          <p className="muted" role="status">
            {source.refresh_status ? tr('source.updating') : tr('source.processing')}
          </p>
        )}
        {notice && (
          <p className="muted" role="status">
            {notice}
          </p>
        )}
        {(source.error || source.refresh_error) && (
          <div className="source-error" role="alert">
            <p>{source.refresh_error ? tr('source.updateFailed') : tr('source.failed')}</p>
            <p>{localize(source.refresh_error || source.error || '')}</p>
            <button
              className="text-button"
              disabled={busy || processing}
              onClick={() => void update('retry')}
            >
              {tr('common.retry')}
            </button>
          </div>
        )}
      </div>
      {archived && (
        <div className="draft-notice">
          <strong>{tr('source.previousVersion')}</strong>
          <p>{tr('source.versionChanged')}</p>
        </div>
      )}
      {document.error && (
        <div className="source-error" role="alert">
          <p>{document.error.message}</p>
          {evidence && (
            <>
              <strong>{tr('source.savedPassage')}</strong>
              <blockquote>{evidence.quote}</blockquote>
            </>
          )}
        </div>
      )}
      <SourceDocument detail={detail} evidence={evidence} />
    </aside>
  );
}
