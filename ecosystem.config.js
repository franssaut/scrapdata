const path = require('path');
const fs = require('fs');

/**
 * Konfigurasi PM2 untuk Bot Telegram & Web Server Cipta Group
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
      restart_delay: 5000,
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
