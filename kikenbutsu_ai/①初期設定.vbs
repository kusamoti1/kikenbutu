' ==================================================
'  Kikenbutsu Knowledge Graph AI - Initial Setup
'  Double-click to run
' ==================================================
Dim WshShell, batPath, fso, result

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Resolve the paired .bat path
batPath = Replace(WScript.ScriptFullName, ".vbs", ".bat")

' Verify .bat file exists
If Not fso.FileExists(batPath) Then
    MsgBox "The setup batch file (.bat) was not found." & vbCrLf & _
           "Please make sure the matching .bat file is in the same folder.", _
           vbExclamation, "Kikenbutsu Knowledge Graph AI"
    WScript.Quit
End If

' Show progress window (1) and wait until completion (True)
result = WshShell.Run("""" & batPath & """", 1, True)
