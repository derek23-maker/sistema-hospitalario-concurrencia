@echo off
setlocal
cd /d "%~dp0"
title Preparar Sistema Hospitalario

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo No se encontro Python. Instala Python 3.11 o superior y marca
    echo la opcion "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

echo.
echo [1/3] Creando el entorno de Python...
python -m venv .venv
if errorlevel 1 goto :error

echo [2/3] Instalando FastAPI, Flet y MySQL Connector...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Creando el archivo de configuracion .env...
if not exist .env copy /Y .env.example .env >nul

echo.
echo Listo. Ahora abre el archivo .env y cambia DB_PASSWORD por la
echo contrasena con la que entras a MySQL Workbench.
echo Despues ejecuta INICIAR_BACKEND.bat y, en otra ventana, INICIAR_FLET.bat.
echo.
pause
exit /b 0

:error
echo.
echo No se pudo preparar el proyecto. Lee el mensaje anterior.
pause
exit /b 1
