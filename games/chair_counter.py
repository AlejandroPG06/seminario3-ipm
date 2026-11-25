"""Contador de levantadas de la silla: máquina de estados con histéresis (lógica pura).

SENTADO → SUBIENDO → DE_PIE → BAJANDO → SENTADO. Una repetición cuenta al
llegar a DE_PIE habiendo partido de SENTADO.
"""
from __future__ import annotations

from dataclasses import dataclass

import config as C

SENTADO, SUBIENDO, DE_PIE, BAJANDO = "SENTADO", "SUBIENDO", "DE_PIE", "BAJANDO"


@dataclass
class Repeticion:
    """Una levantada: duración de la subida (s), apoyo de manos y valoración."""
    duracion_subida: float
    manos: bool
    calidad: str              # "Perfecta", "Buena" o "Incompleta"
    t: float                  # s desde el inicio del contador


class ContadorSilla:
    """Cuenta repeticiones a partir del ángulo de rodilla (grados)."""

    def __init__(self, angulo_de_pie: float = C.SILLA_ANGULO_DE_PIE,
                 angulo_subiendo: float = C.SILLA_ANGULO_SUBIENDO,
                 angulo_sentado: float = C.SILLA_ANGULO_SENTADO,
                 angulo_bajando: float = C.SILLA_ANGULO_BAJANDO,
                 subida_perfecta_s: float = C.SILLA_SUBIDA_PERFECTA_S,
                 manos_invalida: bool = False):
        self.angulo_de_pie = angulo_de_pie
        self.angulo_subiendo = angulo_subiendo
        self.angulo_sentado = angulo_sentado
        self.angulo_bajando = angulo_bajando
        self.subida_perfecta_s = subida_perfecta_s
        self.manos_invalida = manos_invalida
        self.estado: str | None = None
        self.t = 0.0
        self.repeticiones: list[Repeticion] = []
        self.incompletas: list[Repeticion] = []
        self._t_inicio_subida = 0.0
        self._manos = False

    @property
    def cuenta(self) -> int:
        return len(self.repeticiones)

    def actualizar(self, angulo_rodilla: float, dt: float, manos_en_rodillas: bool = False) -> Repeticion | None:
        """Procesa un frame. Devuelve la Repeticion (válida o incompleta) si termina una subida."""
        self.t += dt
        a = angulo_rodilla
        if self.estado is None:
            self.estado = SENTADO if a < self.angulo_bajando else DE_PIE
            return None
        if self.estado == SENTADO:
            if a > self.angulo_subiendo:
                self.estado = SUBIENDO
                self._t_inicio_subida = self.t
                self._manos = manos_en_rodillas
        elif self.estado == SUBIENDO:
            self._manos = self._manos or manos_en_rodillas
            if a >= self.angulo_de_pie:
                self.estado = DE_PIE
                return self._cerrar_repeticion()
            if a < self.angulo_sentado:
                self.estado = SENTADO
                rep = Repeticion(self.t - self._t_inicio_subida, self._manos, "Incompleta", self.t)
                self.incompletas.append(rep)
                return rep
        elif self.estado == DE_PIE:
            if a < self.angulo_bajando:
                self.estado = BAJANDO
        elif self.estado == BAJANDO:
            if a < self.angulo_sentado:
                self.estado = SENTADO
            elif a >= self.angulo_de_pie:
                self.estado = DE_PIE
        return None

    def _cerrar_repeticion(self) -> Repeticion:
        dur = self.t - self._t_inicio_subida
        if self._manos and self.manos_invalida:
            rep = Repeticion(dur, True, "Incompleta", self.t)
            self.incompletas.append(rep)
            return rep
        calidad = "Perfecta" if (dur <= self.subida_perfecta_s and not self._manos) else "Buena"
        rep = Repeticion(dur, self._manos, calidad, self.t)
        self.repeticiones.append(rep)
        return rep
