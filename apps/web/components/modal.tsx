"use client";
import { useEffect, useRef, type ReactNode } from "react";
import { X } from "@phosphor-icons/react";
import { useI18n } from "../lib/i18n";

export function Modal({
  title,
  close,
  children,
  busy = false,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
  busy?: boolean;
}) {
  const { tr } = useI18n();
  const panel = useRef<HTMLElement>(null);
  const dismiss = useRef(close);
  dismiss.current = close;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const root = panel.current!;
    const targets = () =>
      Array.from(
        root.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex="0"]',
        ),
      );
    (
      root.querySelector<HTMLElement>("[data-initial-focus]") ||
      targets()[0] ||
      root
    ).focus();
    const trap = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) {
        e.preventDefault();
        dismiss.current();
      }
      if (e.key === "Tab") {
        const list = targets(),
          first = list[0],
          last = list[list.length - 1];
        if (!first) {
          e.preventDefault();
          return;
        }
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    root.addEventListener("keydown", trap);
    return () => {
      root.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [busy, title]);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (!busy && e.target === e.currentTarget) close();
      }}
    >
      <section
        className="modal management-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        ref={panel}
        tabIndex={-1}
      >
        <button
          className="modal-close icon-button"
          disabled={busy}
          aria-label={tr("common.close")}
          onClick={close}
        >
          <X size={19} />
        </button>
        <h2>{title}</h2>
        {children}
      </section>
    </div>
  );
}
