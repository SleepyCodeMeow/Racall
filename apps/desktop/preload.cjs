const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('desktop', {
  connection: () => ipcRenderer.invoke('connection'),
  openVault: () => ipcRenderer.invoke('open-vault'),
});
