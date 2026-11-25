"""Física del funambulista en la cuerda floja (lógica pura).

El funambulista es un péndulo amortiguado con fuerza recuperadora: el
balanceo del jugador lo empuja; si su ángulo supera el máximo, cae.
"""
from __future__ import annotations

import math

import config as C
from core.geometry import zona_muerta


class CuerdaFloja:
    """Ángulo del funambulista (grados) en función del balanceo (aw)."""

    def __init__(self, ganancia: float = C.CUERDA_GANANCIA, rigidez: float = C.CUERDA_RIGIDEZ,
                 amortiguacion: float = C.CUERDA_AMORTIGUACION,
                 angulo_max: float = C.CUERDA_ANGULO_MAX, zona: float = C.ZONA_MUERTA_BALANCEO):
        self.ganancia = ganancia
        self.rigidez = rigidez
        self.amortiguacion = amortiguacion
        self.angulo_max = angulo_max
        self.zona = zona
        self.angulo = 0.0     # grados
        self.vel = 0.0        # grados/s
        self.fase = 0.0       # rad, para animar la cuerda
        self.caido = False

    def actualizar(self, balanceo: float, dt: float, viento: float = 0.0) -> bool:
        """Avanza dt segundos (viento en grados/s²). Devuelve True si ha caído."""
        if self.caido:
            return True
        pasos = max(1, math.ceil(dt / C.FISICA_PASO_MAX))
        for _ in range(pasos):
            if self._paso(balanceo, dt / pasos, viento):
                break
        return self.caido

    def _paso(self, balanceo: float, dt: float, viento: float) -> bool:
        acc = (self.ganancia * zona_muerta(balanceo, self.zona) + viento
               - self.rigidez * self.angulo - self.amortiguacion * self.vel)
        self.vel += acc * dt
        self.angulo += self.vel * dt
        self.fase += dt * 6.0
        if abs(self.angulo) > self.angulo_max:
            self.caido = True
        return self.caido

    @property
    def peligro(self) -> float:
        """0-1: lo cerca que está de caer."""
        return min(1.0, abs(self.angulo) / self.angulo_max)

    @property
    def amplitud_cuerda(self) -> float:
        """Amplitud visual de la oscilación de la cuerda (px)."""
        return min(40.0, 4.0 + abs(self.vel) * 0.6)
