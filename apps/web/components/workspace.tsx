'use client';
import { useI18n } from '../lib/i18n';
import { useEffect, useRef, useState } from 'react';
import { ArrowUp, ArrowUpRight, Check, Copy, FileText, MagnifyingGlass, Plus, Sparkle } from '@phosphor-icons/react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Answer, api, Evidence, locationLabel, Note, Research } from '../lib/api';
import { Markdown } from './markdown';
import { ChatActions } from './chat-actions';

export function AnswerView({ answer, cite }: { answer: Answer; cite: (e: Evidence) => void }) {
  const { tr, localize } = useI18n();
  return <div className="answer-body">
    {answer.claims.map((claim, i) => <p key={i}>{claim.text} <span className="citation-buttons">{claim.evidence_ids.map(id => {
      const e = answer.citations.find(c => c.id === id);
      return e ? <button key={id} title={`${e.title} · ${locationLabel(e)}`} onClick={() => cite(e)}>{e.number}</button> : null;
    })}</span></p>)}
    {answer.message && <p className="muted">{localize(answer.message)}</p>}
    {answer.citations.length > 0 && <div className="evidence-list"><div className="eyebrow">{tr("answer.sources")}</div>{answer.citations.map(e => <button key={e.id} onClick={() => cite(e)}><span className="evidence-number">{e.number}</span><span><strong>{e.title}</strong><small>{locationLabel(e)}</small></span><ArrowUpRight size={16} /></button>)}</div>}
    {answer.validated && <div className="verification"><Check size={14} /> {tr("answer.verified")}</div>}
  </div>;
}

export function Chat({ notebook, count, cite, report, settings, openSources, navigate }: { notebook: string; count: number; cite: (e: Evidence) => void; report: (s: string) => void; settings: () => void; openSources: () => void; navigate: (id: string) => void }) {
  const { tr, localize } = useI18n();
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<'ask' | 'search'>('ask');
  const [turns, setTurns] = useState<{ question: string; answer?: Answer; evidence?: Evidence[] }[]>([]);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [turns, busy]);
  return <div className={`chat-layout ${!turns.length && !busy ? 'is-empty' : ''}`}><div className="chat-scroll">
    {!turns.length && !busy && <div className="chat-welcome"><div className="welcome-heading"><img src="/brand/raccoon.png" width="46" height="46" alt="" /><h2>{tr("chat.title")}</h2></div><p>{count ? tr("chat.description") : tr("chat.start")}</p></div>}
    {turns.map((turn, index) => <article className="turn" key={index}><div className="question-label">{tr("chat.you")}</div><h3>{turn.question}</h3><div className="assistant-label"><img className="answer-mascot" src="/brand/raccoon.png" width="26" height="26" alt="" /> Racall</div>{turn.answer && <AnswerView answer={turn.answer} cite={cite} />}{turn.evidence && <div className="search-results">{turn.evidence.length === 0 ? <p>{tr("chat.noMatches")}</p> : turn.evidence.map(e => <button key={e.id} onClick={() => cite(e)}><strong>{e.title}</strong><small>{locationLabel(e)}</small><p>{e.quote.slice(0, 550)}{e.quote.length > 550 ? '…' : ''}</p></button>)}</div>}</article>)}
    {busy && <div className="answer-loading" aria-live="polite"><span>{mode === 'ask' ? tr("chat.thinking") : tr("chat.searching")}</span><div className="skeleton" /><div className="skeleton w-4/5" /><div className="skeleton w-3/5" /></div>}<div ref={end} />
  </div><div className="composer-wrap"><form className="composer" onSubmit={async e => {
    e.preventDefault(); if (!question.trim() || busy) return;
    const q = question.trim(); setBusy(true);
    try {
      if (mode === 'ask') { const answer = await api<Answer>(`/notebooks/${notebook}/ask`, 'POST', { question: q }); setTurns(t => [...t, { question: q, answer }]); }
      else { const result = await api<{ evidence: Evidence[] }>(`/notebooks/${notebook}/search`, 'POST', { question: q }); setTurns(t => [...t, { question: q, evidence: result.evidence }]); }
      setQuestion('');
    } catch (error) { report((error as Error).message); } finally { setBusy(false); }
  }}><textarea aria-label={tr("chat.questionLabel")} placeholder={count ? tr("chat.placeholder") : tr("chat.noSourcePlaceholder")} value={question} onChange={e => setQuestion(e.target.value)} disabled={!count} rows={2} maxLength={2000} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} />
    <div className="composer-bottom"><div className="composer-tools"><ChatActions openSources={openSources} navigate={navigate} settings={settings} /><div className="mode-switch"><button type="button" className={mode === 'ask' ? 'active' : ''} onClick={() => setMode('ask')}><Sparkle size={14} />{tr("chat.aiAnswer")}</button><button type="button" className={mode === 'search' ? 'active' : ''} onClick={() => setMode('search')}><MagnifyingGlass size={14} />{tr("common.search")}</button></div></div><button className="send-button" aria-label={tr("chat.send")} disabled={busy || !count || !question.trim()}><ArrowUp size={20} /></button></div>
  </form>{!turns.length && !busy && <div className="chat-shortcuts">{count ? <><button onClick={() => setQuestion(tr("chat.suggestion"))}><Sparkle size={14} />{tr("chat.ideas")}</button><button onClick={() => navigate('research')}><MagnifyingGlass size={14} />{tr("chat.research")}</button><button onClick={() => navigate('notes')}><FileText size={14} />{tr("chat.notes")}</button></> : <button onClick={openSources}><Plus size={15} />{tr("source.addMaterials")}</button>}</div>}<p className="composer-caption">{tr("chat.sourcesOnly")} <span>·</span> {tr("chat.checkCitations")}</p></div></div>;
}

