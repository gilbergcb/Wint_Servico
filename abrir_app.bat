@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado.
  echo Crie com: py -3.12-32 -m venv .venv
  echo E instale as dependencias: .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

".venv\Scripts\python.exe" app.py

if errorlevel 1 (
  echo.
  echo O aplicativo encerrou com erro.
  pause
)
