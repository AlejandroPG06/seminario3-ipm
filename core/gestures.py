"""Gestos sin teclado: brazos arriba y posición de las manos para el dwell."""
from __future__ import annotations

import config as C
from core.pose import PoseFrame


def brazos_arriba(pose: PoseFrame | None) -> bool:
    """True si las dos muñecas están claramente por encima de la nariz."""
    if pose is None or not pose.visibles((C.MUNECA_IZQ, C.MUNECA_DER, C.NARIZ)):
        return False
    limite = pose.p(C.NARIZ)[1] - C.BRAZOS_ARRIBA_MARGEN
    return pose.p(C.MUNECA_IZQ)[1] < limite and pose.p(C.MUNECA_DER)[1] < limite


class DetectorBrazosArriba:
    """Dispara una vez cuando se mantienen los brazos arriba; se rearma al bajarlos."""

    def __init__(self, duracion_s: float = C.BRAZOS_ARRIBA_S):
        self.duracion_s = duracion_s
        self._t = 0.0
        self._armado = True

    @property
    def progreso(self) -> float:
        return min(1.0, self._t / self.duracion_s)

    def actualizar(self, pose: PoseFrame | None, dt: float) -> bool:
        """Devuelve True en el frame en que se completa el gesto."""
        if brazos_arriba(pose):
            self._t += dt
            if self._armado and self._t >= self.duracion_s:
                self._armado = False
                return True
        else:
            self._t = 0.0
            self._armado = True
        return False


def manos_px(pose: PoseFrame | None) -> list[tuple[int, int]]:
    """Posiciones en píxeles de los índices visibles (para botones con dwell)."""
    if pose is None:
        return []
    return [pose.px(i) for i in (C.INDICE_IZQ, C.INDICE_DER) if pose.vis(i) >= C.VISIBILIDAD_MIN]
