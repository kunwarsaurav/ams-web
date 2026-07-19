const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let backendProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        title: "Attendance Management System",
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    // Completely remove the default menu bar (File, Edit, View, etc.)
    mainWindow.setMenu(null);

    // In production, load the built React app. In dev, load localhost.
    if (app.isPackaged) {
        mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));
    } else {
        mainWindow.loadURL('http://localhost:5173');
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startBackend() {
    const backendPath = app.isPackaged
        ? path.join(process.resourcesPath, 'synthbit-backend.exe')
        : path.join(__dirname, '../backend/dist/synthbit-backend.exe');

    // Spawn the backend executable using uvicorn programmatic execution or direct execution
    backendProcess = spawn(backendPath, [], { detached: false });

    backendProcess.stderr.on('data', (data) => {
        console.error(`Backend Error: ${data}`);
    });
}

app.on('ready', () => {
    startBackend();

    // Wait for backend to be ready on port 8080 before showing UI
    const checkBackend = setInterval(() => {
        http.get('http://127.0.0.1:8080/device/settings', (res) => {
            if (res.statusCode === 200) {
                clearInterval(checkBackend);
                createWindow();
            }
        }).on('error', () => {
            // Backend not ready yet...
        });
    }, 500);
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Kill the backend when Electron exits
app.on('will-quit', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
});
