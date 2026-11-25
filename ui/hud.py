"""Elementos del HUD: tiempo, puntos, racha, semáforo de estabilidad, textos flotantes."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

import config as C
from ui.dwell_button import anillo
from ui.text import panel, texto


def color_estabilidad(balanceo_abs: float) -> tuple:
    """Verde / amarillo / rojo según los umbrales de multiplicador."""
    if balanceo_abs < C.MULTIPLICADORES_ESTABILIDAD[0][0]:
        return C.VERDE
    if balanceo_abs < C.MULTIPLICADORES_ESTABILIDAD[1][0]:
        return C.AMARILLO
    return C.ROJO


def semaforo(frame: np.ndarray, x: int, y: int, balanceo_abs: float) -> None:
    """Medidor de estabilidad tipo semáforo (3 luces verticales)."""
    panel(frame, x, y, x + 60, y + 170)
    activo = color_estabilidad(balanceo_abs)
    for i, col in enumerate((C.ROJO, C.AMARILLO, C.VERDE)):
        c = (x + 30, y + 30 + i * 55)
        encendido = col == activo
        cv2.circle(frame, c, 22, col if encendido else tuple(v // 4 for v in col), -1, cv2.LINE_AA)
        if encendido:
            cv2.circle(frame, c, 24, C.BLANCO, 2, cv2.LINE_AA)


def barra_balanceo(frame: np.ndarray, cx: int, y: int, balanceo: float, ancho: int = 400) -> None:
    """Barra horizontal con la posición del balanceo (para depurar y para Evaluación)."""
    x0, x1 = cx - ancho // 2, cx + ancho // 2
    cv2.rectangle(frame, (x0, y), (x1, y + 16), (50, 50, 50), -1)
    zona = int(ancho / 2 * C.MULTIPLICADORES_ESTABILIDAD[1][0] / 0.4)
    cv2.rectangle(frame, (cx - zona, y), (cx + zona, y + 16), (60, 120, 60), -1)
    px = int(cx + np.clip(balanceo / 0.4, -1, 1) * ancho / 2)
    cv2.circle(frame, (px, y + 8), 11, color_estabilidad(abs(balanceo)), -1, cv2.LINE_AA)
    cv2.line(frame, (cx, y - 4), (cx, y + 20), C.BLANCO, 2)


def reloj(frame: np.ndarray, centro: tuple[int, int], restante_s: float, total_s: float) -> None:
    """Barra de tiempo circular con los segundos restantes en el centro."""
    frac = 0.0 if total_s <= 0 else max(0.0, restante_s) / total_s
    color = C.VERDE if frac > 0.3 else C.NARANJA
    cv2.circle(frame, centro, 52, (30, 30, 30), -1, cv2.LINE_AA)
    anillo(frame, centro, 46, frac, color, 9)
    texto(frame, f"{max(0.0, restante_s):.1f}", (centro[0], centro[1] - 18), 32, C.BLANCO, "centro")


def marcador(frame: np.ndarray, puntos: int, racha_s: float, mult: float) -> None:
    """Panel de puntos, racha y multiplicador (arriba a la izquierda)."""
    panel(frame, 10, 10, 330, 130)
    texto(frame, f"Puntos: {puntos}", (24, 18), 34, C.AMARILLO)
    texto(frame, f"Racha: {racha_s:.1f} s", (24, 60), 26, C.BLANCO)
    texto(frame, f"x{mult:.2f}", (24, 92), 26, C.VERDE if mult > 1 else C.BLANCO)


def estrellas_en_juego(frame: np.ndarray, centro: tuple[int, int], estrellas: int, sprites) -> None:
    """Estrellas que aún se pueden conseguir en el nivel (las perdidas salen vacías)."""
    x, y = centro
    panel(frame, x - 160, y - 26, x + 160, y + 26)
    texto(frame, "En juego:", (x - 150, y - 15), C.TAM_PEQUENO, C.BLANCO)
    for k in range(3):
        sprites.estrella(frame, (x + 40 + k * 44, y), 18, k < estrellas)


def mensaje_central(frame: np.ndarray, lineas: list[str], color=C.BLANCO, tam: int = C.TAM_TEXTO,
                    y: int | None = None) -> None:
    """Varias líneas centradas sobre un panel."""
    H, W = frame.shape[:2]
    alto_linea = int(tam * 1.4)
    y0 = (H // 2 - len(lineas) * alto_linea // 2) if y is None else y
    panel(frame, W // 2 - 520, y0 - 16, W // 2 + 520, y0 + len(lineas) * alto_linea + 10)
    for i, l in enumerate(lineas):
        texto(frame, l, (W // 2, y0 + i * alto_linea), tam, color, "centro")


def titulo(frame: np.ndarray, txt: str, y: int = 30, color=C.DORADO) -> None:
    """Título grande centrado."""
    texto(frame, txt, (frame.shape[1] // 2, y), C.TAM_TITULO, color, "centro")


@dataclass
class _TextoFlotante:
    texto: str
    x: float
    y: float
    color: tuple
    vida: float


class TextosFlotantes:
    """Textos que suben y desaparecen («¡Perfecto!», «+25»)."""

    def __init__(self):
        self._items: list[_TextoFlotante] = []

    def anadir(self, txt: str, pos: tuple[int, int], color=C.AMARILLO) -> None:
        self._items.append(_TextoFlotante(txt, pos[0], pos[1], color, C.TEXTO_FLOTANTE_S))

    def actualizar(self, dt: float) -> None:
        for t in self._items:
            t.vida -= dt
            t.y -= 60 * dt
        self._items = [t for t in self._items if t.vida > 0]

    def dibujar(self, frame: np.ndarray) -> None:
        for t in self._items:
            tam = int(40 + 12 * (t.vida / C.TEXTO_FLOTANTE_S))
            texto(frame, t.texto, (int(t.x), int(t.y)), tam, t.color, "centro")
