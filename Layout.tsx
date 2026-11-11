import { useEffect, useState, type ReactNode } from 'react';
import { Palette, Search, Tv } from 'lucide-react';
import { modules } from '../../core/registry';
import { useRoute } from '../../core/router';
import { isBool, isOneOf, useStoredState } from '../../core/storage';
import { CommandPalette } from './CommandPalette';

const ACCENTS = ['cyan', 'green', 'amber'] as const;
type Accent = (typeof ACCENTS)[number];

export function Layout({ children }: { children: (active: (typeof modules)[number]) => ReactNode }) {
  const route = useRoute();
  const active = modules.find((m) => m.path === route) ?? modules[0];

  const [crt, setCrt] = useStoredState('crt', true, isBool);
  const [accent, setAccent] = useStoredState<Accent>('accent', 'cyan', isOneOf(ACCENTS));
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => { document.documentElement.dataset.accent = accent; }, [accent]);

  // Ctrl/Cmd + K toggles the palette globally.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const cycleAccent = () => setAccent(ACCENTS[(ACCENTS.indexOf(accent) + 1) % ACCENTS.length]);
  const iconBtn = 'p-2 text-dim hover:text-accent focus-visible:outline focus-visible:outline-accent';

  return (
    <div className={`flex h-dvh flex-col md:flex-row ${crt ? 'crt' : ''}`}>
      {/* Nav: sidebar on desktop, bottom tab bar on mobile */}
      <nav aria-label="Modules" className="order-last flex border-t border-line bg-panel md:order-first md:w-56 md:flex-col md:border-r md:border-t-0">
        <div className="hidden px-4 py-4 text-sm text-accent md:block">
          CYBERSEC<span className="text-dim">//</span>TOOLKIT
        </div>
        {modules.map((m) => {
          const on = m.id === active.id;
          return (
            <a
              key={m.id} href={`#${m.path}`} aria-current={on ? 'page' : undefined}
              className={`flex flex-1 items-center justify-center gap-3 px-3 py-3 text-sm md:flex-none md:justify-start md:border-l-2 ${
                on ? 'border-accent bg-accent/10 text-accent' : 'border-transparent text-dim hover:text-ink'
              }`}
            >
              <m.icon size={18} aria-hidden />
              <span className="hidden md:inline">{m.title}</span>
              <span className="sr-only md:hidden">{m.title}</span>
            </a>
          );
        })}
      </nav>

      <div className="flex min-h-0 flex-1 flex-col">
        {/* Header: breadcrumb + controls */}
        <header className="flex items-center justify-between border-b border-line px-4 py-2 text-sm">
          <div className="truncate">
            <span className="text-accent">root@toolkit</span>
            <span className="text-dim">:~/</span>
            <span>{active.id}</span>
            <span className="animate-pulse text-accent">_</span>
          </div>
          <div className="flex items-center">
            <button onClick={() => setPaletteOpen(true)} className={`${iconBtn} flex items-center gap-2`} aria-label="Open command palette">
              <Search size={16} /> <kbd className="hidden border border-line px-1 text-xs sm:inline">Ctrl K</kbd>
            </button>
            <button onClick={cycleAccent} className={iconBtn} aria-label={`Accent: ${accent}. Click to change`}><Palette size={16} /></button>
            <button onClick={() => setCrt(!crt)} className={iconBtn} aria-pressed={crt} aria-label="Toggle CRT effect"><Tv size={16} /></button>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">{children(active)}</main>

        {/* Status bar */}
        <footer className="flex flex-wrap gap-x-4 border-t border-line bg-panel px-4 py-1 text-xs text-dim">
          <span><span className="text-accent">●</span> client-side only</span>
          <span>secure-ctx: {window.isSecureContext ? 'yes' : <span className="text-danger">no</span>}</span>
          <span>webcrypto: {globalThis.crypto?.subtle ? 'ok' : <span className="text-danger">unavailable</span>}</span>
          <span className="ml-auto">{active.path}</span>
        </footer>
      </div>

      {paletteOpen && <CommandPalette onClose={() => setPaletteOpen(false)} />}
    </div>
  );
}