' FlowScout desktop launcher — always RUNS the bat (never opens in an editor)
Option Explicit
Dim sh, fso, root, batDir, bat, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
If fso.FolderExists(root & "\bat") = False Then
  root = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\StreamlitExcel"
End If
batDir = root & "\bat"
bat = batDir & "\START_FLOWSCOUT.bat"
If fso.FileExists(bat) = False Then
  ' Fallback: old root launcher
  bat = root & "\START_FLOWSCOUT.bat"
End If
If fso.FileExists(bat) = False Then
  MsgBox "Cannot find START_FLOWSCOUT.bat." & vbCrLf & "Expected:" & vbCrLf & batDir & "\START_FLOWSCOUT.bat", 16, "FlowScout"
  WScript.Quit 1
End If
cmd = "cmd.exe /k """ & bat & """"
sh.Run cmd, 1, False
