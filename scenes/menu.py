"""Menú principal y selección/creación de jugador."""
from __future__ import annotations

import numpy as np

import config as C
from core.gestures import manos_px
from scenes.base import SALIR, Scene, Transicion
from ui.dwell_button import BotonDwell, MenuDwell, dibujar_manos
from ui.hud import titulo
from ui.text import panel, texto

ALIAS_TECLAS = {"w": "arriba", "s": "abajo", "a": "izquierda", "d": "derecha"}


class EscenaMenu(Scene):
    """Menú principal: modos de juego, información de la SPPB, historial, jugador, ajustes y salir."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.menu: MenuDwell | None = None

    def _crear_menu(self, ancho: int, alto: int) -> None:
        opciones = [
            ("Modo Evaluación", "evaluacion"),
            ("Modo Aventura", "aventura"),
            ("Modo Práctica", "practica"),
            ("Info SPPB", "info", {"icono": "info"}),
            ("Historial", "historial"),
            (f"Jugador: {self.ctx.jugador}", "jugador"),
            ("Ajustes", "ajustes", {"icono": "ajustes"}),
            ("Salir", "salir"),
        ]
        self.menu = MenuDwell.laterales(opciones, ancho, alto)
        t, m = C.MENU_TROFEO_TAM, C.MENU_TROFEO_MARGEN      # trofeo pequeño, sin texto, abajo a la derecha
        self.menu.botones.append(BotonDwell((ancho - m - t, alto - m - t, t, t), "", "logros", icono="trofeo"))

    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        if self.menu is None:
            return None
        accion = self.menu.actualizar(manos_px(pose), dt)
        return self._ejecutar(accion)

    def on_key(self, tecla: str) -> Transicion:
        if tecla == "esc":
            return SALIR
        if self.menu is None:
            return None
        return self._ejecutar(self.menu.tecla(ALIAS_TECLAS.get(tecla, tecla)))

    def _ejecutar(self, accion: str | None) -> Transicion:
        if accion is None:
            return None
        self.ctx.audio.reproducir("click")
        if accion == "salir":
            return SALIR
        if accion == "evaluacion":
            from scenes.flows import FlujoEvaluacion
            return FlujoEvaluacion(self.ctx).iniciar()
        if accion == "aventura":
            from scenes.flows import FlujoAventura
            return FlujoAventura(self.ctx).mapa()
        if accion == "practica":
            from scenes.flows import FlujoPractica
            return FlujoPractica(self.ctx).menu()
        if accion == "historial":
            from scenes.results_scene import EscenaHistorial
            return EscenaHistorial(self.ctx)
        if accion == "jugador":
            return EscenaJugador(self.ctx)
        if accion == "logros":
            from scenes.achievements_scene import EscenaLogros
            return EscenaLogros(self.ctx)
        if accion == "ajustes":
            from scenes.settings_scene import EscenaAjustes
            return EscenaAjustes(self.ctx)
        if accion == "info":
            from scenes.info_scene import EscenaInfoSPPB
            return EscenaInfoSPPB(self.ctx, lambda: EscenaMenu(self.ctx))
        return None

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        if self.menu is None:
            self._crear_menu(frame.shape[1], frame.shape[0])
        titulo(frame, "El Gran Circo del Equilibrio", 20)
        segundos = f"{C.DWELL_S:g}".replace(".", ",")
        texto(frame, f"Estira el brazo hacia un botón y mantén la mano {segundos} s",
              (frame.shape[1] // 2, 88), C.TAM_PEQUENO, C.BLANCO, "centro")
        self.menu.dibujar(frame, self.ctx.sprites)
        dibujar_manos(frame, manos_px(self.pose))
        return frame


class EscenaJugador(Scene):
    """Elegir un jugador existente, «Invitado» o escribir uno nuevo con el teclado."""

    MAX_LISTA = 5
    MAX_NOMBRE = 16

    def __init__(self, ctx):
        super().__init__(ctx)
        self.escribiendo = False
        self.nombre = ""
        self.menu: MenuDwell | None = None

    def _crear_menu(self, ancho: int, alto: int) -> None:
        nombres = [n for n in self.ctx.almacen.jugadores() if n != "Invitado"][: self.MAX_LISTA]
        opciones = [(n, f"j:{n}") for n in nombres]
        opciones += [("Invitado", "j:Invitado"), ("Nuevo (teclado)", "nuevo"), ("Volver", "volver")]
        self.menu = MenuDwell.laterales(opciones, ancho, alto, alto=70)

    def _elegir(self, nombre: str) -> Transicion:
        self.ctx.elegir_jugador(nombre)      # se recuerda para la próxima vez que se abra el juego
        perfil = self.ctx.almacen.perfil(nombre)
        self.ctx.almacen.guardar_perfil(perfil)
        return EscenaMenu(self.ctx)

    def _ejecutar(self, accion: str | None) -> Transicion:
        if accion is None:
            return None
        self.ctx.audio.reproducir("click")
        if accion == "volver":
            return EscenaMenu(self.ctx)
        if accion == "nuevo":
            self.escribiendo = True
            self.nombre = ""
            return None
        if accion.startswith("j:"):
            return self._elegir(accion[2:])
        return None

    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        if self.escribiendo or self.menu is None:
            return None
        return self._ejecutar(self.menu.actualizar(manos_px(pose), dt))

    def on_key(self, tecla: str) -> Transicion:
        if self.escribiendo:
            if tecla == "esc":
                self.escribiendo = False
            elif tecla == "enter" and self.nombre.strip():
                return self._elegir(self.nombre.strip())
            elif tecla == "retroceso":
                self.nombre = self.nombre[:-1]
            elif len(tecla) == 1 and (tecla.isalnum() or tecla in " _-") and len(self.nombre) < self.MAX_NOMBRE:
                self.nombre += tecla
            return None
        if tecla == "esc":
            return EscenaMenu(self.ctx)
        if self.menu is None:
            return None
        return self._ejecutar(self.menu.tecla(ALIAS_TECLAS.get(tecla, tecla)))

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        if self.menu is None:
            self._crear_menu(frame.shape[1], frame.shape[0])
        titulo(frame, "¿Quién juega?", 20)
        if self.escribiendo:
            H, W = frame.shape[:2]
            panel(frame, W // 2 - 360, H // 2 - 90, W // 2 + 360, H // 2 + 90, alfa=0.85)
            texto(frame, "Escribe tu nombre y pulsa Enter", (W // 2, H // 2 - 70), C.TAM_TEXTO, C.BLANCO, "centro")
            texto(frame, (self.nombre or "") + "_", (W // 2, H // 2 - 10), C.TAM_TITULO, C.AMARILLO, "centro")
            texto(frame, "Esc: cancelar", (W // 2, H // 2 + 55), C.TAM_PEQUENO, C.GRIS, "centro")
        else:
            self.menu.dibujar(frame, self.ctx.sprites)
            dibujar_manos(frame, manos_px(self.pose))
        return frame

