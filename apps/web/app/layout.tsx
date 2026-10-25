import type { Metadata } from 'next';
import './globals.css';
import './racall.css';
import './workbench.css';
import '../features/models/model-picker.css';
import '../features/studio/knowledge-workbench.css';
import './themes.css';
export const metadata: Metadata = { title: 'Racall', description: 'An open-source alternative to NotebookLM + Obsidian: AI research, cited answers, and connected Markdown notes.' };
export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
