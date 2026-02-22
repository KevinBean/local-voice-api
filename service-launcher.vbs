' Local Voice API - Silent Launcher
' Runs service.bat with a hidden window (no console flash).
' Used by Task Scheduler / Startup folder for auto-start at logon.

Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c ""C:\Users\Kevin\local-voice-api\service.bat""", 0, False
