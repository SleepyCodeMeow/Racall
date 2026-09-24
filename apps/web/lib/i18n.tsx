'use client';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from './api';
import { isLocale, localizeMessage, pluralize, setCurrentLocale, translate, type Locale, type MessageKey, type Parameters } from './translations';

type I18n = {
  locale: Locale;
  setLanguage: (locale: Locale) => Promise<void>;
  savingLanguage: boolean;
  tr: (key: MessageKey, params?: Parameters) => string;
  plural: (prefix: 'source.ready', count: number) => string;
  localize: (message: string) => string;
};
const Context = createContext<I18n | null>(null);
export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>('en');
  const [ready, setReady] = useState(false);
  const [savingLanguage, setSavingLanguage] = useState(false);
  const [error, setError] = useState<MessageKey | null>(null);
  const apply = useCallback((next: Locale) => {
    setCurrentLocale(next);
    document.documentElement.lang = next;
    setLocale(next);
  }, []);
  const load = useCallback(async () => {
    try {
      const hash = new URLSearchParams(window.location.hash.slice(1));
      if (hash.has('token')) { sessionStorage.setItem('on-token', hash.get('token')!); history.replaceState(null, '', location.pathname); }
      const prefs = await api<{ locale: Locale }>('/preferences');
      apply(isLocale(prefs.locale) ? prefs.locale : 'en');
      setError(null);
    } catch { setError('settings.languageLoadError'); }
    finally { setReady(true); }
  }, [apply]);
  useEffect(() => { void load(); }, [load]);
  const setLanguage = useCallback(async (next: Locale) => {
    if (!isLocale(next)) return;
    setSavingLanguage(true);
    try {
      await api('/preferences', 'PUT', { locale: next });
      apply(next);
      setError(null);
    } catch { setError('settings.languageError'); }
    finally { setSavingLanguage(false); }
  }, [apply]);
  const value = useMemo<I18n>(() => ({
    locale, setLanguage, savingLanguage,
    tr: (key, params) => translate(key, params, locale),
    plural: (prefix, count) => pluralize(prefix, count, locale),
    localize: message => localizeMessage(message, locale),
  }), [locale, setLanguage, savingLanguage]);
  if (!ready) return <div className="app-loading" role="status">{translate('common.loadingApp', {}, 'en')}</div>;
  return <Context.Provider value={value}>
    {error && <div className="language-error" role="alert"><span>{value.tr(error)}</span><button onClick={() => void load()}>{value.tr('common.retry')}</button><button aria-label={value.tr('common.dismissError')} onClick={() => setError(null)}>×</button></div>}
    {children}
  </Context.Provider>;
}
export function useI18n() {
  const value = useContext(Context);
  if (!value) throw new Error('useI18n requires I18nProvider');
  return value;
}
