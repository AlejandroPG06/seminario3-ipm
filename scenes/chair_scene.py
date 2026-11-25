"""Escena de la silla (acto 4 «El Hombre Bala» y prueba de la Evaluación).

Fases: instrucciones → cuenta → jugando → (disparo en Aventura) → fin → al_terminar.
Si se pierde de vista la pierna, la prueba se pausa y se repite desde cero
(el cronómetro clínico no admite pausas).
"""
from __future__ import annotations

import math
from typing import Callable

import cv2
import numpy as np

import config as C
from core.calibration import Calibracion, pierna
from core.geometry import angulo, distancia
from core.gestures import DetectorBrazosArriba
from core.pose import MonitorVisibilidad, PoseFrame
from games.chair_counter import ContadorSilla, Ritmo
from games.scoring import distancia_canon, puntos_silla
from scenes.base import Scene, Transicion
from ui.dwell_button import anillo
from ui.hud import TextosFlotantes, mensaje_central, reloj, titulo
from ui.particles import Confeti
from ui import pictograms
from ui.text import panel, texto

FIN_S = 2.5   # s que se muestra el mensaje final


def manos_en_rodillas(pose: PoseFrame, rodilla: int, muslo: float) -> bool:
    """True si alguna muñeca está muy cerca de la rodilla (apoyo con las manos)."""
    if muslo <= 0:
        return False
    for m in (C.MUNECA_IZQ, C.MUNECA_DER):
        if pose.vis(m) >= C.VISIBILIDAD_MIN and distancia(pose.q(m), pose.q(rodilla)) / muslo < C.SILLA_MANOS_RODILLA_MAX:
            return True
    return False


