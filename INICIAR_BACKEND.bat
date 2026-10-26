@echo off
setlocal
cd /d "%~dp0"
title Backend FastAPI - Sistema Hospitalario

if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta PREPARAR_PROYECTO.bat.
    pause
    exit /b 1
)

echo Iniciando API. No cierres esta ventana.
echo Documentacion: http://127.0.0.1:8000/docs
".venv\Scripts\python.exe" run_backend.py
pause
