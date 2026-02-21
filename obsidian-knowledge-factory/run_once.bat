@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "ENGINE_DIR=%SCRIPT_DIR%engine"
set "CONFIG_FILE=%ENGINE_DIR%\config.yaml"
set "ENV_FILE=%ENGINE_DIR%\.env"
set "PYTHON_EXE=D:\vivi\.venv310\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
)

if not exist "%CONFIG_FILE%" (
  if exist "%ENGINE_DIR%\config.example.yaml" (
    copy "%ENGINE_DIR%\config.example.yaml" "%CONFIG_FILE%" >nul
    echo [info] Created config.yaml from config.example.yaml
  ) else (
    echo [error] Missing config file: %CONFIG_FILE%
    pause
    exit /b 1
  )
)

if not exist "%ENV_FILE%" (
  if exist "%ENGINE_DIR%\.env.example" (
    copy "%ENGINE_DIR%\.env.example" "%ENV_FILE%" >nul
    echo [error] Created .env from template. Please fill API values and rerun.
    pause
    exit /b 1
  )
)

findstr /C:"replace_me" "%ENV_FILE%" >nul
if not errorlevel 1 (
  echo [error] .env still has placeholder values. Fill OPENAI credentials first.
  pause
  exit /b 1
)

echo [run] Processing inbox in API mode...
set "PADDLE_PDX_CACHE_HOME=D:/pdxcache"
set "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=true"
"%PYTHON_EXE%" "%ENGINE_DIR%\main.py" --once --config "%CONFIG_FILE%" --env-file "%ENV_FILE%"

if errorlevel 1 (
  echo [error] run_once failed.
  pause
  exit /b 1
)

echo [ok] run_once completed.
pause
