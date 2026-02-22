$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\LocalVoiceAPI.lnk")
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = '"C:\Users\Kevin\local-voice-api\service-launcher.vbs"'
$shortcut.WorkingDirectory = "C:\Users\Kevin\local-voice-api"
$shortcut.Description = "Local Voice API Auto-Start"
$shortcut.WindowStyle = 7
$shortcut.Save()
Write-Host "Shortcut created in Startup folder."
