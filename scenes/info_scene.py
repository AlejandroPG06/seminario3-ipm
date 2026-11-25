"""Pantalla informativa «¿Qué es la SPPB?» (solo explica; no cambia ninguna prueba).

Se abre desde el menú principal y al entrar en el Modo Evaluación, donde
lleva además un botón para empezar. Tiene dos páginas: qué es y cómo se puntúa.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

import config as C
from scenes.base import Scene, Transicion
from scenes.results_scene import _EscenaConMenu, zona_central
from ui import pictograms
from ui.hud import titulo
from ui.text import panel, parrafo, texto

QUE_ES = [
    "Pruebas que médicos y fisioterapeutas usan en todo el mundo para medir el equilibrio "
    "y la fuerza de las piernas (Guralnik et al., 1994).",
    "Una nota baja avisa de fragilidad y riesgo de caídas.",
]
PRUEBAS_INFO = [("pies_juntos", "Pies juntos", "10 s"), ("semitandem", "Semitándem", "10 s"),
                ("tandem", "Tándem", "10 s"), ("silla", "Silla", "5 veces")]


def _coma(v: float) -> str:
    return f"{v:.2f}".replace(".", ",").replace(",00", "")


def _lineas_puntuacion() -> list[tuple[str, str]]:
    """(prueba, puntos) a partir de los cortes de config."""
    silla, desde = [], None
    for maximo, puntos in C.SPPB_SILLA_CORTES:
        rango = f"hasta {_coma(maximo)} s" if desde is None else f"{_coma(desde)} a {_coma(maximo)} s"
        silla.append((f"Silla, 5 veces: {rango}", f"{puntos} p"))
        desde = maximo + 0.01
    return [
        ("Pies juntos: 10 s", "1 p"),
        ("Semitándem: 10 s", "1 p"),
        (f"Tándem: 10 s  /  {C.SPPB_TANDEM_PARCIAL_S:.0f} a 9,99 s", "2 p / 1 p"),
        *silla,
        ("Silla: más de 60 s o no puede", "0 p"),
    ]


class EscenaInfoSPPB(_EscenaConMenu):
    """Explica la SPPB. `empezar` (opcional) añade el botón para empezar la Evaluación."""

    def __init__(self, ctx, volver: Callable[[], Scene], empezar: Callable[[], Scene] | None = None):
        super().__init__(ctx)
        self.volver = volver
        self.empezar = empezar
        self.pagina = 0          # 0 = qué es, 1 = cómo se puntúa
        self.t = 0.0

    def opciones(self) -> list[tuple]:
        ops = [("Empezar evaluación", "empezar")] if self.empezar else []
        ops.append((self._etiqueta_pagina(), "pagina"))
        ops.append(("Volver", "volver"))
        return ops

    def _etiqueta_pagina(self) -> str:
        return "Cómo se puntúa" if self.pagina == 0 else "Qué es la SPPB"

    def accion(self, a: str) -> Transicion:
        if a == "empezar" and self.empezar:
            return self.empezar()
        if a == "pagina":
            self.pagina = 1 - self.pagina
            for b in self.menu.botones if self.menu else []:
                if b.accion == "pagina":
                    b.etiqueta = self._etiqueta_pagina()
            return None
        return self.volver()

    def update(self, pose, dt) -> Transicion:
        self.t += dt
        return super().update(pose, dt)

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        x0, x1 = zona_central(W)
        titulo(frame, "¿Qué es la SPPB?" if self.pagina == 0 else "¿Cómo se puntúa?", 14)
        panel(frame, x0, 100, x1, H - 30, alfa=0.85)
        if self.pagina == 0:
            self._dibujar_que_es(frame, x0, x1)
        else:
            self._dibujar_puntuacion(frame, x0, x1)
        self.dibujar_menu(frame)
        return frame

    def _dibujar_que_es(self, frame: np.ndarray, x0: int, x1: int) -> None:
        H = frame.shape[0]
        cx, ancho = (x0 + x1) // 2, x1 - x0 - 30
        texto(frame, "Short Physical Performance Battery", (cx, 112), C.TAM_PEQUENO - 4, C.GRIS, "centro")
        y = 142
        for p in QUE_ES:
            y = parrafo(frame, p, cx, y, C.TAM_PEQUENO, C.BLANCO, ancho) + 6
        # Las cuatro pruebas en una cuadrícula 2×2, con su pictograma
        celda_w = (x1 - x0) / 2
        celda_h = (H - 40 - y) / 2
        tam = min(celda_w * 0.7, celda_h - 34)
        for i, (prueba, nombre, dur) in enumerate(PRUEBAS_INFO):
            xc = x0 + celda_w * (i % 2 + 0.5)
            yc = y + celda_h * (i // 2) + tam / 2 + 4
            pictograms.pictograma(frame, (xc, yc), tam, prueba, self.t, self.ctx.sprites)
            texto(frame, f"{nombre} · {dur}", (int(xc), int(yc + tam / 2 + 4)), C.TAM_PEQUENO - 2,
                  C.DORADO, "centro")

    def _dibujar_puntuacion(self, frame: np.ndarray, x0: int, x1: int) -> None:
        H = frame.shape[0]
        cx, ancho = (x0 + x1) // 2, x1 - x0 - 30
        y = 116
        for prueba, puntos in _lineas_puntuacion():
            texto(frame, prueba, (x0 + 18, y), C.TAM_PEQUENO - 2, C.BLANCO)
            texto(frame, puntos, (x1 - 18, y), C.TAM_PEQUENO - 2, C.AMARILLO, "der")
            y += 30
        y += 10
        notas = [
            "La SPPB original incluye también caminar 4 metros. Con una webcam no se puede "
            "medir bien, así que aquí la nota va de 0 a 8.",
            "Es orientativa: no sustituye la valoración de un profesional.",
        ]
        for nota in notas:
            y = parrafo(frame, nota, cx, y, C.TAM_PEQUENO - 4, C.CREMA_CARPA, ancho) + 6
