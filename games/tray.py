"""Física de la bandeja con vaso u objetos apilados (lógica pura).

Unidades: la posición x del objeto va en «medias bandejas» (-1 a 1 es la
bandeja); el balanceo de entrada va en anchuras de hombros (aw).
"""
from __future__ import annotations

import math

import config as C
from core.geometry import limitar, zona_muerta


class Bandeja:
    """Bandeja que se inclina con el balanceo; los objetos se deslizan y pueden caer."""

    def __init__(self, objetos: int = 1,
                 ganancia: float = C.BANDEJA_GANANCIA,
                 inclinacion_max: float = C.BANDEJA_INCLINACION_MAX,
                 gravedad: float = C.BANDEJA_GRAVEDAD,
                 rozamiento: float = C.BANDEJA_ROZAMIENTO,
                 zona: float = C.ZONA_MUERTA_BALANCEO):
        self.objetos = max(1, objetos)
        extra = self.objetos - 1
        self.inercia = 1.0 + C.BANDEJA_INERCIA_POR_OBJETO * extra
        self.borde = max(0.3, C.BANDEJA_BORDE - C.BANDEJA_BORDE_POR_OBJETO * extra)
        self.ganancia = ganancia
        self.inclinacion_max = inclinacion_max
        self.gravedad = gravedad
        self.rozamiento = rozamiento
        self.zona = zona
        self.x = 0.0             # posición de la pila (medias bandejas)
        self.v = 0.0             # velocidad (medias bandejas/s)
        self.inclinacion = 0.0   # grados, positivo = baja por la derecha de la pantalla
        self.caido = False

    def actualizar(self, balanceo: float, dt: float, viento: float = 0.0) -> bool:
        """Avanza dt segundos. balanceo en aw (positivo = derecha). Devuelve True si se ha caído."""
        if self.caido:
            return True
        pasos = max(1, math.ceil(dt / C.FISICA_PASO_MAX))
        for _ in range(pasos):
            if self._paso(balanceo, dt / pasos, viento):
                break
        return self.caido

    def _paso(self, balanceo: float, dt: float, viento: float) -> bool:
        self.inclinacion = limitar(self.ganancia * zona_muerta(balanceo, self.zona),
                                   -self.inclinacion_max, self.inclinacion_max)
        a = (self.gravedad * math.sin(math.radians(self.inclinacion)) + viento) / self.inercia
        self.v += a * dt
        self.v *= math.exp(-self.rozamiento / self.inercia * dt)
        if self.inclinacion == 0.0 and viento == 0.0 and abs(self.v) < C.BANDEJA_VEL_REPOSO:
            self.v = 0.0
        self.x += self.v * dt
        if abs(self.x) > self.borde:
            self.caido = True
        return self.caido

    @property
    def peligro(self) -> float:
        """0-1: lo cerca que está la pila del borde."""
        return min(1.0, abs(self.x) / self.borde)

    @property
    def inclinacion_pila(self) -> float:
        """Grados extra que se tuerce la pila al moverse (solo visual)."""
        return limitar(self.v * 25.0, -25.0, 25.0)
