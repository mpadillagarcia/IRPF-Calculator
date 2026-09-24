@echo off
setlocal

echo ============================================
echo   Calculadora IRPF - instalacion y arranque
echo ============================================
echo.

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encuentra Python en el PATH.
    echo Instala Python 3.10 o superior desde https://www.python.org/downloads/
    echo y marca la casilla "Add python.exe to PATH" durante la instalacion.
    pause
    exit /b 1
)

if not exist ".venv\" (
    echo [1/3] Creando entorno virtual local en .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Entorno virtual ya existe, se reutiliza.
)

echo [2/3] Instalando dependencias ...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Fallo instalando dependencias.
    pause
    exit /b 1
)

echo [3/3] Arrancando la aplicacion ...
echo.
echo Se abrira el navegador con la calculadora. Para cerrar, cierra esta
echo ventana o pulsa Ctrl+C.
echo.

call ".venv\Scripts\python.exe" -m streamlit run app.py

pause
