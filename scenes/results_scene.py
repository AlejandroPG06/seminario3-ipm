"""Pantallas de resultados (nivel de Aventura, Evaluación, preguntas) e Historial.

Los botones van en columnas laterales (ver MenuDwell.laterales) y el texto en
la zona central que queda libre entre ellas.
"""
from __future__ import annotations

import cv2
import numpy as np

import config as C
from core.gestures import manos_px
from scenes.base import Scene, Transicion
from scenes.menu import ALIAS_TECLAS
from ui.dwell_button import MenuDwell, dibujar_manos
from ui.hud import titulo
from games.practice import MAXIMOS_SPPB
from games.tips import consejo_evaluacion, consejos_nivel
from ui.particles import Confeti
from ui.text import panel, parrafo, texto

NOMBRES_LOGROS = {l["id"]: l for l in C.LOGROS}


def zona_central(W: int) -> tuple[int, int]:
    """x inicial y final de la zona libre entre las dos columnas de botones."""
    x0 = int(C.MENU_COLUMNAS_X[0] * W + C.MENU_BOTON_ANCHO / 2 + 12)
    x1 = int(C.MENU_COLUMNAS_X[1] * W - C.MENU_BOTON_ANCHO / 2 - 12)
    return x0, x1


class _EscenaConMenu(Scene):
    """Base para pantallas con botones (dwell + teclado)."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.menu: MenuDwell | None = None

    def opciones(self) -> list[tuple[str, str]]:
        return []

    def accion(self, accion: str) -> Transicion:
        return None

    def _crear_menu(self, W: int, H: int) -> None:
        self.menu = MenuDwell.laterales(self.opciones(), W, H)

    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        if self.menu is None:
            return None
        a = self.menu.actualizar(manos_px(pose), dt)
        return self._ejecutar(a)

    def on_key(self, tecla: str) -> Transicion:
        if tecla == "esc":
            return self._ejecutar(self.opciones()[-1][1])
        if self.menu is None:
            return None
        return self._ejecutar(self.menu.tecla(ALIAS_TECLAS.get(tecla, tecla)))

    def _ejecutar(self, a: str | None) -> Transicion:
        if a is None:
            return None
        self.ctx.audio.reproducir("click")
        return self.accion(a)

    def dibujar_menu(self, frame: np.ndarray) -> None:
        H, W = frame.shape[:2]
        if self.menu is None:
            self._crear_menu(W, H)
        self.menu.dibujar(frame, self.ctx.sprites)
        dibujar_manos(frame, manos_px(self.pose))


def _menu(ctx) -> Scene:
    from scenes.menu import EscenaMenu
    return EscenaMenu(ctx)


def dibujar_logros_nuevos(frame: np.ndarray, logros: list[dict], y: int, ancho: int | None = None) -> int:
    """Lista de logros recién conseguidos; devuelve la y siguiente."""
    if not logros:
        return y
    W = frame.shape[1]
    ancho = ancho or W - 80
    texto(frame, "¡Logro conseguido!", (W // 2, y), C.TAM_TEXTO - 6, C.DORADO, "centro")
    y += 36
    for l in logros:
        y = parrafo(frame, f"{l['nombre']}: {l['descripcion']}", W // 2, y, C.TAM_PEQUENO - 2, C.BLANCO, ancho)
    return y


class EscenaResultadosNivel(_EscenaConMenu):
    """Estrellas, puntos y logros de un nivel de Aventura."""

    def __init__(self, ctx, flujo, acto_id: int, n_nivel: int, res: dict, estrellas: int,
                 logros: list[dict], record: bool):
        super().__init__(ctx)
        self.flujo = flujo
        self.acto_id, self.n_nivel = acto_id, n_nivel
        self.res = res
        self.estrellas = estrellas
        self.logros = logros
        self.record = record
        self.siguiente = flujo.hay_siguiente(acto_id, n_nivel)
        acto = C.ACTOS[acto_id - 1]
        self.consejos = consejos_nivel(acto, acto["niveles"][n_nivel - 1], res, estrellas)
        self.t = 0.0
        self.mostradas = 0
        self.confeti = Confeti(ctx.semilla, ctx.animaciones)
        if estrellas > 0:
            self.confeti.lanzar(1280)
            ctx.audio.reproducir("fanfarria")

    def opciones(self) -> list[tuple[str, str]]:
        ops = [("Repetir", "repetir")]
        if self.siguiente:
            ops.append(("Siguiente", "siguiente"))
        ops.append(("Mapa", "mapa"))
        return ops

    def accion(self, a: str) -> Transicion:
        if a == "repetir":
            return self.flujo.jugar(self.acto_id, self.n_nivel)
        if a == "siguiente" and self.siguiente:
            return self.flujo.jugar(*self.siguiente)
        return self.flujo.mapa(self.acto_id)

    def update(self, pose, dt) -> Transicion:
        self.t += dt
        self.confeti.actualizar(dt)
        objetivo = min(self.estrellas, int(self.t / 0.5))
        if objetivo > self.mostradas:
            self.mostradas = objetivo
            self.ctx.audio.reproducir("acierto")
        return super().update(pose, dt)

    def _lineas(self) -> list[str]:
        r = self.res
        acto = C.ACTOS[self.acto_id - 1]
        lineas = [f"Puntos: {r['puntos']}" + (" · ¡Récord!" if self.record else "")]
        if r["prueba"] == "silla":
            if r["tiempo"] is not None:
                lineas.append(f"{r['repeticiones']} levantadas en {r['tiempo']:.2f} s")
                lineas.append(f"¡{r['distancia']:.0f} m de vuelo!")
            else:
                lineas.append(f"{r['repeticiones']}/{r['objetivo']} levantadas: se acabó el tiempo")
            calidades = [rep.calidad for rep in r["reps"]]
            if r.get("ritmo"):
                lineas.append(f"Al ritmo: {len(calidades)} · Fuera de ritmo: {r.get('fuera_ritmo', 0)}")
            else:
                lineas.append(f"Perfectas {calidades.count('Perfecta')} · Buenas {calidades.count('Buena')}"
                              + (" · Con manos" if r["manos"] else ""))
        elif r["prueba"] == "marcha":
            lineas.append(f"{r['pasos']} pasos en {r['tiempo']:.0f} s")
            if acto["niveles"][self.n_nivel - 1].get("tempo_bpm"):
                lineas.append(f"Al compás: {r['al_compas']} de {r['pasos']}")
        else:
            lineas.append(f"{r['motivo']} · {r['tiempo']:.1f} s")
            lineas.append(f"Racha máxima: {r['racha_max_s']:.1f} s")
        if r.get("burbujas"):
            lineas.append(f"Burbujas: {r['burbujas']}")
        return lineas

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        x0, x1 = zona_central(W)
        acto = C.ACTOS[self.acto_id - 1]
        superado = self.estrellas > 0
        titulo(frame, "¡Nivel superado!" if superado else "¡Casi! Otra vez", 14,
               C.DORADO if superado else C.NARANJA)
        texto(frame, f"{acto['nombre']} · {acto['niveles'][self.n_nivel - 1]['nombre']}",
              (W // 2, 80), C.TAM_PEQUENO, C.BLANCO, "centro")
        panel(frame, x0, 115, x1, H - 20, alfa=0.72)
        for k in range(3):
            self.ctx.sprites.estrella(frame, (W // 2 - 100 + k * 100, 175), 40, k < self.mostradas)
        y = 235
        for linea in self._lineas():
            y = parrafo(frame, linea, W // 2, y, C.TAM_TEXTO - 8, C.BLANCO, x1 - x0 - 24) + 2
        y += 6
        for c in self.consejos:          # qué hacer para conseguir (más) estrellas
            y = parrafo(frame, c, W // 2, y, C.TAM_PEQUENO, C.AMARILLO, x1 - x0 - 24) + 4
        dibujar_logros_nuevos(frame, self.logros[:1], y + 8, x1 - x0 - 24)
        self.dibujar_menu(frame)
        self.confeti.dibujar(frame)
        return frame


class EscenaResultadosEvaluacion(_EscenaConMenu):
    """Tabla de la SPPB reducida con puntuación 0-8, interpretación y complementarias."""

    def __init__(self, ctx, res: dict, logros: list[dict]):
        super().__init__(ctx)
        self.res = res
        self.logros = logros
        ctx.audio.reproducir("fanfarria")

    def opciones(self) -> list[tuple[str, str]]:
        return [("Historial", "historial"), ("Menú", "menu")]

    def accion(self, a: str) -> Transicion:
        if a == "historial":
            return EscenaHistorial(self.ctx)
        return _menu(self.ctx)

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        x0, x1 = zona_central(W)
        ancho = x1 - x0 - 24
        titulo(frame, "Resultado de la evaluación", 14)
        panel(frame, x0, 85, x1, H - 12, alfa=0.82)
        y = 98
        fila = C.TAM_PEQUENO
        for prueba in ("pies_juntos", "semitandem", "tandem", "silla"):
            t = self.res["tiempos"].get(prueba)
            pts = self.res["puntos"][prueba]
            maximo = {"tandem": 2, "silla": 4}.get(prueba, 1)
            if prueba in self.res["omitidas"]:
                desc = "no hecha"
            elif t is None:
                desc = "no completada"
            else:
                desc = f"{t:.2f} s"
            texto(frame, C.NOMBRES_PRUEBA[prueba], (x0 + 12, y), fila, C.BLANCO)
            texto(frame, desc, (x1 - 70, y), fila, C.GRIS if t is None else C.BLANCO, "der")
            texto(frame, f"{pts}/{maximo}", (x1 - 12, y), fila, C.AMARILLO, "der")
            y += 32
        texto(frame, f"SPPB: {self.res['total']} / 8", (W // 2, y + 6), C.TAM_TEXTO + 8, C.DORADO, "centro")
        y = parrafo(frame, self.res["interpretacion"], W // 2, y + 54, C.TAM_PEQUENO + 2, C.BLANCO, ancho)
        if self.res.get("manos_silla"):
            y = parrafo(frame, "Aviso: posible apoyo de las manos en la silla", W // 2, y, C.TAM_PEQUENO - 2,
                        C.NARANJA, ancho)
        comp = self.res.get("complementarias", {})
        if comp:
            y = parrafo(frame, "Complementarias (no suman)", W // 2, y + 8, C.TAM_PEQUENO, C.DORADO, ancho)
            if "una_pierna" in comp:
                v = comp["una_pierna"]["valor"]
                desc = f"{v:.1f} s" if v is not None else "no completada"
                y = parrafo(frame, f"Una pierna: {desc}", W // 2, y, C.TAM_PEQUENO - 2, C.BLANCO, ancho)
                y = parrafo(frame, comp["una_pierna"]["texto"], W // 2, y, C.TAM_PEQUENO - 6, C.CREMA_CARPA, ancho)
            if "marcha" in comp:
                v = comp["marcha"]["valor"]
                desc = f"{int(v)} pasos (rodilla dcha.)" if v is not None else "no completada"
                y = parrafo(frame, f"Marcha {C.MARCHA_EVAL_S:.0f} s: {desc}", W // 2, y, C.TAM_PEQUENO - 2, C.BLANCO, ancho)
                y = parrafo(frame, comp["marcha"]["texto"], W // 2, y, C.TAM_PEQUENO - 6, C.CREMA_CARPA, ancho)
        y = parrafo(frame, consejo_evaluacion(self.res["puntos"], MAXIMOS_SPPB), W // 2, y + 6,
                    C.TAM_PEQUENO - 2, C.AMARILLO, ancho)
        y = parrafo(frame, "SPPB reducida (sin marcha de 4 m). Orientativa: no es un diagnóstico.",
                    W // 2, y + 6, C.TAM_PEQUENO - 8, C.GRIS, ancho)
        dibujar_logros_nuevos(frame, self.logros[:1], y + 6, ancho)
        self.dibujar_menu(frame)
        return frame


class EscenaPregunta(_EscenaConMenu):
    """Pregunta con varias opciones; cada opción es (etiqueta, función que devuelve la escena)."""

    def __init__(self, ctx, encabezado: str, lineas: list[str], opciones: list[tuple[str, object]]):
        super().__init__(ctx)
        self.encabezado = encabezado
        self.lineas = lineas
        self._opciones = opciones

    def opciones(self) -> list[tuple[str, str]]:
        return [(etq, str(i)) for i, (etq, _) in enumerate(self._opciones)]

    def accion(self, a: str) -> Transicion:
        return self._opciones[int(a)][1]()

    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        x0, x1 = zona_central(W)
        titulo(frame, self.encabezado, 14)
        panel(frame, x0, 100, x1, H - 30, alfa=0.8)
        y = 125
        for l in self.lineas:
            y = parrafo(frame, l, W // 2, y, C.TAM_TEXTO - 6, C.BLANCO, x1 - x0 - 30) + 14
        self.dibujar_menu(frame)
        return frame


# ---------------------------------------------------------------------------
# Historial: ranking, logros y gráfica de evolución
# ---------------------------------------------------------------------------


def grafica_sppb(filas: list[dict], ancho: int = 520, alto: int = 360) -> np.ndarray:
    """Gráfica de la SPPB total por sesión (matplotlib → imagen BGR)."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    valores = []
    for f in filas:
        if f.get("modo") == "evaluacion" and f.get("sppb_total", "") != "":
            valores.append((f.get("fecha", "")[:10], float(f["sppb_total"])))
    fig = Figure(figsize=(ancho / 100, alto / 100), dpi=100)
    fig.patch.set_facecolor("#1e1e28")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#1e1e28")
    if valores:
        xs = list(range(1, len(valores) + 1))
        ax.plot(xs, [v for _, v in valores], marker="o", color="#f0c040", linewidth=2)
        ax.set_xticks(xs)
        ax.set_xticklabels([d[5:] for d, _ in valores], rotation=45, fontsize=7, color="white")
    else:
        ax.text(0.5, 0.5, "Sin evaluaciones todavía", ha="center", va="center", color="white",
                transform=ax.transAxes)
    ax.set_ylim(-0.3, 8.3)
    ax.set_yticks(range(0, 9))
    ax.set_title("Evolución SPPB (0-8)", color="white")
    ax.tick_params(colors="white")
    for s in ax.spines.values():
        s.set_color("#888888")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    rgba = np.asarray(canvas.buffer_rgba())
    return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)


