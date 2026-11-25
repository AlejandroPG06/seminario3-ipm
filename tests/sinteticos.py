"""Poses sintéticas para tests (coordenadas normalizadas, ya en espejo)."""
from __future__ import annotations

import math

import numpy as np

from core.pose import PoseFrame

ANCHO, ALTO = 1280, 720
ASPECTO = ANCHO / ALTO


def _a_norm(puntos_q: dict, vis: float) -> np.ndarray:
    """Convierte puntos isótropos (altos de imagen) a landmarks normalizados (x / aspecto)."""
    lm = np.full((33, 3), [0.5, 0.5, vis], dtype=np.float32)
    for i, (x, y) in puntos_q.items():
        lm[i, 0], lm[i, 1] = x / ASPECTO, y
    return lm


def pose_de_pie(dx_cadera: float = 0.0, brazos_arriba: bool = False, sep_pies: float = 0.045,
                adelanto_pie: float = 0.0, mascara: bool = False, vis: float = 0.95,
                elev_izq: float = 0.0, elev_der: float = 0.0) -> PoseFrame:
    """Persona de pie de frente con proporciones reales (hombros/torso ≈ 0,73) en 16:9.

    dx_cadera desplaza tronco y cadera (no los pies) en x NORMALIZADA (fracción del ancho).
    sep_pies y adelanto_pie van en altos de imagen. elev_izq/elev_der levantan la rodilla
    (y el pie) de cada pierna: 0 = reposo, 1 = rodilla a la altura de la cadera.
    """
    cx = 0.5 * ASPECTO
    d = dx_cadera * ASPECTO
    q = {
        0: (cx + d, 0.15),
        11: (cx + 0.08 + d, 0.28), 12: (cx - 0.08 + d, 0.28),
        13: (cx + 0.10 + d, 0.39), 14: (cx - 0.10 + d, 0.39),
        15: (cx + 0.105 + d, 0.49), 16: (cx - 0.105 + d, 0.49),
        19: (cx + 0.11 + d, 0.52), 20: (cx - 0.11 + d, 0.52),
        23: (cx + 0.05 + d, 0.50), 24: (cx - 0.05 + d, 0.50),
        25: (cx + 0.045 + d / 2, 0.69), 26: (cx - 0.045 + d / 2, 0.69),
        27: (cx + sep_pies / 2, 0.87 + adelanto_pie), 28: (cx - sep_pies / 2, 0.87),
        29: (cx + sep_pies / 2, 0.885 + adelanto_pie), 30: (cx - sep_pies / 2, 0.885),
        31: (cx + sep_pies / 2, 0.90 + adelanto_pie), 32: (cx - sep_pies / 2, 0.90),
    }
    for e, idx in ((elev_izq, (25, 27, 29, 31)), (elev_der, (26, 28, 30, 32))):
        subida = e * (0.69 - 0.50)
        for i in idx:
            q[i] = (q[i][0], q[i][1] - subida)
    if brazos_arriba:
        q.update({13: (cx + 0.11 + d, 0.18), 14: (cx - 0.11 + d, 0.18), 15: (cx + 0.11 + d, 0.05),
                  16: (cx - 0.11 + d, 0.05), 19: (cx + 0.11 + d, 0.03), 20: (cx - 0.11 + d, 0.03)})
    m = np.full((ALTO, ANCHO), 0.0, np.float32) if mascara else None
    if m is not None:
        m[:, ANCHO // 3: 2 * ANCHO // 3] = 1.0
    return PoseFrame(_a_norm(q, vis), m, 0, ANCHO, ALTO)


def pose_sentado_lado(angulo_rodilla: float, manos_rodilla: bool = False) -> PoseFrame:
    """Persona de lado (pierna izquierda visible) con el ángulo de rodilla REAL dado (grados)."""
    cx = 0.5 * ASPECTO
    rodilla = np.array([cx + 0.08, 0.70])
    tobillo = np.array([cx + 0.08, 0.88])
    giro = math.radians(180.0 - angulo_rodilla)
    direccion = np.array([-math.sin(giro), -math.cos(giro)])
    cadera = rodilla + 0.17 * direccion
    hombro = cadera + np.array([0.0, -0.22])
    q = {
        0: hombro + (0.03, -0.08),
        11: hombro + (0.01, 0), 12: hombro - (0.01, 0),
        13: hombro + (0.05, 0.08), 14: hombro + (0.05, 0.08),
        15: hombro + (0.07, 0.10), 16: hombro + (0.05, 0.11),
        19: hombro + (0.08, 0.10), 20: hombro + (0.06, 0.11),
        23: cadera, 24: cadera, 25: rodilla, 26: rodilla, 27: tobillo, 28: tobillo,
        29: tobillo + (-0.03, 0.01), 30: tobillo + (-0.03, 0.01),
        31: tobillo + (0.06, 0.02), 32: tobillo + (0.06, 0.02),
    }
    if manos_rodilla:
        q[15] = rodilla + (0.0, -0.01)
        q[16] = rodilla + (0.0, -0.01)
    lm = _a_norm(q, 0.95)
    for i in (24, 26, 28, 30, 32):   # lado derecho peor visto
        lm[i, 2] = 0.6
    return PoseFrame(lm, None, 0, ANCHO, ALTO)


def ciclos_rodilla(n: int, periodo_s: float = 2.0, dt: float = 1 / 30, minimo: float = 90.0,
                   maximo: float = 175.0, ruido: float = 0.0, semilla: int = 0) -> list[float]:
    """Ángulos de rodilla de n ciclos sentado→de pie→sentado (coseno), con ruido opcional."""
    rng = np.random.default_rng(semilla)
    pasos = int(round(n * periodo_s / dt))
    t = np.arange(pasos) * dt
    a = minimo + (maximo - minimo) * (1 - np.cos(2 * np.pi * t / periodo_s)) / 2
    return list(a + rng.normal(0, ruido, pasos)) + [minimo] * 10
