"""Ventana del juego con OpenCV, igual de bien en Windows y en Linux.

En Linux, opencv-python dibuja las ventanas con Qt: añade una barra de
herramientas y otra de estado, y no estira la imagen al maximizar. Por eso, con
Qt, la ventana se crea sin barras y del tamaño exacto de la imagen
(WINDOW_AUTOSIZE) y es el juego el que escala cada frame al tamaño de la
pantalla. En Windows (Win32) la ventana normal ya escala la imagen sola.
F11 alterna la pantalla completa en los dos casos.
"""
from __future__ import annotations

import subprocess

import cv2
import numpy as np

import config as C


def tamano_pantalla() -> tuple[int, int] | None:
    """(ancho, alto) de la pantalla en px, o None si no se puede saber."""
    try:
        import tkinter as tk
        raiz = tk.Tk()
        raiz.withdraw()
        tam = raiz.winfo_screenwidth(), raiz.winfo_screenheight()
        raiz.destroy()
        if tam[0] > 0 and tam[1] > 0:
            return tam
    except Exception:  # noqa: BLE001 - sin Tk o sin servidor gráfico
        pass
    try:
        salida = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=2).stdout
        actual = salida.split("current", 1)[1].split(",", 1)[0]          # " 1920 x 1080"
        w, h = (int(v) for v in actual.split("x"))
        return w, h
    except Exception:  # noqa: BLE001
        return None


def encajar(img: np.ndarray, ancho: int, alto: int, rellenar: bool) -> np.ndarray:
    """Escala manteniendo la proporción para caber en ancho×alto; con rellenar, añade bandas negras."""
    h, w = img.shape[:2]
    esc = min(ancho / w, alto / h)
    nw, nh = max(1, int(w * esc)), max(1, int(h * esc))
    if (nw, nh) != (w, h):
        img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR if esc > 1 else cv2.INTER_AREA)
    if not rellenar or (nw, nh) == (ancho, alto):
        return img
    lienzo = np.zeros((alto, ancho, 3), np.uint8)
    x, y = (ancho - nw) // 2, (alto - nh) // 2
    lienzo[y:y + nh, x:x + nw] = img
    return lienzo


class Ventana:
    """Muestra los frames; F11 (alternar) pone o quita la pantalla completa."""

    def __init__(self, nombre: str = C.VENTANA_NOMBRE, pantalla_completa: bool = False):
        self.nombre = nombre
        marco = cv2.currentUIFramework().upper() if hasattr(cv2, "currentUIFramework") else ""
        self.qt = marco.startswith("QT")
        if self.qt:
            flags = cv2.WINDOW_AUTOSIZE | getattr(cv2, "WINDOW_GUI_NORMAL", 0)
            self.pantalla = tamano_pantalla()
        else:
            flags = cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO
            self.pantalla = None
        cv2.namedWindow(nombre, flags)
        self.completa = pantalla_completa
        self._primera = True

    def mostrar(self, img: np.ndarray) -> None:
        if self.qt and self.pantalla is not None:
            W, H = self.pantalla
            if self.completa:
                img = encajar(img, W, H, rellenar=True)
            else:       # ventana grande, sin salirse de la pantalla (deja sitio a barras y bordes)
                img = encajar(img, int(W * C.VENTANA_FRACCION_PANTALLA), int(H * C.VENTANA_FRACCION_PANTALLA),
                              rellenar=False)
        cv2.imshow(self.nombre, img)
        if self._primera:
            self._primera = False
            if not self.qt:
                cv2.resizeWindow(self.nombre, img.shape[1], img.shape[0])
            if self.completa:
                self._aplicar()

    def alternar(self) -> None:
        self.completa = not self.completa
        self._aplicar()

    def _aplicar(self) -> None:
        modo = cv2.WINDOW_FULLSCREEN if self.completa else cv2.WINDOW_NORMAL
        cv2.setWindowProperty(self.nombre, cv2.WND_PROP_FULLSCREEN, modo)

    def cerrada(self) -> bool:
        return cv2.getWindowProperty(self.nombre, cv2.WND_PROP_VISIBLE) < 1
