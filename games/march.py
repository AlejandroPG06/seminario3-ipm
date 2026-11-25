"""Contador de pasos de la marcha en el sitio (lógica pura).

La elevación de cada rodilla va de 0 (posición de reposo, de pie) a 1 (a la
altura de la cadera). Un paso cuenta cuando la rodilla supera MARCHA_SUBIDA
(la mitad, como en el 2-Minute Step Test) y se rearma al bajar de
MARCHA_BAJADA (histéresis). Opcionalmente se marca si el paso cae al compás.
"""
from __future__ import annotations

from dataclasses import dataclass

import config as C


@dataclass
class Paso:
    pierna: str           # "izq" o "der" (del jugador)
    t: float              # s desde el inicio
    al_compas: bool


def elevacion(y_rodilla: float, y_rodilla_reposo: float, y_cadera_reposo: float) -> float:
    """0 = rodilla en reposo, 1 = rodilla a la altura de la cadera (y crece hacia abajo)."""
    recorrido = y_rodilla_reposo - y_cadera_reposo
    if recorrido <= 1e-6:
        return 0.0
    return (y_rodilla_reposo - y_rodilla) / recorrido


class ContadorMarcha:
    """Cuenta pasos por pierna con histéresis y valora el ritmo si hay tempo."""

    def __init__(self, tempo_bpm: float = 0.0, subida: float = C.MARCHA_SUBIDA,
                 bajada: float = C.MARCHA_BAJADA, tolerancia_s: float = C.MARCHA_TOLERANCIA_S):
        self.tempo_bpm = tempo_bpm
        self.subida = subida
        self.bajada = bajada
        self.tolerancia_s = tolerancia_s
        self.t = 0.0
        self.arriba = {"izq": False, "der": False}
        self.pasos: list[Paso] = []

    @property
    def periodo(self) -> float:
        """s entre pulsos del ritmo (0 si es libre)."""
        return 60.0 / self.tempo_bpm if self.tempo_bpm > 0 else 0.0

    @property
    def total(self) -> int:
        return len(self.pasos)

    @property
    def pasos_der(self) -> int:
        """Pasos de la rodilla derecha: es lo que cuenta el 2-Minute Step Test."""
        return sum(1 for p in self.pasos if p.pierna == "der")

    @property
    def al_compas(self) -> int:
        return sum(1 for p in self.pasos if p.al_compas)

    def fase_pulso(self) -> float:
        """0-1 dentro del pulso actual (para animar el metrónomo)."""
        return (self.t % self.periodo) / self.periodo if self.periodo else 0.0

    def _en_compas(self) -> bool:
        if not self.periodo:
            return False
        resto = self.t % self.periodo
        return min(resto, self.periodo - resto) <= self.tolerancia_s

    def actualizar(self, elev_izq: float, elev_der: float, dt: float) -> list[Paso]:
        """Procesa un frame y devuelve los pasos nuevos."""
        self.t += dt
        nuevos = []
        for pierna, elev in (("izq", elev_izq), ("der", elev_der)):
            if not self.arriba[pierna] and elev >= self.subida:
                self.arriba[pierna] = True
                paso = Paso(pierna, self.t, self._en_compas())
                self.pasos.append(paso)
                nuevos.append(paso)
            elif self.arriba[pierna] and elev < self.bajada:
                self.arriba[pierna] = False
        return nuevos
