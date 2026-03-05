Set WshShell = CreateObject("WScript.Shell")
' 初期設定は進捗が見えた方が安心なので、ウィンドウを表示する (1=通常表示)
WshShell.Run """" & Replace(WScript.ScriptFullName, ".vbs", ".bat") & """", 1, True
