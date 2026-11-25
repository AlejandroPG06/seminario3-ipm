#!/usr/bin/env bash
# Instalación de «El Gran Circo del Equilibrio» en Linux / macOS.
# Crea el entorno conda IPM (Python 3.12), instala dependencias, descarga los
# modelos y genera los sonidos. Se puede ejecutar varias veces sin problema.
#   Uso: bash setup.sh          (añade --dev para instalar también pytest)
set -euo pipefail
cd "$(dirname "$0")"

ENTORNO="IPM"

if ! command -v conda >/dev/null 2>&1; then
    echo "ERROR: no se encuentra conda. Instala Miniconda: https://docs.anaconda.com/miniconda/" >&2
    exit 1
fi
eval "$(conda shell.bash hook)"

if conda env list | awk '{print $1}' | grep -qx "$ENTORNO"; then
    echo ">> El entorno '$ENTORNO' ya existe: se reutiliza."
else
    echo ">> Creando el entorno '$ENTORNO' con Python 3.12..."
    conda create -n "$ENTORNO" python=3.12 -y
fi
conda activate "$ENTORNO"
# Python del entorno por ruta absoluta: otro entorno puede ir antes en el PATH
# (p. ej. el intérprete que tenga seleccionado VS Code).
PY="$CONDA_PREFIX/bin/python"
if [[ "$CONDA_DEFAULT_ENV" != "$ENTORNO" || ! -x "$PY" ]]; then
    echo "ERROR: no se pudo activar el entorno '$ENTORNO'" >&2
    exit 1
fi

echo ">> Instalando dependencias..."
"$PY" -m pip install --upgrade pip
if [[ "${1:-}" == "--dev" ]]; then
    "$PY" -m pip install -r requirements-dev.txt
else
    "$PY" -m pip install -r requirements.txt
fi

echo ">> Descargando modelos de MediaPipe..."
"$PY" download_models.py
if [[ ! -s models/pose_landmarker_full.task ]]; then
    echo "ERROR: no se pudo descargar models/pose_landmarker_full.task" >&2
    exit 1
fi

echo ">> Generando sonidos..."
"$PY" tools/generate_assets.py
mkdir -p data

if ! "$PY" -c "import sounddevice" >/dev/null 2>&1; then
    echo "AVISO: sounddevice no encuentra PortAudio; el juego funcionará sin sonido."
    echo "       En Debian/Ubuntu: sudo apt install libportaudio2"
fi

echo
echo "Instalación completada. Para jugar:"
echo "    conda activate $ENTORNO"
echo "    python main.py"
echo "(Si 'python' no es el de $ENTORNO, usa: $PY main.py)"
