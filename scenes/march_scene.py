"""Escena de la marcha en el sitio: acto 4 «El Desfile» y prueba complementaria.

Fases: instrucciones → cuenta → jugando ⇄ pausa → fin → al_terminar(resultado).
Se dibuja una línea a la altura objetivo de cada rodilla (la mitad entre la
rodilla y la cadera en reposo, como en el 2-Minute Step Test). En Aventura hay
un tambor y, si el nivel tiene tempo, un metrónomo para ir «al compás».
"""
from __future__ import annotations

from typing import Callable

import cv2
import numpy as np

import config as C
from core.calibration import Calibracion
from core.geometry import punto_medio
from core.gestures import DetectorBrazosArriba
from core.pose import MonitorVisibilidad
from games.hazards import Burbujas
from games.march import ContadorMarcha, elevacion
from games.scoring import puntos_marcha
from scenes.base import Scene, Transicion
from ui.dwell_button import anillo
from ui.hud import TextosFlotantes, mensaje_central, reloj, titulo
from ui.particles import Confeti
from ui import pictograms
from ui.text import panel, texto

FIN_S = 2.5   # s que se muestra el mensaje final
ENCABEZADO_MODO = {"evaluacion": "Evaluación", "practica": "Práctica"}


class EscenaMarcha(Scene):
    """Cuenta pasos (rodilla hasta la línea) durante un tiempo fijo."""


    def __init__(self, ctx, calib: Calibracion, modo: str,
                 al_terminar: Callable[[dict], Scene], al_cancelar: Callable[[], Scene],
                 nivel: dict | None = None, acto: dict | None = None):
        super().__init__(ctx)
        self.calib = calib
        self.modo = modo
        self.aventura = modo == "aventura"
        self.nivel = nivel or {}
        self.acto = acto or {}
        self.al_terminar = al_terminar
        self.al_cancelar = al_cancelar
        self.duracion = float(self.nivel.get("duracion_s", C.MARCHA_EVAL_S))
        self.tempo = float(self.nivel.get("tempo_bpm", 0)) if self.aventura else 0.0
        if self.tempo:   # música al mismo tempo que el metrónomo, para ir al compás
            self.pista_musica = f"musica_{int(self.tempo)}"
        self.brazos = DetectorBrazosArriba()
        self.monitor = MonitorVisibilidad(C.GRUPOS_CLAVE_MARCHA)
        self.textos = TextosFlotantes()
        self.confeti = Confeti(ctx.semilla, ctx.animaciones)
        rng = np.random.default_rng(ctx.semilla)
        self.burbujas = Burbujas(rng) if (self.aventura and self.nivel.get("burbujas")) else None
        self.fase = "instrucciones"
        self.t_fase = 0.0
        self.motivo_pausa = ""
        self.resultado: dict | None = None
        self.elev = (0.0, 0.0)
        self.golpe = 0.0            # 0-1, animación del tambor
        self._pulso_anterior = 0.0
        self._reiniciar()

    def _reiniciar(self) -> None:
        self.contador = ContadorMarcha(self.tempo)
        self.puntos_extra = 0

    def _cambiar_fase(self, fase: str) -> None:
        self.fase = fase
        self.t_fase = 0.0

    @property
    def t(self) -> float:
        return self.contador.t

    def _elevaciones(self, pose) -> tuple[float, float]:
        ry = self.calib.rodillas_y
        cy = self.calib.cadera_y
        return (elevacion(pose.p(C.RODILLA_IZQ)[1], ry[0], cy),
                elevacion(pose.p(C.RODILLA_DER)[1], ry[1], cy))

    # -- bucle -----------------------------------------------------------------
    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        self.t_fase += dt
        self.textos.actualizar(dt)
        self.confeti.actualizar(dt)
        self.golpe = max(0.0, self.golpe - dt * 4)
        gesto = self.brazos.actualizar(pose, dt)
        if pose is not None:
            self.elev = self._elevaciones(pose)
        if self.fase == "instrucciones":
            if gesto:
                self._empezar_cuenta()
        elif self.fase == "cuenta":
            if self.t_fase >= C.CUENTA_ATRAS_S:
                self._cambiar_fase("jugando")
                self.ctx.audio.reproducir("ya")
                if self.tempo:   # el primer pulso de la música coincide con el del contador
                    self.ctx.audio.poner_pista(self.pista_musica, reiniciar=True)
        elif self.fase == "jugando":
            return self._jugar(pose, dt, gesto)
        elif self.fase == "pausa":
            visible = not self.monitor.actualizar(pose)
            if gesto and visible:
                self._reanudar()
        elif self.fase == "fin":
            if self.t_fase >= FIN_S:
                return self.al_terminar(self.resultado)
        return None

    def _empezar_cuenta(self) -> None:
        self._cambiar_fase("cuenta")
        self.ctx.audio.reproducir("cuenta")

    def _pausar(self, motivo: str) -> None:
        self.motivo_pausa = motivo
        self._cambiar_fase("pausa")
        self.ctx.audio.reproducir("fallo")

    def _reanudar(self) -> None:
        if not self.aventura:
            self._reiniciar()          # en Evaluación/Práctica se repite entera
        self._empezar_cuenta()

    def _jugar(self, pose, dt: float, gesto: bool) -> Transicion:
        if self.monitor.actualizar(pose):
            self._pausar(self.monitor.mensaje)
            return None
        if gesto:
            self._pausar("Pausa")
            return None
        if pose is None:
            return None
        for paso in self.contador.actualizar(*self.elev, dt):
            self.golpe = 1.0
            self.ctx.audio.reproducir("tambor")
            if self.aventura and paso.al_compas:
                rod = C.RODILLA_IZQ if paso.pierna == "izq" else C.RODILLA_DER
                x, y = pose.px(rod)
                self.textos.anadir("¡Al compás!", (x, y - 60), C.VERDE)
        if self.tempo:
            fase = self.contador.fase_pulso()
            if fase < self._pulso_anterior and not self.ctx.audio.sonando_musica:
                self.ctx.audio.reproducir("click")   # sin música, el clic marca el ritmo
            self._pulso_anterior = fase
        if self.burbujas is not None:
            self._burbujas(pose, dt)
        if self.t >= self.duracion:
            return self._terminar()
        return None

    def _burbujas(self, pose, dt: float) -> None:
        hombros = punto_medio(pose.px(C.HOMBRO_IZQ), pose.px(C.HOMBRO_DER))
        manos = [pose.px(i) for i in (C.INDICE_IZQ, C.INDICE_DER) if pose.vis(i) >= C.VISIBILIDAD_MIN]
        aw_px = self.calib.anchura_hombros * pose.alto
        for b in self.burbujas.actualizar(dt, manos, tuple(hombros), aw_px, C.BURBUJA_RADIO * pose.ancho,
                                          pose.ancho, pose.alto):
            self.puntos_extra += C.PUNTOS_BURBUJA
            self.textos.anadir(f"+{C.PUNTOS_BURBUJA}", (int(b.x), int(b.y)), C.AMARILLO)
            self.ctx.audio.reproducir("burbuja")

    def _terminar(self) -> Transicion:
        c = self.contador
        self.resultado = {
            "prueba": "marcha",
            "tiempo": min(self.t, self.duracion),
            "completado": True,
            "motivo": "¡Desfile terminado!" if self.aventura else "¡Tiempo!",
            "pasos": c.total,
            "pasos_der": c.pasos_der,
            "al_compas": c.al_compas,
            "puntos": puntos_marcha(c.total, c.al_compas) + self.puntos_extra if self.aventura else 0,
            "burbujas": self.burbujas.tocadas if self.burbujas else 0,
            "viento": False,
            "racha_max_s": 0.0,
        }
        self.confeti.lanzar(self.pose.ancho if self.pose is not None else 1280)
        self.ctx.audio.reproducir("aplausos")
        self._cambiar_fase("fin")
        return None

    def on_key(self, tecla: str) -> Transicion:
        if tecla == "esc":
            return self.al_cancelar()
        if self.fase == "instrucciones" and tecla == "enter":
            self._empezar_cuenta()
        elif self.fase == "jugando" and tecla == "p":
            self._pausar("Pausa")
        elif self.fase == "pausa" and tecla in ("p", "enter"):
            self._reanudar()
        elif self.fase == "fin" and tecla == "enter" and self.resultado is not None:
            return self.al_terminar(self.resultado)
        return None

    # -- dibujo ----------------------------------------------------------------
    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        if self.pose is not None and self.fase in ("cuenta", "jugando"):
            self._dibujar_lineas(frame)
        if self.aventura:
            self.ctx.sprites.tambor(frame, (int(W * 0.13), int(H * 0.72)), H * 0.08, self.golpe)
            if self.tempo and self.fase == "jugando":
                self._dibujar_metronomo(frame)
        if self.burbujas is not None and self.fase == "jugando":
            for b in self.burbujas.items:
                self.ctx.sprites.burbuja(frame, (b.x, b.y), C.BURBUJA_RADIO * W)
        if self.fase == "instrucciones":
            encabezado = self.acto.get("nombre") if self.aventura else C.NOMBRES_PRUEBA["marcha"]
            subtitulo = self.nivel.get("nombre", "") if self.aventura else ENCABEZADO_MODO.get(self.modo, "")
            if self.tempo:
                subtitulo += f" · Al ritmo del tambor ({self.tempo:.0f} pasos/min)"
            linea = f"{C.INSTRUCCION_CORTA['marcha']} · {self.duracion:.0f} s"
            pictograms.instrucciones(frame, "marcha", encabezado, linea, self.t_fase,
                                     self.brazos.progreso, subtitulo, self.ctx.sprites)
        elif self.fase == "cuenta":
            restante = max(0.0, C.CUENTA_ATRAS_S - self.t_fase)
            pictograms.cuenta_atras(frame, restante, "marcha", self.t_fase, self.ctx.sprites)
            texto(frame, "¡A marchar!", (W // 2, H // 2 + 90), C.TAM_TITULO, C.BLANCO, "centro")
        elif self.fase in ("jugando", "pausa"):
            reloj(frame, (W - 80, 80), self.duracion - self.t, self.duracion)
            panel(frame, 10, 10, 360, 130)
            texto(frame, f"Pasos: {self.contador.total}", (24, 18), 34, C.AMARILLO)
            if self.aventura:
                pts = puntos_marcha(self.contador.total, self.contador.al_compas) + self.puntos_extra
                texto(frame, f"Puntos: {pts}", (24, 62), 28, C.BLANCO)
                if self.tempo:
                    texto(frame, f"Al compás: {self.contador.al_compas}", (24, 96), 24, C.VERDE)
            else:
                texto(frame, f"Rodilla derecha: {self.contador.pasos_der}", (24, 62), 26, C.BLANCO)
            if self.fase == "pausa":
                pictograms.pausa(frame, self.motivo_pausa, repetir=not self.aventura)
        elif self.fase == "fin" and self.resultado is not None:
            r = self.resultado
            mensaje_central(frame, [r["motivo"], f"{r['pasos']} pasos"], C.VERDE, C.TAM_TITULO - 8)
        self.textos.dibujar(frame)
        self.confeti.dibujar(frame)
        return frame

    def _dibujar_lineas(self, frame) -> None:
        """Línea objetivo a la altura que debe alcanzar cada rodilla."""
        pose = self.pose
        for i, rod in enumerate((C.RODILLA_IZQ, C.RODILLA_DER)):
            y_obj = self.calib.rodillas_y[i] - C.MARCHA_SUBIDA * (self.calib.rodillas_y[i] - self.calib.cadera_y)
            x = pose.px(rod)[0]
            y = int(y_obj * pose.alto)
            ancho = int(self.calib.anchura_hombros * pose.alto * 0.6)
            arriba = self.elev[i] >= C.MARCHA_SUBIDA
            color = C.VERDE if arriba else C.AMARILLO
            cv2.line(frame, (x - ancho, y), (x + ancho, y), color, 4, cv2.LINE_AA)
            cv2.circle(frame, pose.px(rod), 10, color, -1, cv2.LINE_AA)

    def _dibujar_metronomo(self, frame) -> None:
        """Círculo que late con el ritmo."""
        H, W = frame.shape[:2]
        f = self.contador.fase_pulso()
        r = int(18 + 14 * max(0.0, 1 - f * 3))
        centro = (int(W * 0.13), int(H * 0.52))
        cv2.circle(frame, centro, r, C.AMARILLO, -1, cv2.LINE_AA)
        texto(frame, f"{self.tempo:.0f} ppm", (centro[0], centro[1] + 36), C.TAM_PEQUENO, C.BLANCO, "centro")

    def debug_info(self) -> dict[str, str]:
        c = self.contador
        return {"fase": self.fase, "t": f"{self.t:.1f}/{self.duracion:.0f}",
                "elev izq/dcha": f"{self.elev[0]:.2f} / {self.elev[1]:.2f}",
                "arriba": f"{c.arriba['izq']} / {c.arriba['der']}",
                "pasos": f"{c.total} (dcha {c.pasos_der}, compás {c.al_compas})"}