export function Notes({ notebook, kind, report }: { notebook: string; kind: 'notes' | 'artifacts'; report: (s: string) => void }) {
  const { tr, localize } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: [kind, notebook], queryFn: () => api<Note[]>(`/notebooks/${notebook}/${kind}`) });
  const [current, setCurrent] = useState<Note | null>(null);
  const [preview, setPreview] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (kind !== 'notes') return;
    try {
      const raw = localStorage.getItem('draft:' + notebook);
      if (raw) {
        const draft = JSON.parse(raw) as Note;
        if (typeof draft.title === 'string' && typeof draft.body === 'string' && typeof draft.id === 'string') { setCurrent(draft); setDirty(true); }
      }
    } catch { /* An unavailable local cache must not prevent file-backed notes. */ }
  }, [notebook, kind]);
  const updateDraft = (note: Note) => {
    setCurrent(note); setDirty(true);
    try { localStorage.setItem('draft:' + notebook, JSON.stringify(note)); }
    catch { report(tr("error.draft")); }
  };
  const choose = (note: Note) => { if (dirty && !window.confirm(tr("notes.unsaved"))) return; setCurrent(note); setDirty(false); setSaved(false); };
  useEffect(() => { if (query.error) report(query.error.message); }, [query.error, report]);
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => { if (dirty) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', handler); return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);
  return <div className="notes-layout"><div className="note-picker"><div className="flex justify-between items-center mb-5"><h2>{kind === 'notes' ? tr("notes.title") : tr("nav.artifacts")}</h2>{kind === 'notes' && <button className="secondary" onClick={() => choose({ id: '', title: tr("notes.new"), body: '' })}><Plus size={16} />{tr("common.create")}</button>}</div>
    {query.isPending && <div className="skeleton h-20" />}{query.data?.length === 0 && <p className="muted">{kind === 'notes' ? tr("notes.empty") : tr("reports.empty")}</p>}
    <div className="note-tabs">{query.data?.map(note => <button key={note.id} className={current?.id === note.id ? 'selected' : ''} onClick={() => choose(note)}><FileText size={17} />{note.title}</button>)}</div>
  </div>{current ? <div className="note-editor"><div className="editor-toolbar">{kind === 'notes' ? <><button className="text-button" onClick={() => setPreview(!preview)}>{preview ? tr("common.edit") : tr("common.preview")}</button><button className="primary" disabled={busy || !current.title.trim()} onClick={async () => { setBusy(true); try { const note = await api<Note>(`/notebooks/${notebook}/notes`, 'POST', { ...current, id: current.id || undefined }); setCurrent(note); setDirty(false); setSaved(true); localStorage.removeItem('draft:' + notebook); client.invalidateQueries({ queryKey: [kind, notebook] }); } catch (e) { report((e as Error).message); } finally { setBusy(false); } }}>{busy ? tr("common.saving") : saved && !dirty ? tr("common.saved") : tr("common.save")}</button></> : <span className="eyebrow">{tr("research.report")}</span>}</div>
    {preview || kind === 'artifacts' ? <Markdown text={`# ${current.title}\n\n${current.body}`} onWiki={title => { const note = query.data?.find(n => n.title === title); if (note) choose(note); else report(tr('notes.notFound', { title })); }} /> : <><input className="note-title" aria-label={tr("notes.titleLabel")} value={current.title} onChange={e => { updateDraft({ ...current, title: e.target.value }); }} /><textarea className="markdown-editor" aria-label={tr("notes.bodyLabel")} value={current.body} placeholder={tr("notes.placeholder")} onChange={e => { updateDraft({ ...current, body: e.target.value }); }} /></>}
  </div> : <div className="editor-empty"><FileText size={40} weight="light" /><p>{kind === 'notes' ? tr('notes.emptySelection') : tr('reports.emptySelection')}</p></div>}</div>;
}

