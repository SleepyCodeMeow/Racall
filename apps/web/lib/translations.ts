import en from '../../shared/locales/en.json';
import ru from '../../shared/locales/ru.json';

export type Locale = 'en' | 'ru';
export type MessageKey = keyof typeof en;
export type Parameters = Record<string, string | number>;
export const languages: { id: Locale; label: string }[] = [{ id: 'en', label: 'English' }, { id: 'ru', label: 'Русский' }];
const catalogs: Record<Locale, Record<MessageKey, string>> = { en, ru };
let currentLocale: Locale = 'en';
export const isLocale = (value: unknown): value is Locale => value === 'en' || value === 'ru';
export function setCurrentLocale(locale: Locale) { currentLocale = locale; }
export function translate(key: MessageKey, params: Parameters = {}, locale: Locale = currentLocale): string {
  return (catalogs[locale][key] || en[key]).replace(/\{(\w+)\}/g, (match, name: string) => String(params[name] ?? match));
}
export function pluralize(prefix: 'source.ready', count: number, locale: Locale = currentLocale) {
  const category = new Intl.PluralRules(locale).select(count);
  const key = `${prefix}.${category}` as MessageKey;
  return translate(key in en ? key : `${prefix}.other`, { count }, locale);
}

// Adapter for existing service messages. Never call on source text, notes or AI claims.
// Catalog keys remain stable; adding a locale does not change stored documents.
export function localizeMessage(message: string, locale: Locale = currentLocale): string {
  for (const catalog of [en, ru]) {
    for (const [rawKey, template] of Object.entries(catalog)) {
      const key = rawKey as MessageKey;
      if (message === template) return translate(key, {}, locale);
      if (!template.includes('{')) continue;
      const names: string[] = [];
      const pattern = template.split(/(\{\w+\})/).map(part => {
        if (/^\{\w+\}$/.test(part)) { names.push(part.slice(1, -1)); return '([\\s\\S]+?)'; }
        return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      }).join('');
      const match = message.match(new RegExp(`^${pattern}$`));
      if (match) return translate(key, Object.fromEntries(names.map((name, i) => [name, match[i + 1]])), locale);
    }
  }
  return message;
}
