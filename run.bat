@echo off
title SiriloQwenTTS Pro
cd /d "%~dp0"

echo ========================================
echo    SiriloQwenTTS Pro
echo ========================================
echo.

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Verificar si los modelos estan descargados
if not exist "models\Qwen3-TTS-Tokenizer-12Hz" (
    echo Primera ejecucion: descargando modelos...
    echo Esto puede tomar varios minutos...
    echo.
    python download_models.py
    echo.
)

REM Instalar dependencias Python de la API si faltan
pip show sse-starlette >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias de la API...
    pip install fastapi "uvicorn[standard]" sse-starlette python-multipart
    echo.
)

REM Reinstalar node_modules desde Windows si falta vite.cmd
if not exist "ui\node_modules\.bin\vite.cmd" (
    echo Instalando dependencias del frontend desde Windows...
    if exist "ui\node_modules" (
        echo Eliminando node_modules de Linux...
        rmdir /s /q "ui\node_modules"
    )
    pushd ui
    call npm install
    popd
    echo.
)

echo Iniciando backend en puerto 8000...
start "SiriloQwenTTS API" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python -m api.run"

echo Esperando al backend...
timeout /t 5 /nobreak >nul

echo Iniciando frontend en puerto 5173...
start "SiriloQwenTTS UI" cmd /k "cd /d %~dp0ui && node node_modules\vite\bin\vite.js"

echo Esperando al frontend...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo    Abriendo http://localhost:5173
echo ========================================
echo.
start "" http://localhost:5173

echo.
echo Backend API:  http://localhost:8000/docs
echo Frontend UI:  http://localhost:5173
echo.
echo Presiona cualquier tecla para detener todo...
pause >nul

REM Cerrar ambos procesos
taskkill /FI "WINDOWTITLE eq SiriloQwenTTS API" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq SiriloQwenTTS UI" /F >nul 2>&1
