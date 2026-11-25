"""Texto con tildes y ñ usando PIL, con caché de fuentes y de textos renderizados.

Cada texto se renderiza una sola vez a una imagen pequeña con alfa (caché LRU)
y luego se mezcla en el frame con numpy: mucho más rápido que convertir el
frame entero a PIL en cada llamada.
"""
from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config as C


@lru_cache(maxsize=32)
def leer_imagen(ruta: str, flags: int = 1) -> np.ndarray | None:
    """cv2.imread que funciona con rutas no ASCII en Windows (lee los bytes con Python)."""
    import cv2
    try:
        datos = np.fromfile(ruta, dtype=np.uint8)
    except OSError:
        return None
    return cv2.imdecode(datos, flags) if datos.size else None


@lru_cache(maxsize=32)
def fuente(tam: int) -> ImageFont.FreeTypeFont:
    """Primera fuente disponible de config.FUENTES al tamaño dado (cacheada)."""
    for ruta in C.FUENTES:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, tam)
            except OSError:
                continue
    return ImageFont.load_default(size=tam)


@lru_cache(maxsize=512)
def _renderizar(texto: str, tam: int, color: tuple, sombra: bool) -> tuple[np.ndarray, np.ndarray]:
    """Renderiza el texto a (bgr uint8 HxWx3, alfa float32 HxWx1)."""
    f = fuente(tam)
    izq, arr, der, aba = f.getbbox(texto or " ")
    off = max(2, tam // 16) if sombra else 0
    w, h = der - izq + off + 2, aba - arr + off + 2
    img = Image.new("RGBA", (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rgb = (color[2], color[1], color[0], 255)
    if sombra:
        d.text((-izq + off, -arr + off), texto, font=f, fill=(0, 0, 0, 200))
    d.text((-izq, -arr), texto, font=f, fill=rgb)
    arr_img = np.asarray(img)
    bgr = np.ascontiguousarray(arr_img[:, :, 2::-1])
    alfa = (arr_img[:, :, 3:4].astype(np.float32)) / 255.0
    return bgr, alfa


def tamano_texto(texto: str, tam: int = C.TAM_TEXTO) -> tuple[int, int]:
    """Ancho y alto en px del texto renderizado."""
    bgr, _ = _renderizar(texto, tam, (255, 255, 255), True)
    return bgr.shape[1], bgr.shape[0]


def pegar_rgba(frame: np.ndarray, bgr: np.ndarray, alfa: np.ndarray, x: int, y: int) -> None:
    """Mezcla una imagen con alfa en el frame en (x, y) (esquina sup. izq.), recortando."""
    h, w = bgr.shape[:2]
    H, W = frame.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    sx, sy = x0 - x, y0 - y
    region = frame[y0:y1, x0:x1].astype(np.float32)
    a = alfa[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
    src = bgr[sy:sy + (y1 - y0), sx:sx + (x1 - x0)].astype(np.float32)
    frame[y0:y1, x0:x1] = (src * a + region * (1.0 - a)).astype(np.uint8)


def envolver(txt: str, tam: int, ancho_max: int) -> list[str]:
    """Parte el texto en líneas que no superan ancho_max px."""
    lineas, actual = [], ""
    for palabra in txt.split():
        prueba = f"{actual} {palabra}".strip()
        if actual and tamano_texto(prueba, tam)[0] > ancho_max:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def parrafo(frame: np.ndarray, txt: str, centro_x: int, y: int, tam: int, color: tuple,
            ancho_max: int, interlineado: float = 1.25) -> int:
    """Texto centrado partido en líneas de como mucho ancho_max px. Devuelve la y siguiente."""
    for linea in envolver(txt, tam, ancho_max):
        texto(frame, linea, (centro_x, y), tam, color, "centro")
        y += int(tam * interlineado)
    return y


def texto(frame: np.ndarray, txt: str, pos: tuple[int, int], tam: int = C.TAM_TEXTO,
          color: tuple = C.BLANCO, ancla: str = "izq", sombra: bool = True) -> tuple[int, int]:
    """Dibuja texto. pos = (x, y) de la parte superior; ancla: "izq", "centro" o "der"."""
    bgr, alfa = _renderizar(str(txt), int(tam), tuple(color), sombra)
    w, h = bgr.shape[1], bgr.shape[0]
    x, y = pos
    if ancla == "centro":
        x -= w // 2
    elif ancla == "der":
        x -= w
    pegar_rgba(frame, bgr, alfa, int(x), int(y))
    return w, h


def panel(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int,
          color: tuple = C.PANEL_FONDO, alfa: float = C.PANEL_ALFA) -> None:
    """Rectángulo semitransparente (para fondos de texto)."""
    H, W = frame.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x0 >= x1 or y0 >= y1:
        return
    region = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (region * (1 - alfa) + np.array(color, np.float32) * alfa).astype(np.uint8)
