"use client";
import { Evidence, locationLabel } from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import { Modal } from "../../components/modal";

export function NoteCitation({ evidence, close }: { evidence: Evidence; close: () => void }) {
  const { tr } = useI18n();
  return <Modal title={evidence.title} close={close}>
    <div className="note-citation">
      <p className="muted">{tr("context.noteSnapshot")}</p>
      <p>{locationLabel(evidence)}</p>
      <blockquote>{evidence.quote}</blockquote>
      <small>{tr("context.revision", { revision: evidence.version })}</small>
    </div>
  </Modal>;
}
