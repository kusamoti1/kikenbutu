Set WshShell = CreateObject("WScript.Shell")
' アプリ起動は黒い画面を隠す (0=非表示)
' Streamlit がブラウザを自動で開くので、ユーザーはブラウザだけ見える
WshShell.Run """" & Replace(WScript.ScriptFullName, ".vbs", ".bat") & """", 0, False
