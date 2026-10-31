const path = require('path');
const fs = require('fs');

/**
 * Konfigurasi PM2 untuk Bot Telegram & Web Server Cipta Group
 * Dilengkapi pengaturan anti-restart loop (stabilitas 24/7)
 */
function getPythonInterpreter() {
  const localAppData = process.env.LOCALAPPDATA || 'C:\\Users\\user\\AppData\\Local';
  const customPython = path.join(localAppData, 'Python', 'pythoncore-3.15-64', 'python.exe');
  if (fs.existsSync(customPython)) {
    return customPython;
  }
  return 'python';
}

module.exports = {
  apps: [
    {
      name: 'cipta-bot',
      script: 'bot.py',
      interpreter: getPythonInterpreter(),
      autorestart: true,
      min_uptime: '15s',                // Waktu minimum agar dianggap stabil
      max_restarts: 10,                 // Batasi loop restart jika terjadi error
      restart_delay: 5000,              // Jeda 5 detik antar-restart agar koneksi Telegram bersih
      kill_timeout: 4000,               // Waktu graceful shutdown
      watch: false,
      max_memory_restart: '250M',
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'cipta-web',
      script: 'app.py',
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
