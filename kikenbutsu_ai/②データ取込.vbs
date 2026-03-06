' ==================================================
'  Kikenbutsu Knowledge Graph AI - Data Import
'  Double-click to run
' ==================================================
Dim WshShell, batPath, fso, result

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

batPath = Replace(WScript.ScriptFullName, ".vbs", ".bat")

If Not fso.FileExists(batPath) Then
    MsgBox "The data import batch file (.bat) was not found." & vbCrLf & _
           "Please make sure the matching .bat file is in the same folder.", _
           vbExclamation, "Kikenbutsu Knowledge Graph AI"
    WScript.Quit
End If

' Show progress window (1) and wait until completion (True)
result = WshShell.Run("""" & batPath & """", 1, True)
