' ==================================================
'  危険物法令ナレッジグラフAI - データ取込
'  ダブルクリックで実行してください
' ==================================================
Dim WshShell, batPath, fso, result

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

batPath = Replace(WScript.ScriptFullName, ".vbs", ".bat")

If Not fso.FileExists(batPath) Then
    MsgBox "データ取込ファイル（.bat）が見つかりません。" & vbCrLf & _
           "このファイルと同じフォルダに「②データ取込.bat」があるか" & vbCrLf & _
           "確認してください。", vbExclamation, "危険物法令ナレッジAI"
    WScript.Quit
End If

' データ取込は進捗を見せる（1 = ウィンドウ表示）
result = WshShell.Run("""" & batPath & """", 1, True)
