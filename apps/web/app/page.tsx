'use client';
import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nProvider } from '../lib/i18n';
import { ThemeProvider } from '../lib/theme';
import { Workspace } from '../features/workspace/workspace';

export default function Page() {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <I18nProvider>
        <ThemeProvider>
          <Workspace />
        </ThemeProvider>
      </I18nProvider>
    </QueryClientProvider>
  );
}
