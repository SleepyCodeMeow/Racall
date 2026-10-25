import type { Evidence } from '../../lib/api';
import type { SourceDetailController } from './use-source-detail';

export function SourceDocument({
  detail,
  evidence,
}: {
  detail: SourceDetailController;
  evidence?: Evidence;
}) {
  const { tr, fileUrl, shown, document, anchor } = detail;
  return (
    <>
      {fileUrl && shown.type === 'pdf' ? (
        <iframe
          title={tr('source.pdf')}
          className="pdf-preview"
          src={`${fileUrl}#page=${evidence?.location.page || 1}`}
        />
      ) : (
        <div className="source-content">
          {document.isPending ? (
            <div className="skeleton h-40" />
          ) : !document.data?.document ? (
            <p className="muted">{tr('source.processingNotice')}</p>
          ) : (
            document.data.document.elements.map((element, i) => {
              const highlighted =
                !!evidence &&
                evidence.version === shown.version &&
                evidence.location.element === i &&
                element.text.slice(evidence.location.offset_start, evidence.location.offset_end) ===
                  evidence.quote;
              return (
                <div
                  key={i}
                  ref={highlighted ? anchor : undefined}
                  className={`source-element ${highlighted ? 'highlighted' : ''}`}
                >
                  {(element.page || element.section) && (
                    <small>
                      {element.page ? tr('source.page', { page: element.page }) : element.section}
                    </small>
                  )}
                  <p>
                    {highlighted && evidence ? (
                      <>
                        {element.text.slice(0, evidence.location.offset_start)}
                        <mark>{evidence.quote}</mark>
                        {element.text.slice(evidence.location.offset_end)}
                      </>
                    ) : (
                      element.text
                    )}
                  </p>
                </div>
              );
            })
          )}
        </div>
      )}
    </>
  );
}
