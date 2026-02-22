$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument '"C:\Users\Kevin\local-voice-api\service-launcher.vbs"' -WorkingDirectory "C:\Users\Kevin\local-voice-api"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "LocalVoiceAPI" -Action $action -Trigger $trigger -Settings $settings -Description "Local Voice API - STT/TTS/LLM server on port 8601" -Force
Write-Host "Task registered successfully."
