"""Escena de equilibrio: actos 1-3 (Aventura), posturas de la Evaluación y de la Práctica.

Fases: instrucciones → cuenta → jugando ⇄ pausa → fin → al_terminar(resultado).
En Evaluación y Práctica no hay mecánicas de juego: solo cronómetro y balanceo.
Con la prueba «una_pierna» el cronómetro corre solo mientras hay un pie
levantado y la prueba termina cuando ese pie vuelve al suelo.
"""
from __future__ import annotations

from typing import Callable

import cv2
import numpy as np

import config as C
from core.calibration import Calibracion, centro_cadera
from core.geometry import ema, punto_medio
from core.gestures import DetectorBrazosArriba
from core.pose import MonitorVisibilidad
from games.hazards import Burbujas, Viento
from games.one_leg import APOYADO, DetectorUnaPierna
from games.posture import VigilantePies, separacion_pies, verificar_postura
from games.scoring import MarcadorEquilibrio, estrellas_por_peligro, estrellas_silla
from games.tightrope import CuerdaFloja
from games.tray import Bandeja
from scenes.base import Scene, Transicion
from ui.hud import (TextosFlotantes, barra_balanceo, estrellas_en_juego, marcador, mensaje_central, reloj,
                    semaforo, titulo)
from ui.particles import Confeti
from ui import pictograms
from ui.sprites import rotar
from ui.text import texto

FIN_S = 2.5   # s que se muestra el mensaje final antes de pasar a resultados
ENCABEZADO_MODO = {"evaluacion": "Evaluación", "practica": "Práctica"}


def duracion_clinica(prueba: str) -> float:
    """Duración de la prueba en Evaluación/Práctica (s)."""
    return C.UNA_PIERNA_EVAL_S if prueba == "una_pierna" else C.PRUEBA_EQUILIBRIO_S


