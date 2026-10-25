import { translate as tr } from '../translations';
import { origin } from './client';
import type { Source } from './types';

export async function originalFile(
  notebook: string,
  source: Source,
  version?: string,
): Promise<string> {
  const token = sessionStorage.getItem('on-token');
  const response = await fetch(
    (await origin()) +
      `/api/notebooks/${notebook}/sources/${source.id}${version ? `/versions/${version}` : ''}/original`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  ).catch(() => {
    throw new Error(tr('error.network'));
  });
  if (!response.ok) throw new Error(tr('error.original'));
  const data = await response.blob();
  return URL.createObjectURL(
    new Blob([data], {
      type: source.type === 'pdf' ? 'application/pdf' : data.type,
    }),
  );
}
