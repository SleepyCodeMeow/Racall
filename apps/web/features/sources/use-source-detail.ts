'use client';
import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, originalFile, type Source } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import type { SourceDetailProps, DocumentData, Version } from './source-detail-types';

export function useSourceDetail({
  notebook,
  source,
  evidence,
  refresh,
  report,
}: SourceDetailProps) {
  const { tr, locale, localize } = useI18n(),
    client = useQueryClient();
  const [picked, setPicked] = useState<string | undefined>(evidence?.version);
  const [busy, setBusy] = useState(false),
    [notice, setNotice] = useState('');
  const [fileUrl, setFileUrl] = useState('');
  const input = useRef<HTMLInputElement>(null),
    anchor = useRef<HTMLDivElement>(null);
  const version = picked || source.version;
  const prefix = `/notebooks/${notebook}/sources/${source.id}`;
  const processing = [source.status, source.refresh_status].some(
    (s) => s === 'queued' || s === 'processing',
  );
  const versions = useQuery({
    queryKey: ['source-versions', notebook, source.id, source.version, source.refresh_status],
    queryFn: () => api<Version[]>(prefix + '/versions'),
  });
  const document = useQuery({
    queryKey: [
      'source-document',
      notebook,
      source.id,
      version,
      source.status,
      source.refresh_status,
    ],
    queryFn: () => api<DocumentData>(prefix + (version ? `/versions/${version}` : '')),
  });
  const shown = document.data?.source || source;
  const archived = !!version && version !== source.version;
  useEffect(() => {
    setFileUrl('');
  }, [version]);
  useEffect(
    () => () => {
      if (fileUrl) URL.revokeObjectURL(fileUrl);
    },
    [fileUrl],
  );
  useEffect(() => {
    anchor.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [document.data, evidence]);
  const update = async (action: 'replace' | 'refresh' | 'retry', file?: File) => {
    setBusy(true);
    setNotice('');
    try {
      let result: Source & { unchanged?: boolean };
      if (action === 'replace' && file) {
        if (file.size > 25 * 1024 * 1024)
          throw new Error(tr('source.fileSize', { name: file.name }));
        const form = new FormData();
        form.append('file', file);
        result = await api(prefix, 'PUT', form);
      } else result = await api(prefix + (action === 'refresh' ? '/refresh' : '/reindex'), 'POST');
      if (result.unchanged) setNotice(tr('source.unchanged'));
      refresh();
      await client.invalidateQueries({
        queryKey: ['source-versions', notebook, source.id],
      });
    } catch (e) {
      report((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = '';
    }
  };
  const openOriginal = async () => {
    try {
      setFileUrl(await originalFile(notebook, shown, version));
    } catch (e) {
      report((e as Error).message);
    }
  };
  return {
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
    anchor,
    processing,
    versions,
    document,
    setPicked,
    update,
    openOriginal,
  };
}

export type SourceDetailController = ReturnType<typeof useSourceDetail>;
