"""Fuentes de imagen: webcam, archivo de vídeo o frames negros sintéticos."""
from __future__ import annotations

import sys

import cv2
import numpy as np

import config as C


def ajustar_frame(frame: np.ndarray, alto: int = C.ALTO_LIENZO) -> np.ndarray:
    """Voltea en espejo y reescala a la altura del lienzo manteniendo la proporción."""
    frame = cv2.flip(frame, 1)
    h, w = frame.shape[:2]
    if h != alto:
        ancho = int(round(w * alto / h))
        frame = cv2.resize(frame, (ancho, alto), interpolation=cv2.INTER_LINEAR)
    return frame


class FuenteCamara:
    """Webcam (indice) o archivo de vídeo (ruta). Los vídeos se reproducen en bucle."""

    def __init__(self, camara: int = 0, video: str | None = None,
                 ancho: int = C.CAMARA_ANCHO_PEDIDO, alto: int = C.CAMARA_ALTO_PEDIDO,
                 formato: str = C.CAMARA_FORMATO):
        self.es_video = video is not None
        if self.es_video:
            self._cap = cv2.VideoCapture(video)
        else:
            backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
            self._cap = cv2.VideoCapture(camara, backend)
            configurar_camara(self._cap, ancho, alto, formato)
        if not self._cap.isOpened():
            origen = video if self.es_video else f"cámara {camara}"
            raise RuntimeError(f"No se pudo abrir la fuente de vídeo: {origen}")

    def leer(self) -> np.ndarray | None:
        """Devuelve el siguiente frame ajustado, o None si falla la cámara."""
        ok, frame = self._cap.read()
        if not ok and self.es_video:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
        return ajustar_frame(frame) if ok else None

    def descripcion(self) -> str:
        return "vídeo" if self.es_video else describir(self._cap)

    def cerrar(self) -> None:
        self._cap.release()


def configurar_camara(cap: cv2.VideoCapture, ancho: int, alto: int, formato: str) -> None:
    """Pide formato, resolución y buffer mínimo (el orden importa en V4L2: formato primero)."""
    if formato:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*formato))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)


def describir(cap: cv2.VideoCapture) -> str:
    """Resolución y formato que la cámara ha aceptado realmente."""
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, "little").decode(errors="replace")
    return f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} {fourcc}"


class FuenteSintetica:
    """Frames negros 16:9 para ejecutar sin cámara (modo headless y pruebas)."""

    def __init__(self, ancho: int = 1280, alto: int = C.ALTO_LIENZO):
        self._frame = np.zeros((alto, ancho, 3), dtype=np.uint8)
        self.es_video = True

    def leer(self) -> np.ndarray:
        return self._frame.copy()

    def cerrar(self) -> None:
        pass
