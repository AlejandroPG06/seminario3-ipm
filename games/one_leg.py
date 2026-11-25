"""Detección del equilibrio sobre una pierna (lógica pura).

Con cámara frontal, el pie levantado se ve como un tobillo claramente más
alto que el otro. Hay histéresis: el pie cuenta como levantado por encima de
UNA_PIERNA_LEVANTADO y como apoyado por debajo de UNA_PIERNA_APOYADO durante
varios frames seguidos.
"""
from __future__ import annotations

import config as C

DOS_PIES, UNA_PIERNA, APOYADO = "DOS_PIES", "UNA_PIERNA", "APOYADO"


class DetectorUnaPierna:
    """DOS_PIES → UNA_PIERNA (pie levantado) → APOYADO (el pie vuelve al suelo: fin)."""

    def __init__(self, levantado: float = C.UNA_PIERNA_LEVANTADO,
                 apoyado: float = C.UNA_PIERNA_APOYADO, frames: int = C.UNA_PIERNA_APOYO_FRAMES):
        self.umbral_levantado = levantado
        self.umbral_apoyado = apoyado
        self.frames = frames
        self.estado = DOS_PIES
        self.pie_levantado = ""        # "izq" o "der" (pie del jugador)
        self.diferencia = 0.0          # aw, positivo = el tobillo izquierdo está más alto
        self._abajo = 0

    @property
    def levantado(self) -> bool:
        return self.estado == UNA_PIERNA

    def actualizar(self, y_tobillo_izq: float, y_tobillo_der: float, escala: float) -> str:
        """y en coordenadas de imagen (crece hacia abajo); escala = anchura de hombros. Devuelve el estado."""
        self.diferencia = (y_tobillo_der - y_tobillo_izq) / max(escala, 1e-6)
        alto = abs(self.diferencia)
        if self.estado == DOS_PIES:
            if alto > self.umbral_levantado:
                self.estado = UNA_PIERNA
                self.pie_levantado = "izq" if self.diferencia > 0 else "der"
                self._abajo = 0
        elif self.estado == UNA_PIERNA:
            self._abajo = self._abajo + 1 if alto < self.umbral_apoyado else 0
            if self._abajo >= self.frames:
                self.estado = APOYADO
        return self.estado
