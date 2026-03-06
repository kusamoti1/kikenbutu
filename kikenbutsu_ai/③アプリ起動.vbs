' ==================================================
'  Kikenbutsu Knowledge Graph AI - Launch App
'  Double-click to run
' ==================================================
Dim WshShell, batPath, fso

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

batPath = Replace(WScript.ScriptFullName, ".vbs", ".bat")

If Not fso.FileExists(batPath) Then
    MsgBox "The launch batch file (.bat) was not found." & vbCrLf & _
           "Please make sure the matching .bat file is in the same folder.", _
           vbExclamation, "Kikenbutsu Knowledge Graph AI"
    WScript.Quit
End If

' Check DB file before launching app
Dim dbPath, parentDir
parentDir = fso.GetParentFolderName(WScript.ScriptFullName)
dbPath = parentDir & "\database\kikenbutsu.db"

If Not fso.FileExists(dbPath) Then
    MsgBox "Database file not found." & vbCrLf & vbCrLf & _
           "Run the data import step first to create the database.", _
           vbExclamation, "Kikenbutsu Knowledge Graph AI"
    WScript.Quit
End If

' Launch app without opening a console window (0), do not wait (False)
WshShell.Run """" & batPath & """", 0, False

MsgBox "Launching the app now." & vbCrLf & vbCrLf & _
       "A browser should open in a few seconds." & vbCrLf & _
       "If not, open: http://localhost:8501" & vbCrLf & vbCrLf & _
       "To stop the app, end Python in Task Manager.", _
       vbInformation, "Kikenbutsu Knowledge Graph AI"
