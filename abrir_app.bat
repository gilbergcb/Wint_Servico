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

if not exist "codclipc_liberados.txt" (
  echo Arquivo codclipc_liberados.txt nao encontrado.
  echo Informe os CODCLIPC liberados, um por linha.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" scripts\gerar_licenca_config.py

if errorlevel 1 (
  echo.
  echo Falha ao validar codclipc_liberados.txt.
  echo Corrija o arquivo e tente novamente.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" app.py

if errorlevel 1 (
  echo.
  echo O aplicativo encerrou com erro.
  pause
)
