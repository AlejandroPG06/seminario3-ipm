"""Modo Práctica: elegir cualquier ejercicio y ver qué valdría en la Evaluación."""
from __future__ import annotations

import numpy as np

import config as C
from core.gestures import manos_px
from games.practice import consejos, valor_en_evaluacion
from scenes.base import Scene, Transicion
from scenes.menu import ALIAS_TECLAS
from scenes.results_scene import _EscenaConMenu, dibujar_logros_nuevos, zona_central
from ui.dwell_button import BotonDwell, MenuDwell, dibujar_manos
from ui.hud import titulo
from ui import pictograms
from ui.text import panel, parrafo, texto


class EscenaPractica(Scene):
    """Rejilla con los 6 ejercicios (sin candados) y Volver."""

    def __init__(self, ctx, flujo):
        super().__init__(ctx)
        self.flujo = flujo
        self.menu: MenuDwell | None = None
        self.t = 0.0

    def _crear_menu(self, W: int, H: int) -> None:
        opciones = []
        for prueba in C.EJERCICIOS_PRACTICA:
            tipo = "Cuenta en la SPPB" if prueba in C.PRUEBAS_SPPB else "Complementaria"
            opciones.append((C.NOMBRES_PRUEBA[prueba], f"p:{prueba}", {"subtitulo": tipo, "tam": 28}))
        opciones.append(("Volver", "volver"))
        self.menu = MenuDwell.laterales(opciones, W, H, alto=72)

    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        self.t += dt
        if self.menu is None:
            return None
        return self._ejecutar(self.menu.actualizar(manos_px(pose), dt))

    def on_key(self, tecla: str) -> Transicion:
        if tecla == "esc":
            return self._ejecutar("volver")
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
        return self.flujo.jugar(accion[2:])

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        if self.menu is None:
            self._crear_menu(W, H)
        titulo(frame, "Modo Práctica", 20)
        texto(frame, "Entrena con los criterios de la evaluación", (W // 2, 88), C.TAM_PEQUENO, C.BLANCO, "centro")
        self.menu.dibujar(frame, self.ctx.sprites)
        b = self.menu.botones[self.menu.indice]           # pictograma del ejercicio con el foco
        foco = next((x for x in self.menu.botones if x.encima), b)
        if foco.accion.startswith("p:"):
            pictograms.pictograma(frame, (W // 2, int(H * 0.45)), H * 0.42, foco.accion[2:], self.t, self.ctx.sprites)
        dibujar_manos(frame, manos_px(self.pose))
        return frame


class EscenaResultadoPractica(_EscenaConMenu):
    """Resultado de un ejercicio de práctica: valor en la Evaluación y consejos."""

    def __init__(self, ctx, flujo, prueba: str, res: dict, logros: list[dict]):
        super().__init__(ctx)
        self.flujo = flujo
        self.prueba = prueba
        self.res = res
        self.logros = logros
        self.consejos = consejos(prueba, res)
        self.valor = valor_en_evaluacion(prueba, res)
        ctx.audio.reproducir("fanfarria" if res.get("completado") else "fallo")

    def opciones(self) -> list[tuple[str, str]]:
        return [("Repetir", "repetir"), ("Otro ejercicio", "otro"), ("Menú", "menu")]

    def accion(self, a: str) -> Transicion:
        if a == "repetir":
            return self.flujo.jugar(self.prueba)
        if a == "otro":
            return self.flujo.menu()
        from scenes.menu import EscenaMenu
        return EscenaMenu(self.ctx)

    def _resumen(self) -> str:
        r = self.res
        if self.prueba == "marcha":
            return f"{r['pasos']} pasos en {r['tiempo']:.0f} s ({r['pasos_der']} con la rodilla derecha)"
        if self.prueba == "silla":
            if r.get("tiempo") is not None:
                return f"{r['repeticiones']} levantadas en {r['tiempo']:.2f} s"
            return f"{r['repeticiones']}/{r['objetivo']} levantadas: se acabó el tiempo"
        return f"{r['motivo']} · {r['tiempo']:.1f} s"

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        x0, x1 = zona_central(W)
        panel(frame, x0, 100, x1, H - 20, alfa=0.8)
        titulo(frame, f"Práctica: {C.NOMBRES_PRUEBA[self.prueba]}", 20)
        ancho = x1 - x0 - 30
        y = parrafo(frame, self._resumen(), W // 2, 115, C.TAM_TEXTO - 4, C.BLANCO, ancho)
        y = parrafo(frame, self.valor, W // 2, y + 8, C.TAM_TEXTO - 6, C.DORADO, ancho)
        texto(frame, "Consejos", (W // 2, y + 14), C.TAM_TEXTO - 6, C.AMARILLO, "centro")
        y += 52
        for c in self.consejos:
            y = parrafo(frame, "• " + c, W // 2, y, C.TAM_PEQUENO, C.BLANCO, ancho) + 6
        dibujar_logros_nuevos(frame, self.logros[:1], y + 10, ancho)
        self.dibujar_menu(frame)
        return frame
