'use client';
import { useI18n } from '../lib/i18n';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function Markdown({ text, onWiki }: { text: string; onWiki?: (title: string) => void }) {
  const { tr } = useI18n();
  const markdown = text.replace(/\[\[([^\]\n]+)\]\]/g, (_, title: string) => `[${title}](#wiki-${encodeURIComponent(title)})`);
  return <div className="prose"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{
    a: ({ href, children }) => href?.startsWith('#wiki-')
      ? <button className="inline-link" onClick={() => onWiki?.(decodeURIComponent(href.slice(6)))}>{children}</button>
      : <a href={href} target="_blank" rel="noreferrer">{children}</a>,
    img: ({ alt }) => <span className="muted">{tr('markdown.image', { alt: alt || tr('markdown.external') })}</span>,
  }}>{markdown}</ReactMarkdown></div>;
}
