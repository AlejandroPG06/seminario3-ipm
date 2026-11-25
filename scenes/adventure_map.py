"""Mapa del Modo Aventura: actos con estrellas y candados, y niveles de cada acto."""
from __future__ import annotations

import numpy as np

import config as C
from core.gestures import manos_px
from games.progress import (acto_desbloqueado, estrellas_nivel, nivel_desbloqueado,
                            total_estrellas_acto)
from scenes.base import Scene, Transicion
from scenes.menu import ALIAS_TECLAS
from ui import pictograms
from ui.dwell_button import MenuDwell, dibujar_manos
from ui.hud import titulo
from ui.text import parrafo, texto


class EscenaMapa(Scene):
    """Vista de actos (acto_id=None) o de los niveles de un acto."""

    def __init__(self, ctx, flujo, acto_id: int | None = None):
        super().__init__(ctx)
        self.flujo = flujo
        self.acto_id = acto_id
        self.progreso = ctx.perfil().get("progreso", {})
        self.menu: MenuDwell | None = None
        self.t = 0.0

    def _crear_menu(self, W: int, H: int) -> None:
        opciones = []
        if self.acto_id is None:
            for acto in C.ACTOS:
                abierto = acto_desbloqueado(self.progreso, acto["id"])
                total = total_estrellas_acto(self.progreso, acto["id"])
                sub = f"Acto {acto['id']} · {total}/{3 * len(acto['niveles'])} estrellas"
                opciones.append((acto["nombre"], f"a:{acto['id']}", {"activo": abierto, "subtitulo": sub, "tam": 28}))
            opciones.append(("Volver", "volver"))
        else:
            acto = C.ACTOS[self.acto_id - 1]
            for i, nivel in enumerate(acto["niveles"]):
                n = i + 1
                abierto = nivel_desbloqueado(self.progreso, self.acto_id, n)
                opciones.append((f"{n}. {nivel['nombre']}", f"n:{n}",
                                 {"activo": abierto, "estrellas": estrellas_nivel(self.progreso, self.acto_id, n),
                                  "tam": 28}))
            opciones.append(("Volver al mapa", "mapa"))
        self.menu = MenuDwell.laterales(opciones, W, H)

    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        self.t += dt
        if self.menu is None:
            return None
        return self._ejecutar(self.menu.actualizar(manos_px(pose), dt))

    def on_key(self, tecla: str) -> Transicion:
        if tecla == "esc":
            return self._ejecutar("mapa" if self.acto_id else "volver")
        if self.menu is None:
            return None
        return self._ejecutar(self.menu.tecla(ALIAS_TECLAS.get(tecla, tecla)))

    def _ejecutar(self, accion: str | None) -> Transicion:
        if accion is None:
            return None
        self.ctx.audio.reproducir("click")
        if accion == "volver":
            from scenes.menu import EscenaMenu
            return EscenaMenu(self.ctx)
        if accion == "mapa":
            return self.flujo.mapa()
        if accion.startswith("a:"):
            return self.flujo.mapa(int(accion[2:]))
        if accion.startswith("n:"):
            return self.flujo.jugar(self.acto_id, int(accion[2:]))
        return None

    def _acto_enfocado(self) -> dict:
        """Acto del botón con la mano encima (o con el foco de teclado)."""
        if self.acto_id is not None:
            return C.ACTOS[self.acto_id - 1]
        foco = next((b for b in self.menu.botones if b.encima), self.menu.botones[self.menu.indice])
        if foco.accion.startswith("a:"):
            return C.ACTOS[int(foco.accion[2:]) - 1]
        return C.ACTOS[0]

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        if self.menu is None:
            self._crear_menu(W, H)
        if self.acto_id is None:
            titulo(frame, "Modo Aventura", 20)
            texto(frame, f"{C.ESTRELLAS_DESBLOQUEO_ACTO} estrellas en un nivel abren el siguiente acto",
                  (W // 2, 88), C.TAM_PEQUENO, C.BLANCO, "centro")
        else:
            titulo(frame, C.ACTOS[self.acto_id - 1]["nombre"], 20)
        self.menu.dibujar(frame, self.ctx.sprites)
        # En el centro: pictograma y descripción del acto enfocado
        acto = self._acto_enfocado()
        pictograms.pictograma(frame, (W // 2, int(H * 0.42)), H * 0.38, acto["prueba"], self.t, self.ctx.sprites)
        parrafo(frame, acto["descripcion"], W // 2, int(H * 0.66), C.TAM_TEXTO - 4, C.CREMA_CARPA, 440)
        dibujar_manos(frame, manos_px(self.pose))
        return frame
