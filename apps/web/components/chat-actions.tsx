'use client';
import { useI18n } from '../lib/i18n';
import { useEffect, useRef, useState } from 'react';
import { FileText, Flask, GearSix, PlugsConnected, Plus, UploadSimple } from '@phosphor-icons/react';

export function ChatActions({ openSources, navigate, settings }: { openSources: () => void; navigate: (id: string) => void; settings: () => void }) {
  const { tr } = useI18n();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); trigger.current?.focus(); } };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, [open]);
  const choose = (action: () => void) => { setOpen(false); action(); };
  return <div ref={root} className="composer-actions">
    <button ref={trigger} type="button" className={`add-action ${open ? 'active' : ''}`} aria-label={tr("chat.actions")} aria-expanded={open} onClick={() => setOpen(!open)}><Plus size={19} /></button>
    {open && <div className="actions-popover" aria-label={tr("chat.actions")}>
      <button type="button" onClick={() => choose(openSources)}><UploadSimple size={17} />{tr("source.addMaterials")}</button>
      <button type="button" onClick={() => choose(() => navigate('notes'))}><FileText size={17} />{tr("nav.notes")}</button>
      <button type="button" onClick={() => choose(() => navigate('research'))}><Flask size={17} />{tr("research.single")}</button>
      <div className="actions-divider" />
      <button type="button" onClick={() => choose(() => navigate('connect'))}><PlugsConnected size={17} />{tr("nav.connect")}</button>
      <button type="button" onClick={() => choose(settings)}><GearSix size={17} />{tr("settings.configureModel")}</button>
    </div>}
  </div>;
}
