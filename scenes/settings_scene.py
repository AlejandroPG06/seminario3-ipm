"""Pantalla de Ajustes: música, volumen, fondo de circo, animaciones y detección.

Los cambios se aplican al momento y se guardan en data/ajustes.json. La
detección (modelo y máscara de segmentación) la cambia main.py en el siguiente
frame al ver que los ajustes ya no coinciden con el detector actual.
"""
from __future__ import annotations

import os

import cv2
import numpy as np

import config as C
from scenes.base import Transicion
from scenes.results_scene import _EscenaConMenu, zona_central
from ui.hud import titulo
from ui.text import panel, parrafo, texto


def _si_no(valor: bool) -> str:
    return "Sí" if valor else "No"


class EscenaAjustes(_EscenaConMenu):
    """Botones de ajustes a los lados y, en el centro, el volumen y los fps actuales."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.hay_modelo_rapido = os.path.exists(C.MODEL_PATH_RAPIDO)

    def _etiquetas(self) -> dict[str, str]:
        a = self.ctx.ajustes
        return {
            "musica": f"Música: {_si_no(a.musica)}",
            "fondo": f"Fondo circo: {_si_no(a.fondo)}",
            "animaciones": f"Animaciones: {_si_no(a.animaciones)}",
            "deteccion": f"Detección: {'Rápida' if a.deteccion_rapida else 'Precisa'}",
            "esqueleto": f"Esqueleto: {_si_no(a.esqueleto)}",
        }

    def opciones(self) -> list[tuple]:
        e = self._etiquetas()
        deteccion = {} if self.hay_modelo_rapido else {"activo": False, "subtitulo": "falta el modelo lite"}
        return [
            (e["musica"], "musica"),
            ("Subir volumen", "subir"),
            ("Bajar volumen", "bajar"),
            (e["deteccion"], "deteccion", deteccion),
            (e["fondo"], "fondo"),
            (e["animaciones"], "animaciones"),
            (e["esqueleto"], "esqueleto"),
            ("Volver", "volver"),
        ]

    def accion(self, a: str) -> Transicion:
        aj = self.ctx.ajustes
        if a == "volver":
            from scenes.menu import EscenaMenu
            return EscenaMenu(self.ctx)
        if a == "musica":
            aj.musica = not aj.musica
        elif a == "subir":
            aj.musica = True
            aj.cambiar_volumen(+1)
        elif a == "bajar":
            aj.cambiar_volumen(-1)
        elif a == "fondo":
            aj.fondo = not aj.fondo
        elif a == "animaciones":
            aj.animaciones = not aj.animaciones
        elif a == "esqueleto":
            aj.esqueleto = not aj.esqueleto
        elif a == "deteccion" and self.hay_modelo_rapido:
            aj.deteccion_rapida = not aj.deteccion_rapida
        self.ctx.guardar_ajustes()
        self._refrescar_etiquetas()
        return None

    def _refrescar_etiquetas(self) -> None:
        if self.menu is None:
            return
        etiquetas = self._etiquetas()
        for b in self.menu.botones:
            if b.accion in etiquetas:
                b.etiqueta = etiquetas[b.accion]

    def on_key(self, tecla: str) -> Transicion:
        if tecla in ("+", "-"):                 # atajo de teclado para el volumen
            return self.accion("subir" if tecla == "+" else "bajar")
        return super().on_key(tecla)

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        x0, x1 = zona_central(W)
        aj = self.ctx.ajustes
        titulo(frame, "Ajustes", 14)
        panel(frame, x0, 100, x1, H - 30, alfa=0.8)
        cx = W // 2
        texto(frame, "Volumen de la música", (cx, 120), C.TAM_TEXTO - 4, C.DORADO, "centro")
        _barra_volumen(frame, (x0 + 40, 170, x1 - 40, 206), aj.volumen_musica if aj.musica else 0)
        estado = f"{aj.volumen_musica} %" if aj.musica else "Música apagada"
        texto(frame, estado, (cx, 214), C.TAM_TEXTO - 6, C.BLANCO, "centro")
        y = 270
        color_fps = C.VERDE if self.ctx.fps >= 24 else (C.AMARILLO if self.ctx.fps >= 15 else C.NARANJA)
        texto(frame, f"Ahora: {self.ctx.fps:.0f} fps", (cx, y), C.TAM_TEXTO - 2, color_fps, "centro")
        y += 50
        ayuda = ("¿Va a tirones? Quita el fondo de circo y las animaciones, "
                 "o usa la detección rápida (algo menos precisa).")
        y = parrafo(frame, ayuda, cx, y, C.TAM_PEQUENO, C.BLANCO, x1 - x0 - 40) + 16
        parrafo(frame, "Se guardan solos para la próxima vez. Tecla M: música.", cx, y,
                C.TAM_PEQUENO - 2, C.GRIS, x1 - x0 - 40)
        self.dibujar_menu(frame)
        return frame


def _barra_volumen(frame: np.ndarray, rect: tuple[int, int, int, int], pct: int) -> None:
    """Barra de 10 segmentos que se encienden según el volumen."""
    x0, y0, x1, y1 = rect
    n = 100 // C.AJUSTES_VOLUMEN_PASO
    ancho = (x1 - x0) / n
    for k in range(n):
        encendido = (k + 1) * C.AJUSTES_VOLUMEN_PASO <= pct
        alto = int((y1 - y0) * (0.35 + 0.65 * (k + 1) / n))
        a = (int(x0 + k * ancho + 3), y1 - alto)
        b = (int(x0 + (k + 1) * ancho - 3), y1)
        cv2.rectangle(frame, a, b, C.AMARILLO if encendido else (70, 70, 70), -1)
