@echo off
REM Abre IDLE con el intérprete .venv del proyecto, sin mostrar una consola.
start "IDLE - Sistema Hospitalario" "%~dp0.venv\Scripts\pythonw.exe" -m idlelib
