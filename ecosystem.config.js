const path = require('path');
const fs = require('fs');

/**
 * Konfigurasi PM2 untuk Bot Telegram & Web Server Cipta Group
 * Dilengkapi direktori kerja tetap (cwd) & pengaturan anti-restart loop
 */
function getPythonInterpreter() {
  // 1. Cek jika ada virtual environment (venv) lokal di direktori proyek
  const venvLinux = path.join(__dirname, 'venv', 'bin', 'python3');
  if (fs.existsSync(venvLinux)) return venvLinux;

  const dotVenvLinux = path.join(__dirname, '.venv', 'bin', 'python3');
  if (fs.existsSync(dotVenvLinux)) return dotVenvLinux;

  const venvWin = path.join(__dirname, 'venv', 'Scripts', 'python.exe');
  if (fs.existsSync(venvWin)) return venvWin;

  // 2. Cek instalasi Python khusus di Windows
  const localAppData = process.env.LOCALAPPDATA || 'C:\\Users\\user\\AppData\\Local';
  const customPython = path.join(localAppData, 'Python', 'pythoncore-3.15-64', 'python.exe');
  if (fs.existsSync(customPython)) {
    return customPython;
  }

  // 3. Fallback default: di Linux/Ubuntu gunakan 'python3', di Windows gunakan 'python'
  return process.platform === 'win32' ? 'python' : 'python3';
}

module.exports = {
  apps: [
    {
      name: 'cipta-bot',
      cwd: __dirname,
      script: path.join(__dirname, 'bot.py'),
      interpreter: getPythonInterpreter(),
      autorestart: true,
      min_uptime: '15s',
      max_restarts: 10,
      restart_delay: 5000,
      kill_timeout: 4000,
      watch: false,
      max_memory_restart: '250M',
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'cipta-web',
      cwd: __dirname,
      script: path.join(__dirname, 'app.py'),
      interpreter: getPythonInterpreter(),
      autorestart: true,
      min_uptime: '10s',
      restart_delay: 3000,
      watch: false,
      max_memory_restart: '200M',
      env: {
        PYTHONUNBUFFERED: '1',
        PORT: 8000,
      },
    },
  ],
};