def ranking(perfiles: dict, n: int = 5) -> list[tuple[str, int]]:
    """Jugadores ordenados por la suma de sus mejores puntos en cada nivel."""
    filas = [(nombre, int(sum(p.get("puntos_mejores", {}).values()))) for nombre, p in perfiles.items()]
    return sorted(filas, key=lambda x: -x[1])[:n]


class EscenaHistorial(_EscenaConMenu):
    """Ranking local y gráfica de evolución de la SPPB (los logros tienen su propia pantalla)."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.grafica: np.ndarray | None = None
        self.ranking: list[tuple[str, int]] = []
        self.n_sesiones = 0

    def enter(self) -> None:
        filas = self.ctx.almacen.historial(self.ctx.jugador)
        self.n_sesiones = len(filas)
        self._filas = filas
        self.ranking = ranking(self.ctx.almacen.todos_los_perfiles())

    def opciones(self) -> list[tuple[str, str]]:
        return [("Volver", "menu")]

    def accion(self, a: str) -> Transicion:
        return _menu(self.ctx)

    def draw(self, frame: np.ndarray) -> np.ndarray:
        if not hasattr(self, "_filas"):
            self.enter()
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        if self.grafica is None:
            self.grafica = grafica_sppb(self._filas, ancho=max(300, min(800, W - 420)), alto=420)
        titulo(frame, f"Historial de {self.ctx.jugador}", 20)
        texto(frame, f"Sesiones jugadas: {self.n_sesiones}", (W // 2, 88), C.TAM_PEQUENO, C.BLANCO, "centro")
        # Ranking
        x0, y0 = 30, 230                 # debajo del botón Volver (columna izquierda)
        panel(frame, x0, y0, x0 + 330, y0 + 60 + 40 * max(1, len(self.ranking)), alfa=0.75)
        texto(frame, "Ranking local", (x0 + 15, y0 + 10), C.TAM_TEXTO - 4, C.DORADO)
        for i, (nombre, pts) in enumerate(self.ranking):
            color = C.AMARILLO if nombre == self.ctx.jugador else C.BLANCO
            texto(frame, f"{i + 1}. {nombre[:14]}", (x0 + 15, y0 + 55 + i * 40), C.TAM_PEQUENO, color)
            texto(frame, str(pts), (x0 + 315, y0 + 55 + i * 40), C.TAM_PEQUENO, color, "der")
        # Gráfica (a la derecha del ranking)
        if self.grafica is not None:
            g = self.grafica
            gx = min(W - g.shape[1] - 20, 400)
            gy = 125
            if gx >= 0 and gy + g.shape[0] <= H:
                frame[gy:gy + g.shape[0], gx:gx + g.shape[1]] = g
        self.dibujar_menu(frame)
        return frame