class EscenaSilla(Scene):
    """Cuenta levantadas con el ángulo de rodilla y cronometra."""

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
        self.objetivo = int(self.nivel.get("repeticiones", C.SILLA_REPETICIONES))
        self.limite = float(self.nivel.get("tiempo_limite_s", C.SILLA_TIEMPO_MAX_S))
        self.estrellas_s = self.nivel.get("estrellas_s", (60, 16.69, 13.69))
        ritmo_s = self.nivel.get("ritmo_s") if self.aventura else None
        self.ritmo = Ritmo(float(ritmo_s)) if ritmo_s else None   # nivel «Al ritmo del cañón»
        self.lado = calib.lado
        self.cad, self.rod, self.tob = pierna(self.lado)
        hombro = C.HOMBRO_IZQ if self.lado == "izq" else C.HOMBRO_DER
        self.monitor = MonitorVisibilidad({"pierna": ((self.cad, self.rod, self.tob, hombro),
                                                      "No te veo la pierna: ponte de lado")})
        self.brazos = DetectorBrazosArriba()
        self.textos = TextosFlotantes()
        self.confeti = Confeti(ctx.semilla, ctx.animaciones)
        self.fase = "instrucciones"
        self.t_fase = 0.0
        self.motivo_pausa = ""
        self.resultado: dict | None = None
        self._reiniciar()

    def _reiniciar(self) -> None:
        self.contador = ContadorSilla(manos_invalida=bool(self.nivel.get("manos_falla", False)))
        self.t = 0.0
        self.angulo_rodilla = 0.0
        self.angulo_cadera = 0.0
        self.manos = False
        self.fuera_ritmo = 0

    def _cambiar_fase(self, fase: str) -> None:
        self.fase = fase
        self.t_fase = 0.0

    # -- bucle -----------------------------------------------------------------
    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        self.t_fase += dt
        self.textos.actualizar(dt)
        self.confeti.actualizar(dt)
        gesto = self.brazos.actualizar(pose, dt)
        if pose is not None:
            self.angulo_rodilla = angulo(pose.q(self.cad), pose.q(self.rod), pose.q(self.tob))
            hombro = C.HOMBRO_IZQ if self.lado == "izq" else C.HOMBRO_DER
            self.angulo_cadera = angulo(pose.q(hombro), pose.q(self.cad), pose.q(self.rod))
        if self.fase == "instrucciones":
            if gesto:
                self._empezar_cuenta()
        elif self.fase == "cuenta":
            if self.t_fase >= C.SILLA_CUENTA_ATRAS_S:
                self._cambiar_fase("jugando")
                self.ctx.audio.reproducir("ya")
        elif self.fase == "jugando":
            return self._jugar(pose, dt, gesto)
        elif self.fase == "pausa":
            visible = not self.monitor.actualizar(pose)
            if gesto and visible:
                self._reiniciar()
                self._empezar_cuenta()
        elif self.fase == "disparo":
            if self.t_fase >= C.CANON_VUELO_S:
                self._cambiar_fase("fin")
        elif self.fase == "fin":
            if self.t_fase >= FIN_S:
                return self.al_terminar(self.resultado)
        return None

    def _empezar_cuenta(self) -> None:
        self._cambiar_fase("cuenta")
        self.ctx.audio.reproducir("cuenta")

    def _jugar(self, pose, dt: float, gesto: bool) -> Transicion:
        if self.monitor.actualizar(pose):
            self._pausar(self.monitor.mensaje)
            return None
        if gesto:
            self._pausar("Pausa")
            return None
        t_anterior = self.t
        self.t += dt
        if self.ritmo is not None and self.ritmo.golpe(t_anterior, self.t):
            self.ctx.audio.reproducir("tambor")
        if pose is not None:
            self.manos = manos_en_rodillas(pose, self.rod, self.calib.longitud_muslo)
            rep = self.contador.actualizar(self.angulo_rodilla, dt, self.manos)
            if rep is not None and self.ritmo is not None and rep.calidad != "Incompleta" \
                    and not self.ritmo.al_ritmo(self.t):
                rep = self.contador.anular_ultima()        # de pie fuera del golpe: no carga el cañón
                self.fuera_ritmo += 1
            if rep is not None:
                x, y = pose.px(self.rod)
                color = {"Perfecta": C.VERDE, "Buena": C.AMARILLO}.get(rep.calidad, C.NARANJA)
                txt = f"¡{rep.calidad}!" + (" (manos)" if rep.manos else "")
                if self.ritmo is not None and rep.calidad in ("Perfecta", "Buena"):
                    txt, color = "¡Al ritmo!", C.VERDE
                self.textos.anadir(txt, (x, y - 80), color)
                self.ctx.audio.reproducir("acierto" if rep.calidad != "Incompleta" else "fallo")
        if self.contador.cuenta >= self.objetivo:
            return self._terminar(self.t)
        if self.t >= self.limite:
            return self._terminar(None)
        return None

    def _pausar(self, motivo: str) -> None:
        self.motivo_pausa = motivo
        self._cambiar_fase("pausa")
        self.ctx.audio.reproducir("fallo")

    def _terminar(self, tiempo: float | None) -> Transicion:
        reps = self.contador.repeticiones
        self.resultado = {
            "prueba": "silla",
            "tiempo": tiempo,
            "completado": tiempo is not None,
            "repeticiones": len(reps),
            "objetivo": self.objetivo,
            "reps": reps,
            "incompletas": len(self.contador.incompletas),
            "manos": any(r.manos for r in reps),
            "puntos": puntos_silla(reps, tiempo, self.estrellas_s[-1]) if self.aventura else 0,
            "distancia": self._distancia(tiempo) if self.aventura else 0.0,
            "fuera_ritmo": self.fuera_ritmo,
            "ritmo": self.ritmo is not None,
            "motivo": "¡Conseguido!" if tiempo is not None else "Se acabó el tiempo",
        }
        if self.aventura and tiempo is not None:
            self.ctx.audio.reproducir("canon")
            self._cambiar_fase("disparo")
        else:
            self.ctx.audio.reproducir("aplausos" if tiempo is not None else "fallo")
            self._cambiar_fase("fin")
        if tiempo is not None:
            self.confeti.lanzar(self.pose.ancho if self.pose is not None else 1280)
        return None

    def _distancia(self, tiempo: float | None) -> float:
        """Metros de vuelo: por tiempo o, con ritmo, por la proporción de levantadas al ritmo."""
        if self.ritmo is None or tiempo is None:
            return distancia_canon(tiempo)
        buenas = self.contador.cuenta
        return max(5.0, C.CANON_DISTANCIA_MAX_M * buenas / max(1, buenas + self.fuera_ritmo))

    def on_key(self, tecla: str) -> Transicion:
        if tecla == "esc":
            return self.al_cancelar()
        if self.fase == "instrucciones" and tecla == "enter":
            self._empezar_cuenta()
        elif self.fase == "jugando" and tecla == "p":
            self._pausar("Pausa")
        elif self.fase == "pausa" and tecla in ("p", "enter"):
            self._reiniciar()
            self._empezar_cuenta()
        elif self.fase == "jugando" and tecla == "f":
            return self._terminar(None)
        elif self.fase in ("fin", "disparo") and tecla == "enter" and self.resultado is not None:
            return self.al_terminar(self.resultado)
        return None

    # -- dibujo ----------------------------------------------------------------
    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        if self.aventura:
            self._dibujar_canon(frame)
        if self.fase == "instrucciones":
            modo = {"evaluacion": "Evaluación", "practica": "Práctica"}.get(self.modo, "")
            encabezado = self.acto.get("nombre") if self.aventura else C.NOMBRES_PRUEBA["silla"]
            subtitulo = (self.nivel.get("nombre", "") if self.aventura else modo) + " · Lo más rápido que puedas"
            linea = f"{C.INSTRUCCION_CORTA['silla']} · {self.objetivo} veces"
            if self.ritmo is not None:
                linea = f"De pie justo al sonar el tambor · {self.objetivo} veces"
                subtitulo = (self.nivel.get("nombre", "") + f" · Un golpe cada {self.ritmo.periodo:.0f} s"
                             " · Sin apoyar las manos")
            pictograms.instrucciones(frame, "silla", encabezado, linea, self.t_fase,
                                     self.brazos.progreso, subtitulo, self.ctx.sprites)
        elif self.fase == "cuenta":
            restante = max(0.0, C.SILLA_CUENTA_ATRAS_S - self.t_fase)
            pictograms.cuenta_atras(frame, restante, "silla", self.t_fase, self.ctx.sprites)
            texto(frame, "Siéntate · brazos cruzados", (W // 2, H // 2 + 90), C.TAM_TITULO - 6, C.BLANCO, "centro")
        elif self.fase in ("jugando", "pausa"):
            reloj(frame, (W - 80, 80), self.limite - self.t, self.limite)
            panel(frame, 10, 10, 360, 120)
            texto(frame, f"Levantadas: {self.contador.cuenta}/{self.objetivo}", (24, 18), 34, C.AMARILLO)
            texto(frame, f"Tiempo: {self.t:.2f} s", (24, 64), 30, C.BLANCO)
            if self.manos:
                texto(frame, "¡Sin manos en las rodillas!", (W // 2, H - 100), C.TAM_TEXTO + 6, C.NARANJA, "centro")
            if self.ritmo is not None and self.fase == "jugando":
                self._dibujar_ritmo(frame)
            if self.fase == "pausa":
                pictograms.pausa(frame, self.motivo_pausa, repetir=True)
        elif self.fase == "disparo":
            pass
        elif self.fase == "fin" and self.resultado is not None:
            r = self.resultado
            lineas = [r["motivo"]]
            if r["tiempo"] is not None:
                lineas.append(f"{r['repeticiones']} levantadas en {r['tiempo']:.2f} s")
            if self.aventura and r["tiempo"] is not None:
                lineas.append(f"¡Has volado {r['distancia']:.0f} m!")
            mensaje_central(frame, lineas, C.VERDE if r["completado"] else C.NARANJA, C.TAM_TITULO - 12)
        self.textos.dibujar(frame)
        self.confeti.dibujar(frame)
        return frame

    def _dibujar_ritmo(self, frame) -> None:
        """Tambor arriba en el centro: el anillo se llena hasta el golpe y se pone verde en la ventana válida."""
        H, W = frame.shape[:2]
        centro = (W // 2, 100)
        en_ventana = self.ritmo.al_ritmo(self.t) and self.t >= self.ritmo.periodo - self.ritmo.tolerancia
        color = C.VERDE if en_ventana else C.AMARILLO
        cv2.circle(frame, centro, 62, (30, 30, 30), -1, cv2.LINE_AA)
        anillo(frame, centro, 54, self.ritmo.fase(self.t), color, 12)
        self.ctx.sprites.tambor(frame, (centro[0], centro[1] + 2), 28, 1.0 if en_ventana else 0.0)
        texto(frame, "¡ARRIBA!" if en_ventana else "Prepárate…", (W // 2, 170), C.TAM_TEXTO,
              C.VERDE if en_ventana else C.BLANCO, "centro")
        if self.fuera_ritmo:
            texto(frame, f"Fuera de ritmo: {self.fuera_ritmo}", (24, 130), C.TAM_PEQUENO, C.NARANJA)

    def _dibujar_canon(self, frame) -> None:
        H, W = frame.shape[:2]
        base = (int(W * 0.12), int(H * 0.72))
        carga = self.contador.cuenta / max(1, self.objetivo)
        self.ctx.sprites.canon(frame, base, W * 0.11, carga)
        if self.fase == "disparo" and self.resultado is not None:
            f = min(1.0, self.t_fase / C.CANON_VUELO_S)
            alcance = W * 0.8 * min(1.0, self.resultado["distancia"] / C.CANON_DISTANCIA_MAX_M)
            x = base[0] + alcance * f
            y = base[1] - math.sin(math.pi * f) * H * 0.55
            ang = -60 + 120 * f
            self.ctx.sprites.hombre_bala(frame, (x, y), W * 0.06, ang)

    def debug_info(self) -> dict[str, str]:
        return {"fase": self.fase, "estado": str(self.contador.estado),
                "rodilla": f"{self.angulo_rodilla:.0f}°", "cadera": f"{self.angulo_cadera:.0f}°",
                "lado": self.lado, "manos": str(self.manos),
                "reps": f"{self.contador.cuenta} (+{len(self.contador.incompletas)} incompl.)"}
