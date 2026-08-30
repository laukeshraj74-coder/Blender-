/**
 * Electron Main Process for AI Video Generator
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let backendProcess = null;
let backendReady = false;

// Backend configuration
const BACKEND_PORT = 5000;
const BACKEND_HOST = '127.0.0.1';

// Get the app's resource path (works in both dev and packaged)
function getResourcePath() {
    if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
        return path.join(__dirname, '../..');
    }
    // In production, resources are in the asar archive
    return process.resourcesPath || path.join(path.dirname(process.execPath), 'resources');
}

function getPythonExecutable() {
    // In production, we bundle Python or use system Python
    if (process.platform === 'win32') {
        // Try bundled python.exe first (if using pyinstaller or similar)
        const bundledPython = path.join(path.dirname(process.execPath), 'python.exe');
        if (fs.existsSync(bundledPython)) {
            return bundledPython;
        }
        // Try system python
        return 'python';
    }
    return 'python3';
}

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

    // Load the index.html - handle both packaged and dev paths
    const indexPath = path.join(getResourcePath(), 'frontend', 'index.html');
    mainWindow.loadFile(indexPath);

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
    const resourcePath = getResourcePath();
    const backendPath = path.join(resourcePath, 'backend', 'main.py');
    const pythonExe = getPythonExecutable();
    
    console.log(`[Main] Starting backend from: ${backendPath}`);
    console.log(`[Main] Using Python: ${pythonExe}`);
    
    // Set up environment for packaged app
    const env = { 
        ...process.env, 
        PYTHONPATH: resourcePath,
        APP_RESOURCE_PATH: resourcePath
    };
    
    backendProcess = spawn(pythonExe, [backendPath], {
        cwd: resourcePath,
        env: env,
        detached: false
    });

    backendProcess.stdout.on('data', (data) => {
        console.log(`[Backend] ${data.toString().trim()}`);
    });

    backendProcess.stderr.on('data', (data) => {
        console.error(`[Backend Error] ${data.toString().trim()}`);
    });

    backendProcess.on('close', (code) => {
        console.log(`[Backend] Process exited with code ${code}`);
        backendReady = false;
        if (mainWindow) {
            mainWindow.webContents.send('backend-status', { 
                status: 'disconnected',
                message: `Backend stopped (exit code: ${code})`
            });
        }
    });

    backendProcess.on('error', (err) => {
        console.error(`[Backend] Failed to start: ${err.message}`);
        backendReady = false;
        if (mainWindow) {
            mainWindow.webContents.send('backend-status', { 
                status: 'error',
                message: `Failed to start backend: ${err.message}`
            });
        }
    });

    return backendProcess;
}

function stopBackend() {
    if (backendProcess) {
        try {
            // Send SIGTERM first for graceful shutdown
            backendProcess.kill('SIGTERM');
            
            // Force kill after a short delay if still running
            setTimeout(() => {
                if (backendProcess && !backendProcess.killed) {
                    backendProcess.kill('SIGKILL');
                }
            }, 3000);
        } catch (e) {
            console.error('[Main] Error stopping backend:', e);
        }
        backendProcess = null;
    }
    backendReady = false;
}

// Health check with retry
async function waitForBackend(maxAttempts = 30, interval = 1000) {
    const http = require('http');
    
    for (let i = 0; i < maxAttempts; i++) {
        await new Promise(resolve => setTimeout(resolve, interval));
        
        try {
            const result = await new Promise((resolve, reject) => {
                const req = http.get(`http://${BACKEND_HOST}:${BACKEND_PORT}/api/health`, (res) => {
                    if (res.statusCode === 200) {
                        resolve(true);
                    } else {
                        reject(new Error(`HTTP ${res.statusCode}`));
                    }
                });
                req.on('error', reject);
                req.setTimeout(2000);
            });
            
            if (result) {
                backendReady = true;
                return true;
            }
        } catch (e) {
            // Continue retrying
        }
    }
    
    return false;
}

// IPC Handlers
ipcMain.handle('start-backend', async () => {
    try {
        startBackend();
        // Wait for backend to be ready
        const ready = await waitForBackend();
        if (ready) {
            if (mainWindow) {
                mainWindow.webContents.send('backend-status', { 
                    status: 'ready',
                    message: 'Backend connected'
                });
            }
            return { success: true };
        } else {
            return { success: false, error: 'Backend failed to start' };
        }
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('stop-backend', async () => {
    stopBackend();
    return { success: true };
});

ipcMain.handle('check-backend', async () => {
    return { 
        running: backendProcess !== null,
        ready: backendReady
    };
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
app.whenReady().then(async () => {
    createWindow();
    
    // Start backend automatically
    startBackend();
    
    // Wait for backend and notify renderer
    const ready = await waitForBackend();
    if (mainWindow) {
        mainWindow.webContents.send('backend-status', { 
            status: ready ? 'ready' : 'error',
            message: ready ? 'Backend connected' : 'Backend failed to start'
        });
    }
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

app.on('will-quit', (event) => {
    // Stop backend before quitting
    stopBackend();
});

app.on('before-quit', () => {
    stopBackend();
});
