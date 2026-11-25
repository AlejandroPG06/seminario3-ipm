"""Botones que se pulsan manteniendo la mano encima (dwell) o con el teclado."""
from __future__ import annotations

import math

import cv2
import numpy as np

import config as C
from ui.text import tamano_texto, texto


class BotonDwell:
    """Botón rectangular con anillo de progreso de dwell."""

    def __init__(self, rect: tuple[int, int, int, int], etiqueta: str, accion: str,
                 activo: bool = True, subtitulo: str = "", tam: int = C.TAM_TEXTO,
                 estrellas: int | None = None, icono: str | None = None):
        self.rect = rect            # x, y, ancho, alto (px)
        self.etiqueta = etiqueta
        self.accion = accion
        self.activo = activo
        self.subtitulo = subtitulo
        self.tam = tam              # px, tamaño de letra de la etiqueta
        self.estrellas = estrellas  # None o 0-3: se dibujan bajo la etiqueta
        self.icono = icono          # None, "ajustes" o "info": se dibuja a la izquierda de la etiqueta
        self.progreso = 0.0         # 0-1
        self.encima = False
        self.seleccionado = False   # foco de teclado

    def contiene(self, punto: tuple[int, int]) -> bool:
        x, y, w, h = self.rect
        return x <= punto[0] <= x + w and y <= punto[1] <= y + h

    def actualizar(self, manos: list[tuple[int, int]], dt: float) -> bool:
        """Avanza el dwell; True si se completa en este frame."""
        self.encima = self.activo and any(self.contiene(m) for m in manos)
        if self.encima:
            self.progreso += dt / C.DWELL_S
            if self.progreso >= 1.0:
                self.progreso = 0.0
                return True
        else:
            self.progreso = max(0.0, self.progreso - dt * C.DWELL_DECAIMIENTO / C.DWELL_S)
        return False

    def dibujar(self, frame: np.ndarray, sprites=None) -> None:
        x, y, w, h = self.rect
        if sprites is not None:
            sprites.boton(frame, self.rect, self.activo, self.encima or self.seleccionado)
        else:
            color = C.ROJO_CARPA if self.activo else C.GRIS
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
            borde = C.DORADO if (self.encima or self.seleccionado) else C.BLANCO
            cv2.rectangle(frame, (x, y), (x + w, y + h), borde, 3)
        color_txt = C.BLANCO if self.activo else (200, 200, 200)
        segunda = bool(self.subtitulo) or self.estrellas is not None
        tam = self.tam if not segunda else self.tam - 4
        con_icono = sprites is not None and (not self.activo or self.icono)
        hueco = 44 if con_icono else 0   # sitio para el candado o el icono
        while tam > 14 and tamano_texto(self.etiqueta, tam)[0] > w - 24 - hueco:   # encoger hasta que quepa
            tam -= 2
        dy = 0 if not segunda else -14
        texto(frame, self.etiqueta, (x + w // 2 + hueco // 2, y + h // 2 - tam // 2 + dy), tam, color_txt, "centro")
        if self.subtitulo:
            sub = C.TAM_PEQUENO
            while sub > 12 and tamano_texto(self.subtitulo, sub)[0] > w - 20:
                sub -= 2
            texto(frame, self.subtitulo, (x + w // 2, y + h // 2 + 6), sub, C.AMARILLO, "centro")
        elif self.estrellas is not None and sprites is not None:
            for k in range(3):
                sprites.estrella(frame, (x + w // 2 + (k - 1) * 34, y + h // 2 + 20), 13, k < self.estrellas)
        if not self.activo and sprites is not None:
            sprites.candado(frame, (x + 26, y + h // 2 - 4), 30)
        elif self.icono and sprites is not None:
            sprites.icono(frame, self.icono, (x + 30, y + h // 2), 36)
        if self.progreso > 0:
            centro = (x + w - h // 2, y + h // 2)
            r = h // 2 - 10
            cv2.ellipse(frame, centro, (r, r), -90, 0, 360 * self.progreso, C.AMARILLO, 6, cv2.LINE_AA)


class MenuDwell:
    """Lista de botones controlable con dwell o con flechas + Enter."""

    def __init__(self, botones: list[BotonDwell]):
        self.botones = botones
        self.indice = next((i for i, b in enumerate(botones) if b.activo), 0)
        self._bloqueo = C.DWELL_BLOQUEO_S
        self._marcar()

    @classmethod
    def laterales(cls, opciones: list[tuple], ancho_frame: int, alto_frame: int,
                  ancho: int = C.MENU_BOTON_ANCHO, alto: int | None = None) -> "MenuDwell":
        """Reparte los botones en dos columnas a los lados (izquierda primero).

        Cada opción es (etiqueta, accion) o (etiqueta, accion, {activo, subtitulo, estrellas, tam, icono}).
        Con 4 o más filas por columna los botones son algo más bajos y ocupan más alto de pantalla.
        """
        n = len(opciones)
        n_izq = math.ceil(n / 2)
        filas = max(1, n_izq)
        muchas = filas >= 4
        if alto is None:
            alto = C.MENU_BOTON_ALTO_4 if muchas else C.MENU_BOTON_ALTO
        y0, y1 = (f * alto_frame for f in (C.MENU_FILAS_Y_4 if muchas else C.MENU_FILAS_Y))
        paso = (y1 - y0 - alto) / max(1, filas - 1) if filas > 1 else 0
        paso = min(paso, alto * 1.6)
        botones = []
        for i, op in enumerate(opciones):
            col, fila = (0, i) if i < n_izq else (1, i - n_izq)
            cx = C.MENU_COLUMNAS_X[col] * ancho_frame
            y = y0 + fila * paso
            extra = op[2] if len(op) > 2 else {}
            botones.append(BotonDwell((int(cx - ancho / 2), int(y), ancho, alto), op[0], op[1], **extra))
        return cls(botones)

    @classmethod
    def vertical(cls, opciones: list[tuple[str, str]], centro_x: int, y0: int,
                 ancho: int = C.BOTON_ANCHO, alto: int = C.BOTON_ALTO) -> "MenuDwell":
        """Crea un menú vertical a partir de (etiqueta, accion)."""
        botones = []
        for i, (etq, acc) in enumerate(opciones):
            y = y0 + i * (alto + C.BOTON_SEPARACION)
            botones.append(BotonDwell((centro_x - ancho // 2, y, ancho, alto), etq, acc))
        return cls(botones)

    def _marcar(self) -> None:
        for i, b in enumerate(self.botones):
            b.seleccionado = i == self.indice

    def actualizar(self, manos: list[tuple[int, int]], dt: float) -> str | None:
        """Devuelve la acción del botón pulsado por dwell, o None.

        Solo carga un botón a la vez (el que más progreso lleve de los que tienen
        una mano encima) y, tras abrir el menú o pulsar, hay DWELL_BLOQUEO_S sin dwell.
        """
        if self._bloqueo > 0:
            self._bloqueo -= dt
            for b in self.botones:
                b.encima, b.progreso = False, 0.0
            return None
        encima = [b for b in self.botones if b.activo and any(b.contiene(m) for m in manos)]
        objetivo = max(encima, key=lambda b: b.progreso) if encima else None
        for b in self.botones:
            b.encima = b is objetivo
            if b is objetivo:
                b.progreso += dt / C.DWELL_S
            elif objetivo is not None:
                b.progreso = 0.0
            else:
                b.progreso = max(0.0, b.progreso - dt * C.DWELL_DECAIMIENTO / C.DWELL_S)
        if objetivo is not None and objetivo.progreso >= 1.0:
            for b in self.botones:
                b.progreso = 0.0
            self._bloqueo = C.DWELL_BLOQUEO_S
            return objetivo.accion
        return None

    def tecla(self, tecla: str) -> str | None:
        """Navega con flechas y devuelve la acción al pulsar Enter."""
        if not self.botones:
            return None
        paso = {"arriba": -1, "izquierda": -1, "abajo": 1, "derecha": 1}.get(tecla)
        if paso:
            n = len(self.botones)
            for _ in range(n):
                self.indice = (self.indice + paso) % n
                if self.botones[self.indice].activo:
                    break
            self._marcar()
        elif tecla == "enter":
            b = self.botones[self.indice]
            return b.accion if b.activo else None
        return None

    def dibujar(self, frame: np.ndarray, sprites=None) -> None:
        for b in self.botones:
            b.dibujar(frame, sprites)


def dibujar_manos(frame: np.ndarray, manos: list[tuple[int, int]]) -> None:
    """Cursor circular en cada mano detectada."""
    for m in manos:
        cv2.circle(frame, m, 16, C.AMARILLO, 3, cv2.LINE_AA)
        cv2.circle(frame, m, 5, C.AMARILLO, -1, cv2.LINE_AA)


def anillo(frame: np.ndarray, centro: tuple[int, int], radio: int, fraccion: float,
           color: tuple = C.VERDE, grosor: int = 10) -> None:
    """Anillo de progreso (0-1) empezando arriba."""
    cv2.circle(frame, centro, radio, (60, 60, 60), grosor, cv2.LINE_AA)
    if fraccion > 0:
        cv2.ellipse(frame, centro, (radio, radio), -90, 0, 360 * min(1.0, fraccion), color, grosor, cv2.LINE_AA)