class EscenaEquilibrio(Scene):
    """Prueba de equilibrio parametrizada por postura, modo y nivel."""

    def __init__(self, ctx, calib: Calibracion, prueba: str, modo: str,
                 al_terminar: Callable[[dict], Scene], al_cancelar: Callable[[], Scene],
                 nivel: dict | None = None, acto: dict | None = None):
        super().__init__(ctx)
        self.calib = calib
        self.prueba = prueba
        self.modo = modo                      # "evaluacion", "practica" o "aventura"
        self.aventura = modo == "aventura"
        self.una_pierna = prueba == "una_pierna"
        self.nivel = nivel or {}
        self.acto = acto or {}
        self.al_terminar = al_terminar
        self.al_cancelar = al_cancelar
        self.objetivo = float(self.nivel.get("duracion_s", duracion_clinica(prueba)))
        self.mecanica = self.acto.get("mecanica") if self.aventura else None
        self.cruzar = self.mecanica == "cuerda" and bool(self.nivel.get("cruzar"))
        self.avance_s = float(self.nivel.get("avance_s", self.objetivo))
        self.brazos = DetectorBrazosArriba()
        self.monitor = MonitorVisibilidad(C.GRUPOS_CLAVE_EQUILIBRIO)
        self.textos = TextosFlotantes()
        self.confeti = Confeti(ctx.semilla, ctx.animaciones)
        rng = np.random.default_rng(ctx.semilla)
        fuerza = float(self.nivel.get("viento", 0.0)) if self.aventura else 0.0
        self.viento = Viento(fuerza, rng)
        self.burbujas = Burbujas(rng) if (self.aventura and self.nivel.get("burbujas")) else None
        self.fase = "instrucciones"
        self.t_fase = 0.0
        self.aviso_postura = ""
        self.motivo_pausa = ""
        self.resultado: dict | None = None
        self._reiniciar_prueba()

    # -- estado ----------------------------------------------------------------
    def _reiniciar_prueba(self) -> None:
        self.t = 0.0
        self.marcador = MarcadorEquilibrio()
        self.bandeja = Bandeja(int(self.nivel.get("objetos", 1)))
        ganancia = C.PELOTA_GANANCIA if self.mecanica == "pelota" else C.CUERDA_GANANCIA
        inestabilidad = float(self.nivel.get("inestabilidad", 0.0)) if self.aventura else 0.0
        zona = C.CUERDA_ZONA_MUERTA if inestabilidad > 0 else C.ZONA_MUERTA_BALANCEO
        self.cuerda = CuerdaFloja(ganancia=ganancia, inestabilidad=inestabilidad, zona=zona,
                                  rng=np.random.default_rng(self.ctx.semilla))   # también para la pelota
        self.avance = 0.0            # 0-1, «Cruza la cuerda»
        self.pierna = DetectorUnaPierna()
        self.vigilante: VigilantePies | None = None
        self.cadera_ref = self.calib.cadera_x
        self._cadera_media: float | None = None
        self.balanceo = 0.0
        self._balanceo_suave: float | None = None
        self.puntos_extra = 0
        self.peligro_max = 0.0       # 0-1, lo más cerca que ha estado de caerse (da las estrellas)

    def _cambiar_fase(self, fase: str) -> None:
        self.fase = fase
        self.t_fase = 0.0

    def _tobillos(self, pose) -> np.ndarray:
        return np.array([pose.q(C.TOBILLO_IZQ), pose.q(C.TOBILLO_DER)])

    def _actualizar_balanceo(self, pose) -> None:
        if pose is None:
            return
        # x normalizada → isótropa (× aspecto) para dividir por la anchura de hombros
        crudo = (centro_cadera(pose)[0] - self.cadera_ref) * pose.aspecto / self.calib.anchura_hombros
        self._balanceo_suave = ema(self._balanceo_suave, crudo, C.BALANCEO_EMA_ALFA)
        self.balanceo = self._balanceo_suave

    # -- bucle -----------------------------------------------------------------
    def update(self, pose, dt) -> Transicion:
        super().update(pose, dt)
        self.t_fase += dt
        self.textos.actualizar(dt)
        self.confeti.actualizar(dt)
        gesto = self.brazos.actualizar(pose, dt)
        if pose is not None and pose.visibles((C.TOBILLO_IZQ, C.TOBILLO_DER)):
            dx, dy = separacion_pies(self._tobillos(pose), self.calib.anchura_hombros)
            _, self.aviso_postura = verificar_postura(self.prueba, dx, dy)
        if self.fase == "instrucciones":
            if gesto:
                return self._intentar_empezar()
        elif self.fase == "cuenta":
            if pose is not None:
                self._cadera_media = ema(self._cadera_media, float(centro_cadera(pose)[0]), C.REFERENCIA_EMA_ALFA)
            if self.t_fase >= C.CUENTA_ATRAS_S:
                self._empezar_a_jugar(pose)
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

    def _intentar_empezar(self) -> Transicion:
        if C.VERIFICACION_POSTURA_ESTRICTA and self.aviso_postura:
            x = self.pose.ancho // 2 if self.pose is not None else 640
            self.textos.anadir(self.aviso_postura, (x, 300), C.AMARILLO)
            return None
        self._cambiar_fase("cuenta")
        self.ctx.audio.reproducir("cuenta")
        return None

    def _empezar_a_jugar(self, pose) -> None:
        if pose is not None:
            self.cadera_ref = self._cadera_media if self._cadera_media is not None else float(centro_cadera(pose)[0])
            if not self.una_pierna:   # con un pie levantado los tobillos se mueven por diseño
                self.vigilante = VigilantePies(self._tobillos(pose), self.calib.anchura_hombros)
        self._balanceo_suave = 0.0
        self.balanceo = 0.0
        self._cambiar_fase("jugando")
        self.ctx.audio.reproducir("ya")

    def _pausar(self, motivo: str) -> None:
        self.motivo_pausa = motivo
        self._cambiar_fase("pausa")
        self.ctx.audio.reproducir("fallo")

    def _reanudar(self) -> None:
        if not self.aventura:
            self._reiniciar_prueba()   # en Evaluación/Práctica la prueba se repite entera
        self.pierna = DetectorUnaPierna()   # el pie pudo bajar durante la pausa
        self._cambiar_fase("cuenta")
        self.ctx.audio.reproducir("cuenta")

    def _jugar(self, pose, dt: float, gesto: bool) -> Transicion:
        if self.monitor.actualizar(pose):
            self._pausar(self.monitor.mensaje)
            return None
        if gesto:
            self._pausar("Pausa")
            return None
        if pose is None:
            return None
        self._actualizar_balanceo(pose)
        if self.una_pierna:
            tob = self._tobillos(pose)
            if self.pierna.actualizar(tob[0, 1], tob[1, 1], self.calib.anchura_hombros) == APOYADO:
                return self._terminar(False, "Has apoyado el pie")
            if not self.pierna.levantado:
                return None          # el cronómetro empieza al levantar el pie
        self.t += dt
        if self.vigilante is not None and self.vigilante.actualizar(self._tobillos(pose)):
            return self._terminar(False, "Has movido los pies")
        eventos = self.marcador.actualizar(dt, abs(self.balanceo), self.balanceo)
        if self.aventura:
            caido = self._mecanica(pose, dt)
            if caido:
                mensaje = {"cuerda": "¡Se ha caído!", "pelota": "¡Se ha caído de la pelota!"}
                return self._terminar(False, mensaje.get(self.mecanica, "¡Se ha caído el vaso!"))
            if self.cruzar:
                if self.cuerda.peligro < C.CRUZAR_PELIGRO_MAX:
                    self.avance = min(1.0, self.avance + dt / self.avance_s)
                if self.avance >= 1.0:
                    return self._terminar(True, "¡Has cruzado la cuerda!")
            for ev in eventos:
                if ev == "pulso_acero":
                    self.textos.anadir("¡Pulso de acero! x2", (pose.px(C.NARIZ)[0], 250), C.VERDE)
                elif ev == "racha":
                    self.textos.anadir(f"¡Racha! x{self.marcador.mult_racha:.2f}", (pose.px(C.NARIZ)[0], 300), C.AMARILLO)
                    self.ctx.audio.reproducir("acierto")
        if self.t >= self.objetivo:
            if self.cruzar:
                return self._terminar(False, "Se acabó el tiempo")
            return self._terminar(True, "¡Conseguido!")
        return None

    def _mecanica(self, pose, dt: float) -> bool:
        """Actualiza viento, bandeja/cuerda y burbujas. True si se ha caído."""
        viento = self.viento.actualizar(dt)
        if self.viento.nueva_rafaga:
            self.textos.anadir("¡Ráfaga de viento!", (pose.ancho // 2, 350), C.AZUL)
        if self.burbujas is not None:
            hombros = punto_medio(pose.px(C.HOMBRO_IZQ), pose.px(C.HOMBRO_DER))
            manos = [pose.px(i) for i in (C.INDICE_IZQ, C.INDICE_DER) if pose.vis(i) >= C.VISIBILIDAD_MIN]
            aw_px = self.calib.anchura_hombros * pose.alto
            radio = C.BURBUJA_RADIO * pose.ancho
            for b in self.burbujas.actualizar(dt, manos, tuple(hombros), aw_px, radio, pose.ancho, pose.alto):
                self.puntos_extra += C.PUNTOS_BURBUJA
                self.textos.anadir(f"+{C.PUNTOS_BURBUJA}", (int(b.x), int(b.y)), C.AMARILLO)
                self.ctx.audio.reproducir("burbuja")
        modelo = self.cuerda if self.mecanica in ("cuerda", "pelota") else self.bandeja
        caido = modelo.actualizar(self.balanceo, dt, viento)
        self.peligro_max = max(self.peligro_max, 1.0 if caido else modelo.peligro)
        return caido

    def estrellas_posibles(self) -> int:
        """Estrellas que aún se pueden conseguir (en «Cruza la cuerda» dependen del tiempo)."""
        if self.cruzar:
            return estrellas_silla(self.t, tuple(self.nivel["estrellas_s"]))
        return estrellas_por_peligro(self.peligro_max, self.umbrales_estrellas)

    @property
    def umbrales_estrellas(self) -> tuple[float, float]:
        return tuple(self.nivel.get("estrellas_peligro", C.ESTRELLAS_PELIGRO))

    def _terminar(self, completado: bool, mensaje: str) -> Transicion:
        self.resultado = {
            "prueba": self.prueba,
            "tiempo": min(self.t, self.objetivo) if completado else self.t,
            "completado": completado,
            "motivo": mensaje,
            "puntos": int(self.marcador.puntos) + self.puntos_extra,
            "balanceo_medio": self.marcador.balanceo_medio,
            "balanceo_signo": self.marcador.balanceo_medio_signo,
            "peligro_max": self.peligro_max,
            "cruzar": self.cruzar,
            "avance": self.avance,
            "racha_max_s": self.marcador.racha_max_s,
            "burbujas": self.burbujas.tocadas if self.burbujas else 0,
            "viento": self.viento.fuerza > 0,
        }
        if completado:
            self.confeti.lanzar(self.pose.ancho if self.pose else 1280)
            self.ctx.audio.reproducir("aplausos")
        else:
            self.ctx.audio.reproducir("fallo")
        self._cambiar_fase("fin")
        return None

    def on_key(self, tecla: str) -> Transicion:
        if tecla == "esc":
            return self.al_cancelar()
        if self.fase == "instrucciones" and tecla == "enter":
            return self._intentar_empezar()
        if self.fase == "jugando" and tecla == "p":
            self._pausar("Pausa")
        elif self.fase == "pausa" and tecla in ("p", "enter"):
            self._reanudar()
        elif self.fase == "jugando" and tecla == "f":
            return self._terminar(False, "Pérdida de equilibrio (marcada a mano)")
        elif self.fase == "fin" and tecla == "enter" and self.resultado is not None:
            return self.al_terminar(self.resultado)
        return None

    # -- dibujo ----------------------------------------------------------------
    def draw(self, frame: np.ndarray) -> np.ndarray:
        frame = self.fondo(frame)
        H, W = frame.shape[:2]
        nombre = C.NOMBRES_PRUEBA[self.prueba]
        if self.aventura and self.pose is not None and self.fase in ("cuenta", "jugando", "pausa", "fin"):
            self._dibujar_mecanica(frame)
        if self.fase == "jugando" and self.viento.activa:
            self._dibujar_viento(frame)
        elif self.fase == "jugando" and self.nivel.get("aviso_viento") and self.viento.aviso():
            self._dibujar_aviso_viento(frame)
        if self.fase == "jugando" and self.mecanica in ("cuerda", "pelota") and self.pose is not None:
            self._dibujar_correccion(frame)
        if self.burbujas is not None and self.fase == "jugando":
            for b in self.burbujas.items:
                self.ctx.sprites.burbuja(frame, (b.x, b.y), C.BURBUJA_RADIO * W)
        if self.fase == "instrucciones":
            encabezado = self.acto.get("nombre") if self.aventura else nombre
            subtitulo = self.nivel.get("nombre", "") if self.aventura else ENCABEZADO_MODO.get(self.modo, "")
            if self.una_pierna:
                subtitulo += " · " + C.AVISO_SEGURIDAD
            linea = f"{C.INSTRUCCION_CORTA[self.prueba]} · {self.objetivo:.0f} s"
            if self.cruzar:
                linea = f"Quieto para avanzar · cruza en {self.objetivo:.0f} s"
            if self.aventura and self.nivel.get("inestabilidad", 0) > C.CUERDA_RIGIDEZ:
                subtitulo += " · Si se inclina, mueve la cadera hacia la flecha"
            pictograms.instrucciones(frame, self.prueba, encabezado, linea, self.t_fase,
                                     self.brazos.progreso, subtitulo, self.ctx.sprites)
            if self.aviso_postura:
                texto(frame, self.aviso_postura, (W // 2, H - 150), C.TAM_TEXTO, C.AMARILLO, "centro")
        elif self.fase == "cuenta":
            restante = max(0.0, C.CUENTA_ATRAS_S - self.t_fase)
            pictograms.cuenta_atras(frame, restante, self.prueba, self.t_fase, self.ctx.sprites)
            aviso = "¡Levanta un pie!" if self.una_pierna else "¡Colócate!"
            texto(frame, aviso, (W // 2, H // 2 + 90), C.TAM_TITULO, C.BLANCO, "centro")
        elif self.fase in ("jugando", "pausa"):
            reloj(frame, (W - 80, 80), self.objetivo - self.t, self.objetivo)
            if self.aventura:
                marcador(frame, int(self.marcador.puntos) + self.puntos_extra,
                         self.marcador.racha_s, self.marcador.multiplicador)
                semaforo(frame, W - 80, 160, abs(self.balanceo))
                estrellas_en_juego(frame, (170, 160), self.estrellas_posibles(), self.ctx.sprites)
            else:
                titulo(frame, nombre, 20)
                barra_balanceo(frame, W // 2, H - 50, self.balanceo)
            pictograms.recordatorio(frame, self.prueba, self.t_fase, self.ctx.sprites)
            if self.una_pierna and self.fase == "jugando" and not self.pierna.levantado:
                texto(frame, "¡Levanta un pie!", (W // 2, H // 2 - 40), C.TAM_TITULO + 10, C.AMARILLO, "centro")
            if self.fase == "pausa":
                pictograms.pausa(frame, self.motivo_pausa, repetir=not self.aventura)
        elif self.fase == "fin" and self.resultado is not None:
            color = C.VERDE if self.resultado["completado"] else C.NARANJA
            mensaje_central(frame, [self.resultado["motivo"], f"Tiempo: {self.resultado['tiempo']:.1f} s"], color, C.TAM_TITULO - 8)
        self.textos.dibujar(frame)
        self.confeti.dibujar(frame)
        return frame

    def _dibujar_viento(self, frame) -> None:
        """Flechas horizontales en la dirección de la ráfaga."""
        H, W = frame.shape[:2]
        d = self.viento.direccion
        largo = int(80 + 120 * min(1.0, abs(self.viento.valor) / max(self.viento.fuerza, 1e-6)))
        for y in (int(H * 0.35), int(H * 0.5), int(H * 0.65)):
            x0 = int(W * 0.12) if d > 0 else int(W * 0.88)
            cv2.arrowedLine(frame, (x0, y), (x0 + d * largo, y), C.AZUL, 6, cv2.LINE_AA, tipLength=0.3)

    def _dibujar_aviso_viento(self, frame) -> None:
        """Un segundo antes de la ráfaga: flechas parpadeantes desde el lado del que vendrá."""
        H, W = frame.shape[:2]
        if int(self.t_fase * 6) % 2:
            return
        d = self.viento.direccion
        x0 = int(W * 0.06) if d > 0 else int(W * 0.94)
        for y in (int(H * 0.4), int(H * 0.55)):
            cv2.arrowedLine(frame, (x0, y), (x0 + d * 90, y), C.AMARILLO, 5, cv2.LINE_AA, tipLength=0.35)
        lado = "izquierda" if d > 0 else "derecha"
        texto(frame, f"¡Viento por la {lado}!", (W // 2, int(H * 0.80)), C.TAM_TEXTO + 4, C.AMARILLO, "centro")

    def _dibujar_correccion(self, frame) -> None:
        """Flecha junto a la cadera hacia donde hay que moverla para enderezar al funambulista."""
        sentido = self.cuerda.correccion
        if sentido == 0:
            return
        cadera = punto_medio(self.pose.px(C.CADERA_IZQ), self.pose.px(C.CADERA_DER))
        x, y = int(cadera[0]), int(cadera[1])
        largo = int(60 + 80 * self.cuerda.peligro)
        color = C.NARANJA if self.cuerda.peligro > 0.65 else C.AMARILLO
        cv2.arrowedLine(frame, (x - sentido * 20, y), (x + sentido * largo, y), (30, 30, 30), 16, cv2.LINE_AA,
                        tipLength=0.4)
        cv2.arrowedLine(frame, (x - sentido * 20, y), (x + sentido * largo, y), color, 10, cv2.LINE_AA,
                        tipLength=0.4)

    def _dibujar_mecanica(self, frame) -> None:
        pose = self.pose
        sp = self.ctx.sprites
        hombros = punto_medio(pose.px(C.HOMBRO_IZQ), pose.px(C.HOMBRO_DER))
        aw_px = self.calib.anchura_hombros * pose.alto
        torso_px = self.calib.altura_torso * pose.alto
        pecho = (hombros[0], hombros[1] + torso_px * 0.35)
        if self.mecanica == "cuerda":
            self._dibujar_cuerda(frame, pecho, aw_px)
            return
        if self.mecanica == "pelota":
            self._dibujar_pelota(frame)
            return
        b = self.bandeja
        ancho = aw_px * 2.4
        sp.bandeja(frame, pecho, ancho, b.inclinacion)
        alto_obj = aw_px * (0.55 if b.objetos == 1 else 0.38)
        x_local = b.x * ancho / 2
        caida = 0.0
        if b.caido and self.fase == "fin":
            caida = 600 * self.t_fase ** 2          # animación de caída (px)
            x_local += np.sign(b.x) * 300 * self.t_fase
        base = rotar([(x_local, -8)], b.inclinacion, pecho)[0]
        base = (base[0], base[1] + caida)
        ang = b.inclinacion + b.inclinacion_pila
        malabares = self.acto.get("objetos_apilados") == "malabares"
        for i in range(b.objetos):
            sp.objeto(frame, base, alto_obj, ang, i + 1 if malabares else 0)
            base = rotar([(0, -alto_obj)], ang, base)[0]
            ang += b.inclinacion_pila * 0.3

    def _dibujar_cuerda(self, frame, pecho, aw_px: float) -> None:
        H, W = frame.shape[:2]
        c = self.cuerda
        pies_y = int(max(self.pose.px(C.TOBILLO_IZQ)[1], self.pose.px(C.TOBILLO_DER)[1]) + 10)
        self.ctx.sprites.cuerda(frame, int(W * 0.05), int(W * 0.95), min(pies_y, H - 20), c.amplitud_cuerda, c.fase)
        L = aw_px * 2.2   # pértiga anclada al pecho
        pts = rotar([(-L, aw_px * 0.15), (0, 0), (L, aw_px * 0.15)], c.angulo, pecho).astype(np.int32)
        cv2.polylines(frame, [pts], False, (40, 90, 140), 8, cv2.LINE_AA)
        for e in (pts[0], pts[2]):
            cv2.circle(frame, tuple(int(v) for v in e), 14, C.DORADO, -1, cv2.LINE_AA)
        # Mini funambulista que cruza la cuerda: según el tiempo o, en «Cruza la cuerda», según la estabilidad
        x0, x1, y = int(W * 0.32), int(W * 0.72), 150
        self.ctx.sprites.cuerda(frame, x0, x1, y, c.amplitud_cuerda * 0.3, c.fase, postes=25)
        avance = self.avance if self.cruzar else min(1.0, self.t / self.objetivo)
        self.ctx.sprites.funambulista(frame, (x0 + (x1 - x0) * avance, y), 90, c.angulo)
        if self.cruzar and self.fase == "jugando":
            parado = c.peligro >= C.CRUZAR_PELIGRO_MAX
            txt = "¡Quieto para avanzar!" if parado else f"Cruzando: {avance * 100:.0f} %"
            texto(frame, txt, (W // 2, y + 30), C.TAM_TEXTO - 2, C.NARANJA if parado else C.VERDE, "centro")

    def _dibujar_pelota(self, frame) -> None:
        """Bailarina sobre una pelota gigante, a la izquierda para no tapar al jugador."""
        H, W = frame.shape[:2]
        c = self.cuerda
        radio = int(H * 0.09)
        centro = (int(W * 0.14 + c.angulo * 1.5), int(H * 0.68))
        self.ctx.sprites.pelota(frame, centro, radio, c.angulo * 4)
        pies = (centro[0], centro[1] - radio)
        caida = 500 * self.t_fase ** 2 if (c.caido and self.fase == "fin") else 0.0
        self.ctx.sprites.bailarina(frame, (pies[0], pies[1] + caida), H * 0.22, c.angulo)

    def debug_info(self) -> dict[str, str]:
        info = {"fase": self.fase, "t": f"{self.t:.1f}/{self.objetivo:.0f}",
                "balanceo": f"{self.balanceo:+.3f} aw", "postura": self.aviso_postura or "ok"}
        if self.vigilante is not None:
            info["pies movidos"] = f"{self.vigilante.desplazamiento:.2f} aw"
        if self.una_pierna:
            info["pierna"] = f"{self.pierna.estado} dif={self.pierna.diferencia:+.2f} aw"
        if self.aventura:
            if self.mecanica in ("cuerda", "pelota"):
                info["ángulo"] = f"{self.cuerda.angulo:+.1f}°"
            else:
                info["bandeja"] = f"x={self.bandeja.x:+.2f} incl={self.bandeja.inclinacion:+.1f}°"
            info["viento"] = f"{self.viento.valor:+.2f}"
        return info
