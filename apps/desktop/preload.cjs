const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('desktop', {
  connection: () => ipcRenderer.invoke('connection'),
  openVault: () => ipcRenderer.invoke('open-vault'),
  setTheme: (theme) => ipcRenderer.invoke('set-theme', theme),
  copyLaunchCommand: (integration) => ipcRenderer.invoke('copy-launch-command', integration),
});
