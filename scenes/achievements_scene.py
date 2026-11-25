"""Pantalla de logros: todos los logros en una cuadrícula (verde = conseguido, gris = pendiente).

Al pasar la mano por encima de un logro (o elegirlo con las flechas) se explica
abajo cómo se consigue y cuánto lleva el jugador. Elegir un logro no cambia
nada, así que basta con señalarlo (sin esperar el dwell). «Volver» sí usa dwell
y está en la misma esquina que el trofeo del menú.
"""
from __future__ import annotations

import cv2
import numpy as np

import config as C
from core.gestures import manos_px
from games.achievements import estadisticas, progreso_logro
from scenes.base import Scene, Transicion
from ui.dwell_button import BotonDwell, MenuDwell, dibujar_manos
from ui.hud import titulo
from ui.text import panel, parrafo, tamano_texto, texto

COLUMNAS = 4
VERDE_LOGRO = (60, 150, 60)       # BGR, fondo de un logro conseguido
GRIS_LOGRO = (90, 90, 90)         # BGR, fondo de un logro pendiente


class EscenaLogros(Scene):
    """Cuadrícula de logros con su explicación."""

    def __init__(self, ctx):
        super().__init__(ctx)
        perfil = ctx.perfil()
        self.conseguidos = set(perfil.get("logros", []))
        self.stats = estadisticas(perfil, ctx.almacen.historial(ctx.jugador))
        self.indice = 0
        self.rects: list[tuple[int, int, int, int]] = []
        self.menu: MenuDwell | None = None

    # -- disposición --------------------------------------------------------
    def _crear(self, W: int, H: int) -> None:
        n = len(C.LOGROS)
        filas = -(-n // COLUMNAS)
        hueco = 14
        ancho = min(250, (W - 120 - hueco * (COLUMNAS - 1)) // COLUMNAS)
        alto = 78
        x0 = (W - (COLUMNAS * ancho + (COLUMNAS - 1) * hueco)) // 2
        y0 = 120
        self.rects = [(x0 + (i % COLUMNAS) * (ancho + hueco), y0 + (i // COLUMNAS) * (alto + hueco), ancho, alto)
                      for i in range(n)]
        self.y_detalle = y0 + filas * (alto + hueco) + 6
        t = C.MENU_TROFEO_TAM
        m = C.MENU_TROFEO_MARGEN
        volver = BotonDwell((W - m - 200, H - m - t, 200, t), "Volver", "volver")
        self.menu = MenuDwell([volver])

    # -- bucle ------------------------------------------------------------------
    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        if self.menu is None:
            return None
        manos = manos_px(pose)
        for i, (x, y, w, h) in enumerate(self.rects):
            if any(x <= mx <= x + w and y <= my <= y + h for mx, my in manos):
                self.indice = i
                break
        if self.menu.actualizar(manos, dt) == "volver":
            return self._volver()
        return None

    def _volver(self) -> Scene:
        from scenes.menu import EscenaMenu
        self.ctx.audio.reproducir("click")
        return EscenaMenu(self.ctx)

    def on_key(self, tecla: str) -> Transicion:
        if tecla in ("esc", "enter", "retroceso"):
            return self._volver()
        paso = {"izquierda": -1, "a": -1, "derecha": 1, "d": 1,
                "arriba": -COLUMNAS, "w": -COLUMNAS, "abajo": COLUMNAS, "s": COLUMNAS}.get(tecla)
        if paso:
            self.indice = (self.indice + paso) % len(C.LOGROS)
        return None

    # -- dibujo -------------------------------------------------------------------
    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        if self.menu is None:
            self._crear(W, H)
        titulo(frame, "Logros", 14)
        n_ok = sum(1 for l in C.LOGROS if l["id"] in self.conseguidos)
        texto(frame, f"{self.ctx.jugador}: {n_ok} de {len(C.LOGROS)} conseguidos", (W // 2, 80),
              C.TAM_PEQUENO, C.BLANCO, "centro")
        for i, (logro, rect) in enumerate(zip(C.LOGROS, self.rects)):
            self._casilla(frame, rect, logro, logro["id"] in self.conseguidos, i == self.indice)
        self._detalle(frame, C.LOGROS[self.indice])
        self.menu.dibujar(frame, self.ctx.sprites)
        dibujar_manos(frame, manos_px(self.pose))
        return frame

    def _casilla(self, frame, rect, logro: dict, conseguido: bool, elegido: bool) -> None:
        x, y, w, h = rect
        fondo = frame[y:y + h, x:x + w]
        color = np.array(VERDE_LOGRO if conseguido else GRIS_LOGRO, np.float32)
        fondo[:] = (fondo * 0.15 + color * 0.85).astype(np.uint8)
        borde = C.AMARILLO if elegido else (C.BLANCO if conseguido else (150, 150, 150))
        cv2.rectangle(frame, (x, y), (x + w, y + h), borde, 4 if elegido else 2)
        if conseguido:
            self.ctx.sprites.icono(frame, "trofeo", (x + 30, y + h // 2), 38)
        else:
            self.ctx.sprites.trofeo(frame, (x + 30, y + h // 2), 38, (150, 150, 150))
        tam = C.TAM_PEQUENO + 2
        while tam > 14 and tamano_texto(logro["nombre"], tam)[0] > w - 66:
            tam -= 2
        texto(frame, logro["nombre"], (x + 56, y + h // 2 - tam // 2 - 2), tam,
              C.BLANCO if conseguido else (210, 210, 210))

    def _detalle(self, frame, logro: dict) -> None:
        H, W = frame.shape[:2]
        conseguido = logro["id"] in self.conseguidos
        x0, x1 = self.rects[0][0], self.rects[COLUMNAS - 1][0] + self.rects[COLUMNAS - 1][2]
        x1 = min(x1, W - C.MENU_TROFEO_MARGEN - 220)       # deja sitio al botón Volver
        y0, y1 = self.y_detalle, H - 20
        panel(frame, x0, y0, x1, y1, alfa=0.82)
        cx = (x0 + x1) // 2
        estado = "¡Conseguido!" if conseguido else "Pendiente"
        texto(frame, f"{logro['nombre']} · {estado}", (cx, y0 + 12), C.TAM_TEXTO - 2,
              C.VERDE if conseguido else (200, 200, 200), "centro")
        y = parrafo(frame, logro.get("explicacion", logro["descripcion"]), cx, y0 + 60,
                    C.TAM_PEQUENO + 2, C.BLANCO, x1 - x0 - 40) + 6
        if not conseguido:
            progreso = progreso_logro(logro, self.stats)
            if progreso:
                texto(frame, progreso, (cx, y), C.TAM_PEQUENO, C.AMARILLO, "centro")
