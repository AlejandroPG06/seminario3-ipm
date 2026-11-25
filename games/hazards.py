"""Peligros y tareas extra de los niveles: ráfagas de viento y burbujas (doble tarea)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import config as C


class Viento:
    """Ráfagas de seno de duración fija, con dirección e intervalo aleatorios."""

    def __init__(self, fuerza: float, rng: np.random.Generator | None = None,
                 intervalo: tuple[float, float] = C.VIENTO_INTERVALO_S,
                 duracion: float = C.VIENTO_DURACION_S):
        self.fuerza = fuerza
        self.rng = rng or np.random.default_rng()
        self.intervalo = intervalo
        self.duracion = duracion
        self._espera = float(self.rng.uniform(*intervalo))
        self._t_rafaga = -1.0     # <0: no hay ráfaga
        self.direccion = 1
        self.valor = 0.0
        self.nueva_rafaga = False

    def actualizar(self, dt: float) -> float:
        """Devuelve la fuerza actual del viento (con signo)."""
        self.nueva_rafaga = False
        if self.fuerza == 0:
            self.valor = 0.0
            return 0.0
        if self._t_rafaga < 0:
            self._espera -= dt
            if self._espera <= 0:
                self._t_rafaga = 0.0
                self.direccion = int(self.rng.choice([-1, 1]))
                self.nueva_rafaga = True
        else:
            self._t_rafaga += dt
            if self._t_rafaga >= self.duracion:
                self._t_rafaga = -1.0
                self._espera = float(self.rng.uniform(*self.intervalo))
        if self._t_rafaga >= 0:
            self.valor = self.direccion * self.fuerza * math.sin(math.pi * self._t_rafaga / self.duracion)
        else:
            self.valor = 0.0
        return self.valor

    @property
    def activa(self) -> bool:
        return self._t_rafaga >= 0


@dataclass
class Burbuja:
    x: float        # px
    y: float        # px
    vida: float     # s restantes


class Burbujas:
    """Genera burbujas al alcance de la mano y cuenta las que se tocan (coordenadas en px)."""

    def __init__(self, rng: np.random.Generator | None = None, intervalo: float = C.BURBUJA_INTERVALO_S,
                 vida: float = C.BURBUJA_VIDA_S, alcance: tuple[float, float] = C.BURBUJA_ALCANCE):
        self.rng = rng or np.random.default_rng()
        self.intervalo = intervalo
        self.vida = vida
        self.alcance = alcance
        self.items: list[Burbuja] = []
        self._espera = 1.0
        self.tocadas = 0

    def actualizar(self, dt: float, manos: list[tuple[float, float]], hombros: tuple[float, float],
                   aw_px: float, radio_px: float, ancho: int, alto: int) -> list[Burbuja]:
        """Avanza el tiempo, crea burbujas cerca de los hombros y devuelve las tocadas este frame."""
        self._espera -= dt
        if self._espera <= 0:
            self._espera = self.intervalo
            ang = self.rng.uniform(math.radians(200), math.radians(340))   # mitad superior
            dist = self.rng.uniform(*self.alcance) * aw_px
            x = float(np.clip(hombros[0] + math.cos(ang) * dist, radio_px, ancho - radio_px))
            y = float(np.clip(hombros[1] + math.sin(ang) * dist, radio_px, alto - radio_px))
            self.items.append(Burbuja(x, y, self.vida))
        tocadas = []
        for b in self.items:
            b.vida -= dt
            if any(math.hypot(m[0] - b.x, m[1] - b.y) < radio_px * 1.2 for m in manos):
                tocadas.append(b)
                b.vida = 0
        self.items = [b for b in self.items if b.vida > 0]
        self.tocadas += len(tocadas)
        return tocadas
