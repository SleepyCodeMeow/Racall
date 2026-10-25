'use client';
import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties } from 'react';
import { createPortal } from 'react-dom';
import {
  ArrowClockwise,
  CaretDown,
  Check,
  DownloadSimple,
  GearSix,
  MagnifyingGlass,
  Plus,
  X,
} from '@phosphor-icons/react';
import type { ProviderId } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import { providerNames } from '../settings/providers';
import { DownloadStatus, formatBytes } from './download-status';
import { ModelTypeIcon } from './model-type-icon';
import { useModelDownload, useModels } from './use-models';

const providers: ProviderId[] = [
  'openai',
  'anthropic',
  'ollama',
  'ollama_cloud',
  'llama_cpp',
  'openai_compatible',
];

export function ModelPicker({
  configure,
  report,
  disabled = false,
}: {
  configure: () => void;
  report: (message: string) => void;
  disabled?: boolean;
}) {
  const { tr, locale } = useI18n();
  const [open, setOpen] = useState(false);
  const [providerOverride, setProvider] = useState<ProviderId>();
  const [search, setSearch] = useState('');
  const [manual, setManual] = useState('');
  const [confirmDownload, setConfirmDownload] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const popup = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const searchField = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const id = useId();
  const [position, setPosition] = useState<CSSProperties>({});
  const { settings, catalog, select, provider, selectedModelInfo } = useModels(
    open,
    providerOverride,
  );
  const download = useModelDownload(open, provider);
  const selectedProvider = settings.data?.provider;
  const selectedModel = selectedProvider ? settings.data?.profiles[selectedProvider].model : '';
  const selectedKind =
    selectedModelInfo?.kind ??
    (selectedProvider === 'ollama'
      ? /(?::cloud|-cloud)$/i.test(selectedModel ?? '')
        ? 'cloud'
        : undefined
      : selectedProvider === 'llama_cpp' || selectedProvider === 'openai_compatible'
        ? 'server'
        : 'cloud');
  const models =
    catalog.data?.models.filter((model) => model.id.toLowerCase().includes(search.toLowerCase())) ??
    [];
  const locked = disabled || select.isPending || !settings.data;
  const catalogError = settings.error ?? catalog.error;
  const close = (restoreFocus = true) => {
    setOpen(false);
    if (restoreFocus) trigger.current?.focus();
  };
  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      if (!trigger.current) return;
      const bounds = trigger.current.getBoundingClientRect();
      const gap = 12,
        edge = 16;
      const width = Math.min(350, window.innerWidth - edge * 2);
      const above = bounds.top - gap - edge;
      const below = window.innerHeight - bounds.bottom - gap - edge;
      const upwards = above >= 280 || above >= below;
      setPosition({
        left: Math.max(edge, Math.min(bounds.right - width, window.innerWidth - width - edge)),
        width,
        maxHeight: Math.max(0, upwards ? above : below),
        top: upwards ? undefined : bounds.bottom + gap,
        bottom: upwards ? window.innerHeight - bounds.top + gap : undefined,
      });
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
    };
  }, [open]);
  useEffect(() => {
    if (!open) return;
    searchField.current?.focus();
    const outside = (event: PointerEvent) => {
      if (
        !root.current?.contains(event.target as Node) &&
        !popup.current?.contains(event.target as Node)
      )
        setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setOpen(false);
        trigger.current?.focus();
      }
    };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', escape);
    };
  }, [open]);
  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);
  const choose = async (model: string) => {
    if (!model.trim() || locked) return;
    try {
      await select.mutateAsync(model);
      close();
    } catch (error) {
      report((error as Error).message);
    }
  };
  const cloudName = /(?::cloud|-cloud)$/i.test(manual.trim());
  return (
    <div className="model-picker" ref={root}>
      <button
        ref={trigger}
        type="button"
        className="model-picker-trigger"
        id={`${id}-trigger`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? `${id}-popup` : undefined}
        disabled={disabled || settings.isPending}
        onClick={() => {
          setProvider(undefined);
          setSearch('');
          setManual('');
          setConfirmDownload(false);
          setOpen(!open);
        }}
      >
        {selectedKind && <ModelTypeIcon kind={selectedKind} size={14} />}
        <span>{selectedModel || tr('models.choose')}</span>
        <CaretDown size={12} />
      </button>
      {open &&
        createPortal(
          <section
            ref={popup}
            style={position}
            className="model-picker-popup"
            role="dialog"
            id={`${id}-popup`}
            aria-labelledby={`${id}-heading`}
          >
            <div className="model-picker-topline">
              <h3 id={`${id}-heading`}>{tr('models.title')}</h3>
              <button
                type="button"
                className="model-icon-button"
                aria-label={tr('models.close')}
                onClick={() => close()}
              >
                <X size={16} />
              </button>
            </div>
            <label className="model-provider-label" htmlFor={`${id}-provider`}>
              {tr('models.provider')}
            </label>
            <select
              id={`${id}-provider`}
              className="model-provider-select"
              value={provider}
              disabled={locked}
              onChange={(event) => {
                setProvider(event.target.value as ProviderId);
                setSearch('');
                setManual('');
                setConfirmDownload(false);
              }}
            >
              {providers.map((value) => (
                <option key={value} value={value}>
                  {providerNames[value]}
                </option>
              ))}
            </select>
            <div className="model-search-row">
              <MagnifyingGlass size={16} aria-hidden="true" />
              <input
                ref={searchField}
                aria-label={tr('models.search')}
                placeholder={tr('models.search')}
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    event.stopPropagation();
                  }
                  if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    list.current
                      ?.querySelector<HTMLButtonElement>('button:not(:disabled)')
                      ?.focus();
                  }
                }}
              />
              <button
                type="button"
                className={`model-icon-button${catalog.isFetching ? ' model-refreshing' : ''}`}
                title={tr('models.refresh')}
                aria-label={tr('models.refresh')}
                disabled={catalog.isFetching || locked}
                onClick={() => void catalog.refetch()}
              >
                <ArrowClockwise size={16} />
              </button>
            </div>
            <div
              className="model-picker-list"
              ref={list}
              aria-label={tr('models.available')}
              aria-busy={catalog.isFetching}
              onKeyDown={(event) => {
                if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
                const buttons = Array.from(
                  list.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? [],
                );
                if (!buttons.length) return;
                const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
                event.preventDefault();
                buttons[
                  (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length
                ].focus();
              }}
            >
              {catalogError ? (
                <div className="model-picker-empty" role="alert">
                  <p>{catalogError.message}</p>
                  <button type="button" className="text-button" onClick={configure}>
                    {tr('models.configure')}
                  </button>
                </div>
              ) : catalog.isPending ? (
                <p className="model-picker-empty" role="status">
                  {tr('models.loading')}
                </p>
              ) : models.length ? (
                models.map((model) => {
                  const active = provider === selectedProvider && model.id === selectedModel;
                  return (
                    <button
                      type="button"
                      className={`model-option${active ? ' selected' : ''}`}
                      key={model.id}
                      disabled={locked || (model.kind === 'local' && !model.installed)}
                      onClick={() => void choose(model.id)}
                      aria-pressed={active}
                    >
                      <span className="model-option-name">
                        {model.id}
                        <small>
                          {tr(
                            model.kind === 'cloud'
                              ? 'models.cloud'
                              : model.kind === 'local'
                                ? 'models.local'
                                : 'models.server',
                          )}
                          {model.size_bytes ? ` · ${formatBytes(model.size_bytes, locale)}` : ''}
                        </small>
                      </span>
                      {active ? (
                        <Check size={16} />
                      ) : model.kind === 'local' && !model.installed ? (
                        <DownloadSimple size={16} />
                      ) : (
                        <ModelTypeIcon kind={model.kind} />
                      )}
                    </button>
                  );
                })
              ) : (
                <p className="model-picker-empty">
                  {tr(search ? 'models.noMatches' : 'models.empty')}
                </p>
              )}
            </div>
            {download.job && provider === 'ollama' && (
              <DownloadStatus
                job={download.job}
                cancelling={download.cancel.isPending}
                cancel={() => {
                  void download.cancel.mutateAsync().catch((error: Error) => report(error.message));
                }}
              />
            )}
            {download.error && provider === 'ollama' && (
              <p className="model-download-error" role="alert">
                {download.error.message}
              </p>
            )}
            <details
              className="model-manual"
              onToggle={(event) => {
                if (!event.currentTarget.open) setConfirmDownload(false);
              }}
            >
              <summary>
                <Plus size={14} />
                {tr('models.manual')}
              </summary>
              <div className="model-manual-entry">
                <label htmlFor={`${id}-manual`}>{tr('models.modelId')}</label>
                <div className="model-manual-row">
                  <input
                    id={`${id}-manual`}
                    value={manual}
                    maxLength={200}
                    placeholder={tr('models.modelIdPlaceholder')}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault();
                        event.stopPropagation();
                        void choose(manual);
                      }
                    }}
                    onChange={(event) => {
                      setManual(event.target.value);
                      setConfirmDownload(false);
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => void choose(manual)}
                    disabled={!manual.trim() || locked}
                  >
                    {select.isPending ? tr('models.saving') : tr('models.use')}
                  </button>
                </div>
              </div>
              {provider === 'ollama' && catalog.data?.can_download && (
                <>
                  {!confirmDownload ? (
                    <button
                      type="button"
                      className="model-download-button"
                      disabled={
                        !manual.trim() ||
                        cloudName ||
                        download.active ||
                        download.start.isPending ||
                        locked
                      }
                      onClick={() => setConfirmDownload(true)}
                    >
                      <DownloadSimple size={15} />
                      {tr('models.download')}
                    </button>
                  ) : (
                    <div className="model-download-confirm">
                      <p>{tr('models.downloadConfirm', { model: manual.trim() })}</p>
                      <small>{tr('models.downloadHint')}</small>
                      <div>
                        <button
                          type="button"
                          className="model-download-button"
                          disabled={download.start.isPending || locked}
                          onClick={() => {
                            void download.start
                              .mutateAsync(manual)
                              .then(() => setConfirmDownload(false))
                              .catch((error: Error) => report(error.message));
                          }}
                        >
                          {download.start.isPending
                            ? tr('models.starting')
                            : tr('models.confirmDownload')}
                        </button>
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => setConfirmDownload(false)}
                        >
                          {tr('models.back')}
                        </button>
                      </div>
                    </div>
                  )}
                  <a
                    className="model-library-link"
                    href="https://ollama.com/library"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {tr('models.library')}
                  </a>
                </>
              )}
            </details>
            <button
              type="button"
              className="model-picker-settings"
              onClick={() => {
                close(false);
                configure();
              }}
            >
              <GearSix size={15} />
              {tr('models.configure')}
            </button>
          </section>,
          document.body,
        )}
    </div>
  );
}
