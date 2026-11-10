/**
 * APEX desktop — processus principal Electron.
 * Ouvre une fenêtre avec le site APEX (build statique) et fournit un
 * canal IPC vers le backend local (port auto-découvert).
 */
import { app, BrowserWindow, ipcMain, shell } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import * as http from 'http';

const isDev = !!process.env.ELECTRON_IS_DEV;
const SITE_ROOT = path.join(__dirname, '..', 'out');

function resolveBackendPort(): number | null {
  const stateFile = path.join(app.getPath('userData'), '..', '.apex', 'state', 'port');
  try {
    const port = fs.readFileSync(stateFile, 'utf8').trim();
    return Number(port) || null;
  } catch {
    return null;
  }
}

function serveStatic(req: http.IncomingMessage, res: http.ServerResponse) {
  const urlPath = decodeURIComponent(new URL(req.url ?? '/', 'http://localhost').pathname);
  let file = path.join(SITE_ROOT, urlPath === '/' ? 'index.html' : urlPath);
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    file = path.join(SITE_ROOT, urlPath, 'index.html');
  }
  if (!fs.existsSync(file)) file = path.join(SITE_ROOT, '404.html');

  const ext = path.extname(file);
  const mime: Record<string, string> = {
    '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
    '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json',
  };
  res.writeHead(200, { 'Content-Type': mime[ext] ?? 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}

async function createWindow() {
  // Serveur local pour le site statique
  const httpServer = http.createServer(serveStatic);
  await new Promise<void>((resolve) => httpServer.listen(0, '127.0.0.1', resolve));
  const port = (httpServer.address() as any).port;

  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    title: 'APEX',
    webPreferences: { preload: path.join(__dirname, 'preload.js') },
  });

  await win.loadURL(`http://127.0.0.1:${port}`);

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

ipcMain.handle('apex:backend-port', () => resolveBackendPort());

app.whenReady().then(async () => {
  await createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
