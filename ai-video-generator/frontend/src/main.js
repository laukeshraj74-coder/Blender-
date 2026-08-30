/**
 * Electron Main Process for AI Video Generator
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess = null;

// Backend configuration
const BACKEND_PORT = 5000;
const BACKEND_HOST = '127.0.0.1';

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1024,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        backgroundColor: '#1a1a2e',
        show: false,
        titleBarStyle: 'hiddenInset'
    });

    // Load the index.html
    mainWindow.loadFile(path.join(__dirname, '../index.html'));

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Open DevTools in development
    if (process.env.NODE_ENV === 'development') {
        mainWindow.webContents.openDevTools();
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startBackend() {
    const backendPath = path.join(__dirname, '../../backend/main.py');
    
    backendProcess = spawn('python', [backendPath], {
        cwd: path.join(__dirname, '../..'),
        env: { ...process.env, PYTHONPATH: path.join(__dirname, '../..') }
    });

    backendProcess.stdout.on('data', (data) => {
        console.log(`[Backend] ${data.toString().trim()}`);
    });

    backendProcess.stderr.on('data', (data) => {
        console.error(`[Backend Error] ${data.toString().trim()}`);
    });

    backendProcess.on('close', (code) => {
        console.log(`[Backend] Process exited with code ${code}`);
        if (mainWindow) {
            mainWindow.webContents.send('backend-status', { 
                status: 'disconnected',
                message: 'Backend stopped'
            });
        }
    });

    return backendProcess;
}

function stopBackend() {
    if (backendProcess) {
        backendProcess.kill();
        backendProcess = null;
    }
}

// IPC Handlers
ipcMain.handle('start-backend', async () => {
    try {
        startBackend();
        // Wait a bit for backend to start
        await new Promise(resolve => setTimeout(resolve, 2000));
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('stop-backend', async () => {
    stopBackend();
    return { success: true };
});

ipcMain.handle('check-backend', async () => {
    return { running: backendProcess !== null };
});

ipcMain.handle('open-file-dialog', async (event, filters) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile', 'multiSelections'],
        filters: filters || [
            { name: 'Media Files', extensions: ['mp4', 'mov', 'webm', 'avi', 'mp3', 'wav', 'm4a', 'png', 'jpg', 'jpeg', 'webp'] },
            { name: 'Video', extensions: ['mp4', 'mov', 'webm', 'avi'] },
            { name: 'Audio', extensions: ['mp3', 'wav', 'm4a'] },
            { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] },
            { name: 'All Files', extensions: ['*'] }
        ]
    });
    
    return result;
});

// App lifecycle
app.whenReady().then(() => {
    createWindow();
    
    // Start backend automatically
    startBackend();
});

app.on('window-all-closed', () => {
    stopBackend();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

app.on('will-quit', () => {
    stopBackend();
});
