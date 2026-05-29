@echo off
cd /d "%~dp0"
echo Iniciando Admin de Vendas em http://127.0.0.1:8020
start "" http://127.0.0.1:8020
venv_app\Scripts\python.exe admin_vendas.py
pause
