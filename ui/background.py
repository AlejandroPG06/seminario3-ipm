"""Fondo de carpa de circo procedural, compuesto con la máscara de segmentación."""
from __future__ import annotations

import os

import cv2
import numpy as np

import config as C
from ui.text import leer_imagen


def generar_carpa(ancho: int, alto: int) -> np.ndarray:
    """Carpa a rayas radiales con arena en el suelo y bombillas (BGR uint8)."""
    ys, xs = np.mgrid[0:alto, 0:ancho].astype(np.float32)
    ang = np.arctan2(ys + alto * 0.25, xs - ancho / 2.0)
    franjas = (np.floor(ang / (np.pi / 18)) % 2).astype(bool)
    img = np.empty((alto, ancho, 3), np.uint8)
    img[franjas] = C.ROJO_CARPA
    img[~franjas] = C.CREMA_CARPA
    # Viñeta para que el jugador destaque
    dist = np.sqrt(((xs - ancho / 2) / ancho) ** 2 + ((ys - alto / 2) / alto) ** 2)
    oscuro = np.clip(1.0 - dist * 0.9, 0.35, 1.0)[..., None]
    img = (img.astype(np.float32) * oscuro).astype(np.uint8)
    # Arena
    suelo = int(alto * 0.78)
    img[suelo:] = (90, 160, 205)
    cv2.ellipse(img, (ancho // 2, alto + alto // 8), (int(ancho * 0.55), int(alto * 0.32)),
                0, 180, 360, (60, 120, 170), 6, cv2.LINE_AA)
    # Guirnalda de bombillas
    for i in range(24):
        x = int((i + 0.5) * ancho / 24)
        y = int(alto * 0.07 + 18 * np.sin(i * np.pi / 3))
        cv2.circle(img, (x, y), 7, C.AMARILLO, -1, cv2.LINE_AA)
    return img


class Fondo:
    """Sustituye el fondo de la cámara por la carpa usando la máscara de la persona.

    Si existe assets/fondo.png se usa en lugar de la carpa procedural.
    """

    def __init__(self, activado: bool = C.FONDO_SEGMENTACION, directorio: str = C.ASSETS_DIR):
        self.activado = activado
        ruta = os.path.join(directorio, "fondo.png") if directorio else ""
        self._png = leer_imagen(ruta) if ruta and os.path.exists(ruta) else None
        self._cache: dict[tuple[int, int], np.ndarray] = {}

    def imagen(self, ancho: int, alto: int) -> np.ndarray:
        """Imagen de fondo al tamaño pedido (cacheada)."""
        clave = (ancho, alto)
        if clave not in self._cache:
            if self._png is not None:
                self._cache[clave] = cv2.resize(self._png, (ancho, alto))
            else:
                self._cache[clave] = generar_carpa(ancho, alto)
        return self._cache[clave]

    def componer(self, frame: np.ndarray, mascara: np.ndarray | None) -> np.ndarray:
        """Persona (máscara≈1) sobre la carpa; si no hay máscara devuelve el frame tal cual."""
        if not self.activado or mascara is None:
            return frame
        alto, ancho = frame.shape[:2]
        m = mascara.astype(np.float32)
        if m.shape[:2] != (alto, ancho):
            m = cv2.resize(m, (ancho, alto))
        lo, hi = C.MASCARA_UMBRAL_SUAVE
        m = np.clip((m - lo) / (hi - lo), 0.0, 1.0)
        return cv2.blendLinear(frame, self.imagen(ancho, alto), m, 1.0 - m)
