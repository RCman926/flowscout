' ONE double-click: server + browser. No second file needed.
Option Explicit
Dim sh, fso, batDir, bat, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
batDir = fso.GetParentFolderName(WScript.ScriptFullName)
If fso.FileExists(batDir & "\START_FLOWSCOUT.bat") = False Then
  batDir = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\StreamlitExcel\bat"
End If
bat = batDir & "\START_FLOWSCOUT.bat"
If fso.FileExists(bat) = False Then
  MsgBox "Cannot find START_FLOWSCOUT.bat at:" & vbCrLf & bat, 16, "FlowScout"
  WScript.Quit 1
End If
' /c = run bat once and close this launcher (server stays in its own window)
cmd = "cmd.exe /c """ & bat & """"
sh.Run cmd, 1, False
