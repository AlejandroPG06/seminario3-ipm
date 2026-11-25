"""Confeti sencillo con numpy (posiciones, velocidades y colores vectorizados)."""
from __future__ import annotations

import cv2
import numpy as np

import config as C

COLORES = np.array([C.ROJO, C.VERDE, C.AMARILLO, C.AZUL, C.NARANJA, (200, 80, 200)], np.int32)


class Confeti:
    """Sistema de partículas que cae desde arriba con gravedad."""

    def __init__(self, semilla: int | None = None, activo: bool = True):
        self._rng = np.random.default_rng(semilla)
        self.activo = activo        # False (Ajustes → animaciones no): lanzar() no hace nada
        self.pos = np.zeros((0, 2), np.float32)
        self.vel = np.zeros((0, 2), np.float32)
        self.col = np.zeros((0,), np.int32)

    def lanzar(self, ancho: int, n: int = C.CONFETI_PARTICULAS, origen: tuple | None = None) -> None:
        """Añade n partículas (desde arriba, o en explosión desde `origen`)."""
        if not self.activo:
            return
        if origen is None:
            pos = np.stack([self._rng.uniform(0, ancho, n), self._rng.uniform(-200, 0, n)], 1)
            vel = np.stack([self._rng.uniform(-60, 60, n), self._rng.uniform(50, 200, n)], 1)
        else:
            ang = self._rng.uniform(0, 2 * np.pi, n)
            v = self._rng.uniform(150, 450, n)
            pos = np.tile(np.array(origen, np.float32), (n, 1))
            vel = np.stack([np.cos(ang) * v, np.sin(ang) * v - 200], 1)
        self.pos = np.concatenate([self.pos, pos.astype(np.float32)])
        self.vel = np.concatenate([self.vel, vel.astype(np.float32)])
        self.col = np.concatenate([self.col, self._rng.integers(0, len(COLORES), n)])

    def actualizar(self, dt: float, alto: int = C.ALTO_LIENZO) -> None:
        self.vel[:, 1] += 300 * dt
        self.pos += self.vel * dt
        vivas = self.pos[:, 1] < alto + 20
        self.pos, self.vel, self.col = self.pos[vivas], self.vel[vivas], self.col[vivas]

    def dibujar(self, frame: np.ndarray) -> None:
        for (x, y), c in zip(self.pos.astype(int), self.col):
            cv2.rectangle(frame, (x, y), (x + 8, y + 5), tuple(int(v) for v in COLORES[c]), -1)

    @property
    def activas(self) -> int:
        return len(self.pos)
