@echo off
REM Instalacion de "El Gran Circo del Equilibrio" en Windows.
REM Ejecutar desde "Anaconda Prompt" (o una consola con conda en el PATH).
REM Crea el entorno conda IPM (Python 3.12), instala dependencias, descarga
REM los modelos y genera los sonidos. Se puede ejecutar varias veces.
REM   Uso: setup.bat          (anade --dev para instalar tambien pytest)
setlocal
cd /d "%~dp0"
set ENTORNO=IPM

where conda >nul 2>nul
if errorlevel 1 (
    echo ERROR: no se encuentra conda. Abre "Anaconda Prompt" o instala Miniconda.
    exit /b 1
)

call conda env list | findstr /B /C:"%ENTORNO% " >nul
if errorlevel 1 (
    echo ^>^> Creando el entorno %ENTORNO% con Python 3.12...
    call conda create -n %ENTORNO% python=3.12 -y || exit /b 1
) else (
    echo ^>^> El entorno %ENTORNO% ya existe: se reutiliza.
)
call conda activate %ENTORNO% || exit /b 1
REM Python del entorno por ruta absoluta (otro entorno puede ir antes en el PATH)
set "PY=%CONDA_PREFIX%\python.exe"
if not exist "%PY%" (
    echo ERROR: no se pudo activar el entorno %ENTORNO%
    exit /b 1
)

echo ^>^> Instalando dependencias...
"%PY%" -m pip install --upgrade pip
if "%~1"=="--dev" (
    "%PY%" -m pip install -r requirements-dev.txt || exit /b 1
) else (
    "%PY%" -m pip install -r requirements.txt || exit /b 1
)

echo ^>^> Descargando modelos de MediaPipe...
"%PY%" download_models.py || exit /b 1
if not exist models\pose_landmarker_full.task (
    echo ERROR: no se pudo descargar models\pose_landmarker_full.task
    exit /b 1
)

echo ^>^> Generando sonidos...
"%PY%" tools\generate_assets.py || exit /b 1
if not exist data mkdir data

echo.
echo Instalacion completada. Para jugar:
echo     conda activate %ENTORNO%
echo     python main.py
endlocal
