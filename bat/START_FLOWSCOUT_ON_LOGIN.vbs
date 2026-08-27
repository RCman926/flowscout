' Silent FlowScout login starter — no console flash, no browser.
' Installed as a Startup-folder shortcut by install_startup.ps1
Option Explicit
Dim sh, fso, here, ps1
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
here = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = here & "\START_FLOWSCOUT_ON_LOGIN.ps1"
If fso.FileExists(ps1) = False Then WScript.Quit 1
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ps1 & """", 0, False
