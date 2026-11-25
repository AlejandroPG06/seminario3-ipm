"""Física del funambulista en la cuerda floja (lógica pura). También la usa la bailarina.

El funambulista es un péndulo amortiguado: el balanceo del jugador lo empuja.
Con `inestabilidad` = 0 una fuerza recuperadora lo devuelve al centro (fácil).
Con `inestabilidad` > CUERDA_RIGIDEZ se comporta como un péndulo invertido:
si nadie lo corrige, se va cayendo solo hacia el lado al que esté inclinado, y
el jugador tiene que compensar moviendo un poco la cadera hacia el otro lado.
Un temblor aleatorio pequeño evita que se quede quieto en el equilibrio exacto.
Si el ángulo supera el máximo, cae.
"""
from __future__ import annotations

import math

import numpy as np

import config as C
from core.geometry import zona_muerta


class CuerdaFloja:
    """Ángulo del funambulista (grados) en función del balanceo (aw)."""

    def __init__(self, ganancia: float = C.CUERDA_GANANCIA, rigidez: float = C.CUERDA_RIGIDEZ,
                 amortiguacion: float = C.CUERDA_AMORTIGUACION,
                 angulo_max: float = C.CUERDA_ANGULO_MAX, zona: float = C.ZONA_MUERTA_BALANCEO,
                 inestabilidad: float = 0.0, temblor: float | None = None,
                 rng: np.random.Generator | None = None):
        self.ganancia = ganancia
        self.rigidez = rigidez
        self.inestabilidad = inestabilidad    # 1/s², empuja hacia fuera (péndulo invertido)
        self.amortiguacion = amortiguacion
        self.angulo_max = angulo_max
        self.zona = zona
        if temblor is None:
            temblor = C.CUERDA_TEMBLOR if inestabilidad > 0 else 0.0
        self.temblor = temblor                # grados/s², intensidad de la perturbación aleatoria
        self.rng = rng or np.random.default_rng()
        self._perturbacion = 0.0
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
        if self.temblor > 0:      # ruido de Ornstein-Uhlenbeck: cambia suavemente de lado
            tau = C.CUERDA_TEMBLOR_TAU_S
            self._perturbacion += (-self._perturbacion / tau * dt
                                   + self.temblor * math.sqrt(2 * dt / tau) * float(self.rng.normal()))
        acc = (self.ganancia * zona_muerta(balanceo, self.zona) + viento + self._perturbacion
               + (self.inestabilidad - self.rigidez) * self.angulo - self.amortiguacion * self.vel)
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
    def correccion(self) -> int:
        """Hacia dónde debe mover la cadera el jugador para enderezarlo (-1, 0 o 1), con margen."""
        if abs(self.angulo) < self.angulo_max * C.CUERDA_AVISO_PELIGRO:
            return 0
        return -1 if self.angulo > 0 else 1

    @property
    def amplitud_cuerda(self) -> float:
        """Amplitud visual de la oscilación de la cuerda (px)."""
        return min(40.0, 4.0 + abs(self.vel) * 0.6)
