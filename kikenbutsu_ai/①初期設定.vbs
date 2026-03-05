' ==================================================
'  危険物法令ナレッジグラフAI - 初期設定
'  ダブルクリックで実行してください
' ==================================================
Dim WshShell, batPath, fso, result

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 対応する .bat ファイルのパスを取得
batPath = Replace(WScript.ScriptFullName, ".vbs", ".bat")

' .bat ファイルが存在するか確認
If Not fso.FileExists(batPath) Then
    MsgBox "初期設定ファイル（.bat）が見つかりません。" & vbCrLf & _
           "このファイルと同じフォルダに「①初期設定.bat」があるか" & vbCrLf & _
           "確認してください。", vbExclamation, "危険物法令ナレッジAI"
    WScript.Quit
End If

' 初期設定は進捗を見せる（1 = ウィンドウ表示）
' True = 完了まで待つ
result = WshShell.Run("""" & batPath & """", 1, True)
