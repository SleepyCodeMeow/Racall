export {};

declare global {
  interface Window {
    desktop?: {
      connection: () => Promise<{ origin: string }>;
      openVault: () => Promise<string>;
      setTheme?: (theme: 'light' | 'dark' | 'system') => Promise<void>;
      copyLaunchCommand?: (integration: string) => Promise<void>;
    };
  }
}
