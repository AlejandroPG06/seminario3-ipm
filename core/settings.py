"""Ajustes del jugador que se recuerdan entre partidas (data/ajustes.json).

Lógica pura: solo datos y conversión a/desde dict. La lectura y escritura del
archivo la hace core.storage.Almacen.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

import config as C


@dataclass
class Ajustes:
    """Preferencias de sonido, gráficos y el último jugador elegido."""
    musica: bool = True                 # música de fondo (también con la tecla M)
    volumen_musica: int = 50            # %, 0-100 (50 % = config.VOLUMEN_MUSICA)
    fondo: bool = True                  # carpa de circo detrás del jugador (segmentación)
    animaciones: bool = True            # confeti y otras animaciones decorativas
    deteccion_rapida: bool = False      # modelo «lite» de MediaPipe: más fps, algo menos preciso
    esqueleto: bool = True              # dibujar los landmarks y conexiones detectados
    ultimo_jugador: str = "Invitado"    # se elige solo al volver a abrir el juego

    @classmethod
    def desde_dict(cls, datos: dict | None) -> "Ajustes":
        """Ajustes a partir de un dict leído del JSON; ignora claves desconocidas o con tipo erróneo."""
        aj = cls()
        for f in fields(cls):
            if datos and f.name in datos and isinstance(datos[f.name], type(getattr(aj, f.name))):
                setattr(aj, f.name, datos[f.name])
        aj.volumen_musica = limitar_volumen(aj.volumen_musica)
        return aj

    def a_dict(self) -> dict:
        return asdict(self)

    @property
    def factor_volumen(self) -> float:
        """Volumen de la música para el mezclador (0-1)."""
        return C.VOLUMEN_MUSICA_MAX * self.volumen_musica / 100.0

    def cambiar_volumen(self, pasos: int) -> int:
        """Sube (pasos > 0) o baja el volumen en múltiplos de AJUSTES_VOLUMEN_PASO. Devuelve el nuevo %."""
        self.volumen_musica = limitar_volumen(self.volumen_musica + pasos * C.AJUSTES_VOLUMEN_PASO)
        return self.volumen_musica


def limitar_volumen(pct: int) -> int:
    return int(max(0, min(100, pct)))
