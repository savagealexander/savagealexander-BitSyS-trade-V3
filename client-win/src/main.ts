import { app, BrowserWindow } from 'electron';
import { join } from 'path';
import { URL } from 'url';

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 600
  });

  const url = process.env.VITE_DEV_SERVER_URL
    ? process.env.VITE_DEV_SERVER_URL
    : new URL('renderer/index.html', `file://${join(__dirname)}/`).toString();

  win.loadURL(url);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
