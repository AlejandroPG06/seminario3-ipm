"""Funciones geométricas puras sobre puntos 2D normalizados (sin cv2 ni mediapipe)."""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

Punto = Sequence[float]


def distancia(a: Punto, b: Punto) -> float:
    """Distancia euclídea entre dos puntos 2D."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def punto_medio(a: Punto, b: Punto) -> np.ndarray:
    """Punto medio entre dos puntos 2D."""
    return np.array([(a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0])


def angulo(a: Punto, b: Punto, c: Punto) -> float:
    """Ángulo ABC en grados (0-180), con vértice en b. Devuelve 0 si hay puntos coincidentes."""
    v1 = (a[0] - b[0], a[1] - b[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    coseno = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, coseno))))


def normalizar(valor: float, escala: float) -> float:
    """Divide un valor por una escala (p. ej. anchura de hombros), protegiendo contra 0."""
    if abs(escala) < 1e-9:
        return 0.0
    return valor / escala


def zona_muerta(valor: float, umbral: float) -> float:
    """Anula |valor| < umbral y resta el umbral al resto (continua en ±umbral)."""
    if abs(valor) <= umbral:
        return 0.0
    return valor - math.copysign(umbral, valor)


def ema(anterior: float | None, nuevo: float, alfa: float) -> float:
    """Media móvil exponencial; si no hay valor anterior devuelve el nuevo."""
    if anterior is None:
        return nuevo
    return alfa * nuevo + (1.0 - alfa) * anterior


def limitar(valor: float, minimo: float, maximo: float) -> float:
    """Recorta un valor al intervalo [minimo, maximo]."""
    return max(minimo, min(maximo, valor))
