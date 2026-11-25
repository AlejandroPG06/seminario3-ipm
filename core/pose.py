"""Envoltorio del PoseLandmarker de MediaPipe y estructura PoseFrame.

`PoseFrame` y `MonitorVisibilidad` no dependen de mediapipe (se pueden usar en
tests con poses sintéticas). `DetectorPose` importa mediapipe al crearse.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import cv2
import numpy as np

import config as C


@dataclass
class PoseFrame:
    """Pose de un frame: landmarks (33, 3) con columnas x, y, visibilidad (x e y en 0-1)."""
    lm: np.ndarray
    mascara: np.ndarray | None = None
    t_ms: int = 0
    ancho: int = 1
    alto: int = 1

    def p(self, i: int) -> np.ndarray:
        """Coordenadas (x, y) normalizadas 0-1 del landmark i (para posiciones en el encuadre)."""
        return self.lm[i, :2]

    @property
    def aspecto(self) -> float:
        """Ancho / alto de la imagen."""
        return self.ancho / max(self.alto, 1)

    def q(self, i: int) -> np.ndarray:
        """Coordenadas isótropas del landmark i, en «altos de imagen».

        MediaPipe normaliza x por el ancho e y por el alto, así que en una imagen
        16:9 las distancias en x salen encogidas. Para distancias y ángulos
        hay que usar q(), nunca p().
        """
        return np.array([self.lm[i, 0] * self.aspecto, self.lm[i, 1]])

    def px(self, i: int) -> tuple[int, int]:
        """Coordenadas en píxeles del landmark i."""
        return int(self.lm[i, 0] * self.ancho), int(self.lm[i, 1] * self.alto)

    def vis(self, i: int) -> float:
        """Visibilidad (0-1) del landmark i."""
        return float(self.lm[i, 2])

    def visibles(self, indices, umbral: float = C.VISIBILIDAD_MIN) -> bool:
        """True si todos los landmarks indicados superan el umbral de visibilidad."""
        return all(self.lm[i, 2] >= umbral for i in indices)


@dataclass
class MonitorVisibilidad:
    """Cuenta frames seguidos sin ver algún grupo clave y decide cuándo pausar."""
    grupos: dict
    frames_limite: int = C.FRAMES_PERDIDA_PAUSA
    _contador: int = 0
    mensaje: str = ""
    _ultimo_faltante: str = field(default="", repr=False)

    def actualizar(self, pose: PoseFrame | None) -> bool:
        """Devuelve True si hay que pausar (se perdieron landmarks clave varios frames)."""
        faltante = ""
        if pose is None:
            faltante = "No te veo: colócate delante de la cámara"
        else:
            for indices, aviso in self.grupos.values():
                if not pose.visibles(indices):
                    faltante = aviso
                    break
        if faltante:
            self._contador += 1
            self._ultimo_faltante = faltante
        else:
            self._contador = 0
        self.mensaje = self._ultimo_faltante if self._contador >= self.frames_limite else ""
        return self._contador >= self.frames_limite


class DetectorPose:
    """PoseLandmarker en modo VIDEO con BGR→RGB, timestamps reales y suavizado EMA."""

    def __init__(self, ruta_modelo: str = C.MODEL_PATH, segmentacion: bool = True):
        import mediapipe as mp  # import diferido: los tests de lógica no lo necesitan
        self._mp = mp
        # El modelo se lee desde Python y se pasa en memoria: MediaPipe no sabe abrir en
        # Windows rutas con caracteres no ASCII (p. ej. «3º», tildes o ñ en el nombre de carpeta).
        with open(ruta_modelo, "rb") as f:
            modelo = f.read()
        opciones = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=modelo),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=C.POSE_MIN_DETECCION,
            min_pose_presence_confidence=C.POSE_MIN_PRESENCIA,
            min_tracking_confidence=C.POSE_MIN_SEGUIMIENTO,
            output_segmentation_masks=segmentacion,
        )
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(opciones)
        self._ultimo_ts = -1
        self._suave: np.ndarray | None = None

    def _timestamp(self) -> int:
        """Timestamp en ms del reloj monotónico, estrictamente creciente."""
        ts = int(time.monotonic() * 1000)
        if ts <= self._ultimo_ts:
            ts = self._ultimo_ts + 1
        self._ultimo_ts = ts
        return ts

    def detectar(self, frame_bgr: np.ndarray) -> PoseFrame | None:
        """Detecta la pose en un frame BGR (ya volteado). None si no hay nadie."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        ts = self._timestamp()
        resultado = self._landmarker.detect_for_video(imagen, ts)
        if not resultado.pose_landmarks:
            self._suave = None
            return None
        crudo = np.array([[l.x, l.y, l.visibility] for l in resultado.pose_landmarks[0]],
                         dtype=np.float32)
        if self._suave is None:
            self._suave = crudo
        else:
            self._suave = C.EMA_ALFA * crudo + (1.0 - C.EMA_ALFA) * self._suave
        mascara = None
        if resultado.segmentation_masks:
            mascara = resultado.segmentation_masks[0].numpy_view()
            if mascara.ndim == 3:
                mascara = mascara[:, :, 0]
        alto, ancho = frame_bgr.shape[:2]
        return PoseFrame(self._suave.copy(), mascara, ts, ancho, alto)

    def cerrar(self) -> None:
        """Libera el modelo."""
        self._landmarker.close()
