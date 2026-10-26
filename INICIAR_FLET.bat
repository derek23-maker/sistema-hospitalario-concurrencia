@echo off
setlocal
cd /d "%~dp0"
title Aplicacion Flet - Sistema Hospitalario

if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta PREPARAR_PROYECTO.bat.
    pause
    exit /b 1
)

echo Iniciando la aplicacion de citas...
".venv\Scripts\python.exe" -m flet run frontend\app.py
pause
