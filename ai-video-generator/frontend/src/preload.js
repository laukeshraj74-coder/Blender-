/**
 * Electron Preload Script
 * Provides secure bridge between renderer and main process
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
    // Backend control
    startBackend: () => ipcRenderer.invoke('start-backend'),
    stopBackend: () => ipcRenderer.invoke('stop-backend'),
    checkBackend: () => ipcRenderer.invoke('check-backend'),
    
    // File dialog
    openFileDialog: (filters) => ipcRenderer.invoke('open-file-dialog', filters),
    
    // Backend status updates
    onBackendStatus: (callback) => {
        ipcRenderer.on('backend-status', (event, data) => callback(data));
    },
    
    // Platform info
    platform: process.platform
});
