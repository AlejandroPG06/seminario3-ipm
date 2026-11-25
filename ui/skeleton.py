"""Esqueleto del jugador detectado por el Pose Landmarker (33 puntos y sus conexiones).

Se dibuja en todas las pantallas, justo después del fondo y antes de la
interfaz, para que se vea en todo momento lo que detecta el modelo de visión.
"""
from __future__ import annotations

import cv2
import numpy as np

import config as C

_CONEXIONES: list[tuple[int, int]] | None = None


def conexiones() -> list[tuple[int, int]]:
    """mp.solutions.pose.POSE_CONNECTIONS (se importa una sola vez)."""
    global _CONEXIONES
    if _CONEXIONES is None:
        try:
            import mediapipe as mp
            _CONEXIONES = sorted(mp.solutions.pose.POSE_CONNECTIONS)
        except Exception:  # noqa: BLE001 - sin mediapipe: tronco y extremidades a mano
            _CONEXIONES = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24),
                           (23, 25), (25, 27), (24, 26), (26, 28), (27, 29), (29, 31), (27, 31),
                           (28, 30), (30, 32), (28, 32)]
    return _CONEXIONES


def dibujar_esqueleto(frame: np.ndarray, pose) -> None:
    """Líneas entre landmarks visibles y un punto en cada articulación (grosor según el tamaño)."""
    if pose is None:
        return
    H = frame.shape[0]
    g = max(2, int(H * C.ESQUELETO_GROSOR))
    puntos = [pose.px(i) for i in range(len(pose.lm))]
    visible = [pose.vis(i) >= C.VISIBILIDAD_MIN for i in range(len(pose.lm))]
    for a, b in conexiones():
        if a < len(puntos) and b < len(puntos) and visible[a] and visible[b]:
            cara = a <= 10 and b <= 10
            cv2.line(frame, puntos[a], puntos[b], C.ESQUELETO_COLOR, max(1, g // 2) if cara else g, cv2.LINE_AA)
    for i, (p, v) in enumerate(zip(puntos, visible)):
        if v:
            r = max(2, g - 1) if i <= 10 else g + 2
            cv2.circle(frame, p, r, C.ESQUELETO_PUNTO, -1, cv2.LINE_AA)
            cv2.circle(frame, p, r, (40, 40, 40), 1, cv2.LINE_AA)
