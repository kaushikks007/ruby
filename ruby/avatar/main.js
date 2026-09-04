/* Ruby Phase 6 — Electron shell: always-on-top, frameless, transparent overlay
   that hosts ruby/avatar.html (the Three.js spider). State is driven from the
   Python side; the renderer polls http://127.0.0.1:47652/state, so no IPC plumbing
   is needed here.
*/
const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 340,
    height: 340,
    transparent: true,
    frame: false,
    resizable: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    backgroundColor: '#00000000',
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });

  win.loadFile(path.join(__dirname, 'avatar.html'));

  // Stay above normal windows, even fullscreen (screen-saver level).
  win.setAlwaysOnTop(true, 'screen-saver');
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  return win;
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  app.quit();
});
