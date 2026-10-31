Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\user\Music\scraping"
WshShell.Run "pythonw.exe bot.py", 0, False
