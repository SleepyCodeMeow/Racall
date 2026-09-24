import type { Metadata } from 'next';
import './globals.css';
import './racall.css';
export const metadata: Metadata = { title: 'Racall', description: 'Your notes. Your sources. Connected.' };
export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
