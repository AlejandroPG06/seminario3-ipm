"""Comprobación de encuadre y calibración (2 s quieto → posición de reposo y escala)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import config as C
from core.geometry import distancia, punto_medio
from core.pose import PoseFrame

PIERNA_IZQ = (C.CADERA_IZQ, C.RODILLA_IZQ, C.TOBILLO_IZQ)
PIERNA_DER = (C.CADERA_DER, C.RODILLA_DER, C.TOBILLO_DER)


@dataclass
class Calibracion:
    """Resultado de la calibración.

    cadera_x/cadera_y en coordenadas normalizadas 0-1; anchuras, alturas,
    longitudes y tobillos en coordenadas isótropas (altos de imagen, ver PoseFrame.q).
    """
    cadera_x: float
    cadera_y: float
    anchura_hombros: float
    altura_torso: float
    tobillos: np.ndarray            # (2, 2): tobillo izq. y dcho. (isótropas)
    longitud_muslo: float
    lado: str                       # "izq" o "der": lado más visible (silla)
    vista: str                      # "frente" o "lado"
    rodillas_y: np.ndarray = field(default_factory=lambda: np.array([0.7, 0.7]))  # y de rodilla izq./dcha. en reposo


def anchura_hombros(pose: PoseFrame) -> float:
    """Distancia entre hombros (en altos de imagen)."""
    return distancia(pose.q(C.HOMBRO_IZQ), pose.q(C.HOMBRO_DER))


def centro_cadera(pose: PoseFrame) -> np.ndarray:
    """Punto medio de las caderas (normalizado 0-1)."""
    return punto_medio(pose.p(C.CADERA_IZQ), pose.p(C.CADERA_DER))


def centro_cadera_q(pose: PoseFrame) -> np.ndarray:
    """Punto medio de las caderas (isótropo)."""
    return punto_medio(pose.q(C.CADERA_IZQ), pose.q(C.CADERA_DER))


def altura_torso(pose: PoseFrame) -> float:
    """Distancia del punto medio de hombros al de caderas (en altos de imagen)."""
    hombros = punto_medio(pose.q(C.HOMBRO_IZQ), pose.q(C.HOMBRO_DER))
    return distancia(hombros, centro_cadera_q(pose))


def lado_visible(pose: PoseFrame) -> str:
    """Lado ("izq"/"der") cuya pierna se ve mejor."""
    vi = sum(pose.vis(i) for i in PIERNA_IZQ)
    vd = sum(pose.vis(i) for i in PIERNA_DER)
    return "izq" if vi >= vd else "der"


def pierna(lado: str) -> tuple[int, int, int]:
    """Índices (cadera, rodilla, tobillo) del lado indicado."""
    return PIERNA_IZQ if lado == "izq" else PIERNA_DER


def evaluar_encuadre(pose: PoseFrame | None, vista: str) -> str:
    """Devuelve un aviso para el jugador, o "" si el encuadre es correcto."""
    if pose is None:
        return "No te veo: colócate delante de la cámara"
    if vista == "lado":
        return _encuadre_lado(pose)
    return _encuadre_frente(pose)


def _toca_bordes(pose: PoseFrame, indices) -> bool:
    m = C.ENCUADRE_MARGEN
    pts = pose.lm[list(indices), :2]
    return bool(np.any(pts < m) or np.any(pts > 1 - m))


def _encuadre_frente(pose: PoseFrame) -> str:
    if not pose.visibles((C.HOMBRO_IZQ, C.HOMBRO_DER, C.CADERA_IZQ, C.CADERA_DER)):
        return "No te veo el cuerpo: colócate de frente"
    if not pose.visibles((C.TOBILLO_IZQ, C.TOBILLO_DER)):
        return "No te veo los pies: aléjate de la cámara"
    torso = altura_torso(pose)
    if torso > 0 and anchura_hombros(pose) / torso < C.VISTA_FRENTE_RATIO_MIN:
        return "Ponte de frente a la cámara"
    altura = max(pose.p(C.TOBILLO_IZQ)[1], pose.p(C.TOBILLO_DER)[1]) - pose.p(C.NARIZ)[1]
    clave = (C.NARIZ, C.HOMBRO_IZQ, C.HOMBRO_DER, C.TOBILLO_IZQ, C.TOBILLO_DER)
    if altura > C.ENCUADRE_ALTURA_MAX or _toca_bordes(pose, clave):
        return "Aléjate un poco de la cámara"
    if altura < C.ENCUADRE_ALTURA_MIN:
        return "Acércate un poco a la cámara"
    cx = centro_cadera(pose)[0]
    if cx < 0.5 - C.ENCUADRE_CENTRO_MAX:
        return "Muévete un poco hacia tu derecha"   # imagen en espejo
    if cx > 0.5 + C.ENCUADRE_CENTRO_MAX:
        return "Muévete un poco hacia tu izquierda"
    return ""


def _encuadre_lado(pose: PoseFrame) -> str:
    lado = lado_visible(pose)
    if not pose.visibles(pierna(lado)):
        return "No te veo la pierna: ponte de lado y aléjate"
    hombro = C.HOMBRO_IZQ if lado == "izq" else C.HOMBRO_DER
    if not pose.visibles((hombro,)):
        return "No te veo el tronco: aléjate un poco"
    if _toca_bordes(pose, pierna(lado) + (hombro,)):
        return "Aléjate un poco de la cámara"
    torso = altura_torso(pose)
    if torso > 0 and anchura_hombros(pose) / torso > C.VISTA_LADO_RATIO_MAX:
        return "Ponte de lado a la cámara"
    return ""


class Calibrador:
    """Acumula frames mientras el jugador está quieto y produce una Calibracion."""

    def __init__(self, vista: str, duracion_s: float = C.CALIB_DURACION_S):
        self.vista = vista
        self.duracion_s = duracion_s
        self._reiniciar()

    def _reiniciar(self) -> None:
        self._t = 0.0
        self._muestras: list[PoseFrame] = []
        self._ancla: np.ndarray | None = None

    @property
    def progreso(self) -> float:
        """Fracción (0-1) de calibración completada."""
        return min(1.0, self._t / self.duracion_s)

    def actualizar(self, pose: PoseFrame | None, dt: float) -> Calibracion | None:
        """Añade un frame; devuelve la Calibracion al completar el tiempo quieto."""
        if pose is None:
            self._reiniciar()
            return None
        cadera = centro_cadera_q(pose)
        escala = anchura_hombros(pose) if self.vista == "frente" else altura_torso(pose) * 0.5
        if self._ancla is None:
            self._ancla = cadera
        elif distancia(cadera, self._ancla) > C.CALIB_MOVIMIENTO_MAX * max(escala, 1e-3):
            self._reiniciar()
            self._ancla = cadera
        self._muestras.append(pose)
        self._t += dt
        if self._t >= self.duracion_s:
            resultado = self._calcular()
            self._reiniciar()
            return resultado
        return None

    def _calcular(self) -> Calibracion:
        lms = np.stack([m.lm for m in self._muestras])
        ultima = self._muestras[-1]
        media = PoseFrame(lms.mean(axis=0), None, 0, ultima.ancho, ultima.alto)
        lado = lado_visible(media)
        cad, rod, _ = pierna(lado)
        cadera = centro_cadera(media)
        return Calibracion(
            cadera_x=float(cadera[0]),
            cadera_y=float(cadera[1]),
            anchura_hombros=max(anchura_hombros(media), 1e-3),
            altura_torso=max(altura_torso(media), 1e-3),
            tobillos=np.array([media.q(C.TOBILLO_IZQ), media.q(C.TOBILLO_DER)]),
            longitud_muslo=max(distancia(media.q(cad), media.q(rod)), 1e-3),
            lado=lado,
            vista=self.vista,
            rodillas_y=np.array([media.p(C.RODILLA_IZQ)[1], media.p(C.RODILLA_DER)[1]]),
        )
