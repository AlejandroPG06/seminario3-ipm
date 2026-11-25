"""Colocación con silueta guía y calibración de 2 s quieto."""
from __future__ import annotations

from typing import Callable

import numpy as np

import config as C
from core.calibration import Calibracion, Calibrador, evaluar_encuadre
from scenes.base import Scene, Transicion
from ui.dwell_button import anillo
from ui.hud import mensaje_central, titulo
from ui.text import texto


class EscenaColocacion(Scene):
    """Pide al jugador que se coloque (de frente o de lado) y calibra.

    al_calibrar(calibracion) devuelve la escena siguiente; al_cancelar() la de Esc.
    """

    def __init__(self, ctx, vista: str, encabezado: str, instruccion: str,
                 al_calibrar: Callable[[Calibracion], Scene], al_cancelar: Callable[[], Scene]):
        super().__init__(ctx)
        self.vista = vista
        self.encabezado = encabezado
        self.instruccion = instruccion
        self.al_calibrar = al_calibrar
        self.al_cancelar = al_cancelar
        self.calibrador = Calibrador(vista)
        self.aviso = ""
        self.t_ok = 0.0
        self.fase = "colocacion"     # colocacion → calibrando

    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        self.aviso = evaluar_encuadre(pose, self.vista)
        if self.aviso:
            self.t_ok = 0.0
            self.fase = "colocacion"
            self.calibrador = Calibrador(self.vista)
            return None
        if self.fase == "colocacion":
            self.t_ok += dt
            if self.t_ok >= C.ENCUADRE_OK_S:
                self.fase = "calibrando"
                self.ctx.audio.reproducir("cuenta")
            return None
        resultado = self.calibrador.actualizar(pose, dt)
        if resultado is not None:
            self.ctx.audio.reproducir("acierto")
            return self.al_calibrar(resultado)
        return None

    def on_key(self, tecla: str) -> Transicion:
        if tecla == "esc":
            return self.al_cancelar()
        return None

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        ok = not self.aviso
        self.ctx.sprites.silueta(frame, self.vista, C.VERDE if ok else C.BLANCO)
        titulo(frame, self.encabezado, 20)
        texto(frame, self.instruccion, (W // 2, 90), C.TAM_PEQUENO + 2, C.BLANCO, "centro")
        if self.aviso:
            mensaje_central(frame, [self.aviso], C.AMARILLO, y=H - 110)
        elif self.fase == "colocacion":
            mensaje_central(frame, ["¡Bien! Quédate así…"], C.VERDE, y=H - 110)
        else:
            mensaje_central(frame, ["Quieto 2 segundos: calibrando"], C.VERDE, y=H - 110)
            anillo(frame, (W - 90, 90), 50, self.calibrador.progreso, C.VERDE, 12)
        texto(frame, "Esc: volver", (20, H - 36), C.TAM_PEQUENO, C.GRIS)
        return frame

    def debug_info(self) -> dict[str, str]:
        return {"fase": self.fase, "calibración": f"{self.calibrador.progreso:.0%}"}
