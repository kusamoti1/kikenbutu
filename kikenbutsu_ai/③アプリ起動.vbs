' ==================================================
'  危険物法令ナレッジグラフAI - アプリ起動
'  ダブルクリックで実行してください
'  ※ 黒い画面（コマンドプロンプト）は表示されません
'  ※ ブラウザが自動で開きます
' ==================================================
Dim WshShell, batPath, fso

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

batPath = Replace(WScript.ScriptFullName, ".vbs", ".bat")

If Not fso.FileExists(batPath) Then
    MsgBox "起動ファイル（.bat）が見つかりません。" & vbCrLf & _
           "このファイルと同じフォルダに「③アプリ起動.bat」があるか" & vbCrLf & _
           "確認してください。", vbExclamation, "危険物法令ナレッジAI"
    WScript.Quit
End If

' データベースが存在するか先にチェック
Dim dbPath, parentDir
parentDir = fso.GetParentFolderName(WScript.ScriptFullName)
dbPath = parentDir & "\database\kikenbutsu.db"

If Not fso.FileExists(dbPath) Then
    MsgBox "データベースがまだ作成されていません。" & vbCrLf & vbCrLf & _
           "先に「②データ取込」をダブルクリックして" & vbCrLf & _
           "PDFファイルを取り込んでください。", vbExclamation, "危険物法令ナレッジAI"
    WScript.Quit
End If

' アプリ起動（0 = 黒い画面を非表示、False = 待たない）
' ブラウザだけが開きます
WshShell.Run """" & batPath & """", 0, False

' 起動メッセージ
MsgBox "アプリを起動しています。" & vbCrLf & vbCrLf & _
       "数秒後にブラウザが自動で開きます。" & vbCrLf & _
       "もし開かない場合は、ブラウザで" & vbCrLf & _
       "http://localhost:8501 を開いてください。" & vbCrLf & vbCrLf & _
       "アプリを終了するには：" & vbCrLf & _
       "  タスクマネージャー（Ctrl+Shift+Esc）で" & vbCrLf & _
       "  「Python」を終了してください。", vbInformation, "危険物法令ナレッジAI"
