"use client";
import { X } from "@phosphor-icons/react";
import { useI18n } from "../../lib/i18n";
import type { MessageKey } from "../../lib/translations";
import { type DownloadJob, isDownloadActive } from "./types";

const phases: Record<DownloadJob["phase"], MessageKey> = {
  queued: "models.phaseQueued",
  manifest: "models.phaseManifest",
  downloading: "models.phaseDownloading",
  verifying: "models.phaseVerifying",
  writing: "models.phaseWriting",
  completed: "models.phaseCompleted",
  cancelled: "models.phaseCancelled",
  interrupted: "models.phaseInterrupted",
  failed: "models.phaseFailed",
};

export function formatBytes(value: number, locale: string): string {
  const safe = Number.isFinite(value) && value > 0 ? value : 0;
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(safe ? Math.floor(Math.log(safe) / Math.log(1024)) : 0, units.length - 1);
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: index > 1 ? 1 : 0 }).format(safe / 1024 ** index)} ${units[index]}`;
}

export function DownloadStatus({ job, cancel, cancelling }: { job: DownloadJob; cancel: () => void; cancelling: boolean }) {
  const { tr, locale, localize } = useI18n();
  const hasProgress = job.phase === "downloading" && job.total > 0;
  const completed = Math.min(Math.max(job.completed, 0), job.total);
  return (
    <div className="model-download-status" role="status" aria-live="polite">
      <div className="model-download-heading">
        <strong title={job.model}>{job.model}</strong>
        {isDownloadActive(job) && <button type="button" className="model-icon-button" onClick={cancel} disabled={cancelling} aria-label={tr("models.cancelDownload")}><X size={15} /></button>}
      </div>
      <span>{tr(phases[job.phase] ?? "models.phaseQueued")}</span>
      {hasProgress && <>
        <progress max={job.total} value={completed} aria-label={tr("models.layerProgress")} />
        <small>{tr("models.layerBytes", { completed: formatBytes(completed, locale), total: formatBytes(job.total, locale) })}</small>
      </>}
      {job.error && <p className="model-download-error">{localize(job.error)}</p>}
    </div>
  );
}