export function ResearchPanel({ notebook, cite, report }: { notebook: string; cite: (e: Evidence) => void; report: (s: string) => void }) {
  const { tr, localize } = useI18n();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ['research', notebook], queryFn: () => api<Research[]>(`/notebooks/${notebook}/research`) });
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState<Research>();
  const [saved, setSaved] = useState(false);
  useEffect(() => { if (query.error) report(query.error.message); }, [query.error, report]);
  return <div className="page-content research"><div className="eyebrow">{tr("research.eyebrow")}</div><h2>{tr("research.title1")}<br />{tr("research.title2")}</h2><p className="muted">{tr("research.description")}</p>
    <form className="research-form" onSubmit={async e => { e.preventDefault(); setBusy(true); setSaved(false); try { const result = await api<Research>(`/notebooks/${notebook}/research`, 'POST', { question }); setSession(result); client.invalidateQueries({ queryKey: ['research', notebook] }); } catch (e) { report((e as Error).message); } finally { setBusy(false); } }}><label>{tr("research.topic")}<textarea rows={3} placeholder={tr("research.placeholder")} required maxLength={2000} value={question} onChange={e => setQuestion(e.target.value)} /></label><button className="primary" disabled={busy}><Sparkle size={17} />{busy ? tr("research.busy") : tr("research.start")}</button></form>
    {busy && <div className="research-progress"><span className="pulse-dot" />{tr("research.progress")}</div>}
    {session && <div className="research-result"><h3>{session.question}</h3><div className="step-log">{session.steps.map((step, i) => <span key={i}>{({ planner: tr("research.plan"), retrieval: tr("common.search"), critic: tr("research.review"), revision: tr("research.revision") } as Record<string, string>)[step.stage]}{step.count !== undefined ? `: ${step.count}` : ''}</span>)}</div>{session.answer ? <AnswerView answer={session.answer} cite={cite} /> : <p>{tr(session.status === 'failed' ? 'research.failed' : 'research.pending')}</p>}{session.answer?.validated && <button className="secondary mt-5" disabled={saved} onClick={async () => { try { await api(`/notebooks/${notebook}/research/${session.id}/save`, 'POST'); setSaved(true); client.invalidateQueries({ queryKey: ['artifacts', notebook] }); } catch (e) { report((e as Error).message); } }}>{saved ? tr("research.saved") : tr("research.save")}</button>}</div>}
    <div className="section-heading mt-8"><h3>{tr("research.previous")}</h3></div>{query.data?.map(s => <button className="research-history" key={s.id} onClick={() => { setSession(s); setSaved(false); }}><span>{s.question}</span><small>{s.status === 'completed' ? tr("common.completed") : s.status === 'failed' ? tr("common.error") : tr("research.interrupted")}</small><ArrowUpRight size={16} /></button>)}
  </div>;
}

export function Connect({ notebook, report }: { notebook: string; report: (s: string) => void }) {
  const { tr, localize } = useI18n();
  const [config, setConfig] = useState(''); const [copied, setCopied] = useState(false);
  useEffect(() => { api<{ mcpServers: object }>(`/notebooks/${notebook}/connection`).then(c => setConfig(JSON.stringify({ mcpServers: c.mcpServers }, null, 2))).catch(e => report(e.message)); }, [notebook, report]);
  return <div className="page-content connect"><div className="eyebrow">{tr("connect.eyebrow")}</div><h2>{tr("connect.title1")}<br />{tr("connect.title2")}</h2><p className="muted">{tr("connect.description")}</p><div className="permission-row"><Check size={18} />{tr("connect.search")}</div><div className="permission-row"><Check size={18} />{tr("connect.read")}</div><div className="permission-row muted">{tr("connect.readOnly")}</div>
    <h3 className="mt-8 mb-3">{tr("connect.config")}</h3><p className="muted mb-4">{tr("connect.instructions")}</p><pre className="config-block">{config || tr("connect.loading")}</pre><button className="secondary mt-4" onClick={() => navigator.clipboard.writeText(config).then(() => setCopied(true)).catch(() => report(tr("error.clipboard")))}><Copy size={17} />{copied ? tr("common.copied") : tr("common.copy")}</button>
    <div className="notice mt-8">{tr("connect.remoteNotice")}</div>
  </div>;
}
