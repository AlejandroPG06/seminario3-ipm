"""Diagnóstico de la webcam: prueba formatos y resoluciones y mide los fps reales.

Uso:  python tools/probar_camara.py [--camera N]
Con el resultado, ajusta CAMARA_FORMATO / CAMARA_*_PEDIDO en config.py o usa
python main.py --formato MJPG --resolucion 640x480
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.camera import configurar_camara, describir  # noqa: E402

PRUEBAS = [("MJPG", 1280, 720), ("MJPG", 640, 480), ("YUYV", 640, 480), ("", 1280, 720), ("", 640, 480)]


def probar(camara: int, formato: str, ancho: int, alto: int, segundos: float = 4.0) -> str:
    backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
    cap = cv2.VideoCapture(camara, backend)
    if not cap.isOpened():
        return "no se abre (¿permisos de /dev/video0? ¿cámara en uso?)"
    configurar_camara(cap, ancho, alto, formato)
    real = describir(cap)
    t0 = time.monotonic()
    n = fallos = 0
    while time.monotonic() - t0 < segundos and fallos < 3:
        ok, _ = cap.read()
        n, fallos = (n + 1, fallos) if ok else (n, fallos + 1)
    dt = time.monotonic() - t0
    cap.release()
    return f"acepta {real}: {n / dt:5.1f} fps" + (f"  ({fallos} lecturas fallidas)" if fallos else "")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--camera", type=int, default=0)
    args = p.parse_args()
    for formato, ancho, alto in PRUEBAS:
        etiqueta = f"{formato or 'por defecto':>11} {ancho}x{alto}"
        print(f"{etiqueta}: {probar(args.camera, formato, ancho, alto)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
