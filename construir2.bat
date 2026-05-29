@echo off
echo.
echo ==========================================
echo LIMPANDO CONSTRUCOES ANTIGAS...
echo ==========================================

set BACKUP_DB=
if exist "dist\budget_app.db" (
    set BACKUP_DB=%TEMP%\budget_app_backup_%RANDOM%_%RANDOM%.db
    copy /Y "dist\budget_app.db" "%BACKUP_DB%"
)

:: Remove as pastas antigas para garantir build limpa
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo.
echo ==========================================
echo EXECUTANDO O PYINSTALLER...
echo ==========================================

:: Gera o executável diretamente em dist/
python -m PyInstaller --noconfirm --clean main_personal.spec

echo.
echo ==========================================
echo COPIANDO ARQUIVOS DE RECURSOS PARA DIST...
echo ==========================================

:: Cria a pasta dist caso não exista
if not exist "dist" mkdir dist

:: Copia as pastas de recursos para o mesmo nível do executável
xcopy templates dist\templates\ /E /I /Y
xcopy static dist\static\ /E /I /Y

:: Copia o favicon diretamente
if exist favicon.ico copy /Y favicon.ico dist\favicon.ico

:: Restaura o banco existente para nao perder dados ja cadastrados
if defined BACKUP_DB (
    if exist "%BACKUP_DB%" (
        copy /Y "%BACKUP_DB%" "dist\budget_app.db"
        del "%BACKUP_DB%"
    )
)

echo.
echo ==========================================
echo CONSTRUCAO CONCLUIDA!
echo O executavel e os recursos estao em dist\
echo ==========================================

pause



