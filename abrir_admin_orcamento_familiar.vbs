Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "E:\orcamentoapp"
shell.Run "cmd.exe /c ""E:\orcamentoapp\abrir_admin_vendas.bat""", 0, False
