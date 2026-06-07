@echo off
setlocal EnableExtensions

cd /d "%~dp0"

rem Codigo generico da rotina (provisorio). Trocar se houver codigo oficial.
set "APP_NAME=PCWNT_9520"
set "VENV_DIR=.venv-build64"
set "PYTHON_EXE="

echo.
echo === Build %APP_NAME% ===
echo Diretorio: %CD%
echo.

if exist "%VENV_DIR%\Scripts\python.exe" (
  set "PYTHON_EXE=%CD%\%VENV_DIR%\Scripts\python.exe"
) else (
  for /f "tokens=*" %%I in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%I"
  if not defined PYTHON_EXE (
    for /f "tokens=*" %%I in ('py -3.11 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%I"
  )
)

if not defined PYTHON_EXE (
  echo ERRO: Python 3.12 ou 3.11 64-bit nao encontrado.
  echo Instale Python 64-bit ou confira os interpretes com: py -0p
  exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo Criando venv de build 32-bit com:
  echo %PYTHON_EXE%
  "%PYTHON_EXE%" -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo ERRO: falha ao criar %VENV_DIR%.
    exit /b 1
  )
)

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo ERRO: falha ao ativar %VENV_DIR%.
  exit /b 1
)

python -c "import struct, sys; bits=struct.calcsize('P')*8; print('Python:', sys.version); print('Bits:', bits); raise SystemExit(0 if bits == 64 else 1)"
if errorlevel 1 (
  echo ERRO: a venv de build nao e 64-bit.
  echo Apague a pasta %VENV_DIR% e execute build.bat novamente.
  exit /b 1
)

echo.
echo Instalando/atualizando dependencias...
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Gerando whitelist de licenca...
python scripts\gerar_licenca_config.py
if errorlevel 1 (
  echo ERRO: falha ao gerar a whitelist de licenca.
  exit /b 1
)

echo.
echo Validando bytecode...
python -m compileall -q app.py core servicos modelos ui_widgets
if errorlevel 1 (
  echo ERRO: falha na validacao de bytecode.
  exit /b 1
)

echo.
echo Gerando executavel com PyInstaller...
pyinstaller --clean --noconfirm %APP_NAME%.spec
if errorlevel 1 (
  echo ERRO: falha no PyInstaller.
  exit /b 1
)

if not exist "dist\%APP_NAME%.exe" (
  echo ERRO: executavel nao encontrado em dist\%APP_NAME%.exe.
  exit /b 1
)

echo.
echo Build concluido:
echo %CD%\dist\%APP_NAME%.exe
echo.
echo Para o menu WinThor, configure a chamada para este .exe preservando:
echo USUARIOWT SENHABD ALIASBD USUARIOBD CODROTINA
echo.

endlocal
