"""Verificación de la postura de los pies y detección de pies movidos (lógica pura)."""
from __future__ import annotations

import numpy as np

import config as C


def separacion_pies(tobillos: np.ndarray, escala: float) -> tuple[float, float]:
    """(dx, dy) entre tobillos en anchuras de hombros. tobillos: (2, 2) en coords normalizadas."""
    escala = max(escala, 1e-6)
    dx = abs(float(tobillos[0, 0] - tobillos[1, 0])) / escala
    dy = abs(float(tobillos[0, 1] - tobillos[1, 1])) / escala
    return dx, dy


def verificar_postura(prueba: str, dx: float, dy: float) -> tuple[bool, str]:
    """Comprueba si (dx, dy) en aw encaja con la postura. Devuelve (ok, aviso)."""
    if prueba == "pies_juntos":
        if dx > C.PIES_JUNTOS_DX_MAX:
            return False, "Junta más los pies"
        return True, ""
    if prueba == "semitandem":
        if dx > C.SEMITANDEM_DX_MAX:
            return False, "Acerca los pies: talón junto al dedo gordo"
        if dy < C.SEMITANDEM_DY_MIN:
            return False, "Adelanta un poco un pie"
        return True, ""
    if prueba == "tandem":
        if dx > C.TANDEM_DX_MAX:
            return False, "Pon un pie justo delante del otro"
        if dy < C.TANDEM_DY_MIN:
            return False, "Adelanta un pie: talón con punta"
        return True, ""
    return True, ""


class VigilantePies:
    """Detecta si algún tobillo se aleja de su posición inicial (el jugador ha movido los pies)."""

    def __init__(self, tobillos_ref: np.ndarray, escala: float,
                 umbral: float = C.PIES_MOVIDOS_MAX, frames: int = C.PIES_MOVIDOS_FRAMES):
        self.ref = np.asarray(tobillos_ref, dtype=np.float32).copy()
        self.escala = max(escala, 1e-6)
        self.umbral = umbral
        self.frames = frames
        self._contador = 0
        self.desplazamiento = 0.0   # aw, último desplazamiento máximo

    def actualizar(self, tobillos: np.ndarray) -> bool:
        """True si los pies se han movido durante varios frames seguidos."""
        d = np.linalg.norm(np.asarray(tobillos, np.float32) - self.ref, axis=1)
        self.desplazamiento = float(d.max() / self.escala)
        self._contador = self._contador + 1 if self.desplazamiento > self.umbral else 0
        return self._contador >= self.frames
