"""Interfaz común de las escenas y contexto compartido."""
from __future__ import annotations

from typing import Union

import numpy as np

from core.pose import PoseFrame

SALIR = "__salir__"   # valor que una escena devuelve para cerrar el juego


class Contexto:
    """Servicios compartidos por todas las escenas (se crea una vez en main.py)."""

    def __init__(self, almacen, audio, sprites, fondo, jugador: str = "Invitado",
                 debug: bool = False, semilla: int | None = None, ajustes=None):
        from core.settings import Ajustes
        self.almacen = almacen
        self.audio = audio
        self.sprites = sprites
        self.fondo = fondo
        self.jugador = jugador
        self.debug = debug
        self.semilla = semilla          # para que viento/burbujas sean reproducibles en tests
        self.ajustes = ajustes if ajustes is not None else Ajustes()
        self.fps = 0.0                  # lo actualiza main.py (se muestra en Ajustes)

    def perfil(self) -> dict:
        """Perfil actual del jugador (se lee del almacén)."""
        return self.almacen.perfil(self.jugador)

    @property
    def animaciones(self) -> bool:
        return self.ajustes.animaciones

    def aplicar_ajustes(self) -> None:
        """Lleva los ajustes al audio y al fondo (la detección la cambia main.py)."""
        self.audio.ajustar_musica(self.ajustes.musica, self.ajustes.factor_volumen)
        self.fondo.activado = self.ajustes.fondo

    def guardar_ajustes(self) -> None:
        """Aplica y guarda en data/ajustes.json."""
        self.aplicar_ajustes()
        self.almacen.guardar_ajustes(self.ajustes)

    def elegir_jugador(self, nombre: str) -> None:
        """Cambia de jugador y lo recuerda para la próxima vez que se abra el juego."""
        self.jugador = nombre
        self.ajustes.ultimo_jugador = nombre
        self.almacen.guardar_ajustes(self.ajustes)


Transicion = Union["Scene", str, None]


class Scene:
    """Clase base. update/on_key devuelven la escena siguiente, SALIR o None."""

    con_musica = True        # False: la música de fondo se silencia en esta escena
    pista_musica = "musica"  # WAV de assets/sounds que suena de fondo en esta escena

    def __init__(self, ctx: Contexto):
        self.ctx = ctx
        self.pose: PoseFrame | None = None

    def enter(self) -> None:
        """Se llama una vez al activar la escena."""

    def update(self, pose: PoseFrame | None, dt: float) -> Transicion:
        """Avanza la lógica con la pose del frame y el dt real (s)."""
        self.pose = pose
        return None

    def on_key(self, tecla: str) -> Transicion:
        """Tecla lógica: arriba, abajo, izquierda, derecha, enter, esc, retroceso, p, f o un carácter."""
        return None

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """Dibuja sobre el frame de cámara y devuelve la imagen final."""
        return frame

    def debug_info(self) -> dict[str, str]:
        """Valores internos para el modo --debug."""
        return {}

    # -- utilidades ----------------------------------------------------------
    def fondo(self, frame: np.ndarray) -> np.ndarray:
        """Compone la carpa detrás del jugador (si hay máscara) y dibuja su esqueleto encima.

        Todas las escenas lo llaman al empezar draw(), así que el esqueleto queda
        debajo de los paneles y botones.
        """
        from ui.skeleton import dibujar_esqueleto
        mascara = self.pose.mascara if self.pose is not None else None
        frame = self.ctx.fondo.componer(frame, mascara)
        if self.ctx.ajustes.esqueleto:
            dibujar_esqueleto(frame, self.pose)
        return frame
