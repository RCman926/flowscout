# Weekday unattended FlowScout — wake PC, run server, EOD recap.
# Run once as Administrator:  powershell -ExecutionPolicy Bypass -File .\setup_windows_scheduler.ps1

$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = (Get-Command python).Source }
$startBat = Join-Path $root "START_UNATTENDED.bat"
$eod = Join-Path $root "eod_recap.py"

function Register-FsTask($name, $time, $execute, $args, $wake) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    $action = New-ScheduledTaskAction -Execute $execute -Argument $args -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $time
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    if ($wake) { $settings.WakeToRun = $true }
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest | Out-Null
    Write-Host "Created $name at $time"
}

Register-FsTask "FlowScout_RTH_Start" "09:20AM" "cmd.exe" "/c `"$startBat`"" $true
Register-FsTask "FlowScout_EOD_Recap" "04:20PM" $py "`"$eod`"" $true

Write-Host ""
Write-Host "Also in Power Options: enable wake timers, and do not sleep during 9:20-16:20 on weekdays."
Write-Host "Telegram recap needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
