"""Sonido: mezclador propio (música en bucle + efectos superpuestos) sobre sounddevice.

`Mezclador` es lógica pura con numpy (testeable sin tarjeta de sonido).
`Audio` abre un OutputStream cuyo callback pide muestras al mezclador, así que
nunca bloquea el bucle del juego. Si no hay dispositivo, el juego sigue en silencio.
"""
from __future__ import annotations

import os
import threading

import numpy as np

import config as C


class Mezclador:
    """Suma la música (en bucle) y los efectos activos en bloques de muestras."""

    def __init__(self, sonidos: dict[str, np.ndarray], musica: str = "musica"):
        self.sonidos = sonidos
        self.pista = musica
        self._musica = sonidos.get(musica)
        self._pos_musica = 0
        self._activos: list[list] = []          # [muestras, posición]
        self._lock = threading.Lock()
        self.musica_activada = True             # preferencia del jugador (tecla M)
        self.musica_permitida = True            # lo decide la escena
        self.volumen_musica = C.VOLUMEN_MUSICA  # 0-1, se cambia en Ajustes

    def poner_pista(self, nombre: str, reiniciar: bool = False) -> None:
        """Cambia la música de fondo (si existe). reiniciar=True la empieza desde el principio."""
        if nombre not in self.sonidos:
            nombre = "musica"
        with self._lock:
            if nombre != self.pista or reiniciar:
                self.pista = nombre
                self._musica = self.sonidos.get(nombre)
                self._pos_musica = 0

    def reproducir(self, nombre: str) -> None:
        datos = self.sonidos.get(nombre)
        if datos is None:
            return
        with self._lock:
            self._activos.append([datos, 0])
            del self._activos[:-C.AUDIO_MAX_EFECTOS]

    @property
    def sonando_musica(self) -> bool:
        return self._musica is not None and self.musica_activada and self.musica_permitida

    def mezclar(self, n: int) -> np.ndarray:
        """Devuelve n muestras float32 en [-1, 1]."""
        salida = np.zeros(n, np.float32)
        with self._lock:
            if self.sonando_musica:
                idx = (self._pos_musica + np.arange(n)) % len(self._musica)
                salida += self._musica[idx] * self.volumen_musica
                self._pos_musica = int((self._pos_musica + n) % len(self._musica))
            vivos = []
            for efecto in self._activos:
                datos, pos = efecto
                trozo = datos[pos:pos + n]
                salida[:len(trozo)] += trozo * C.VOLUMEN_EFECTOS
                efecto[1] = pos + n
                if efecto[1] < len(datos):
                    vivos.append(efecto)
            self._activos = vivos
        return np.clip(salida, -1.0, 1.0)


def cargar_wavs(directorio: str, sr: int = C.AUDIO_SR) -> dict[str, np.ndarray]:
    """Lee los WAV de un directorio como mono float32 a la frecuencia sr."""
    from scipy.io import wavfile
    sonidos: dict[str, np.ndarray] = {}
    if not os.path.isdir(directorio):
        return sonidos
    for nombre in os.listdir(directorio):
        if not nombre.lower().endswith(".wav"):
            continue
        try:
            sr_archivo, datos = wavfile.read(os.path.join(directorio, nombre))
        except (OSError, ValueError):
            continue
        if datos.dtype.kind == "i":
            datos = datos.astype(np.float32) / np.iinfo(datos.dtype).max
        datos = datos.astype(np.float32)
        if datos.ndim == 2:
            datos = datos.mean(axis=1)
        if sr_archivo != sr and len(datos) > 1:      # remuestreo lineal sencillo
            t = np.linspace(0, len(datos) - 1, int(len(datos) * sr / sr_archivo))
            datos = np.interp(t, np.arange(len(datos)), datos).astype(np.float32)
        sonidos[os.path.splitext(nombre)[0]] = datos
    return sonidos


class Audio:
    """Fachada que usan las escenas: reproducir efectos y controlar la música."""

    def __init__(self, directorio: str = C.SOUNDS_DIR, activado: bool = True, musica: bool = True):
        self._stream = None
        self.mezclador: Mezclador | None = None
        self.motivo = ""
        if not activado:
            self.motivo = "desactivado"
            return
        try:
            import sounddevice as sd  # puede fallar sin PortAudio
            sd.query_devices(kind="output")
        except Exception as e:  # noqa: BLE001 - cualquier fallo → silencio
            self.motivo = f"sin dispositivo de audio ({type(e).__name__})"
            return
        sonidos = cargar_wavs(directorio)
        if not sonidos:
            self.motivo = "no hay sonidos (ejecuta tools/generate_assets.py)"
            return
        self.mezclador = Mezclador(sonidos)
        self.mezclador.musica_activada = musica
        try:
            self._stream = sd.OutputStream(samplerate=C.AUDIO_SR, channels=1, dtype="float32",
                                           blocksize=C.AUDIO_BLOQUE, callback=self._callback)
            self._stream.start()
        except Exception as e:  # noqa: BLE001
            self.motivo = f"no se pudo abrir la salida de audio ({type(e).__name__})"
            self.mezclador = None

    def _callback(self, outdata, frames, tiempo, estado) -> None:  # noqa: ARG002
        outdata[:, 0] = self.mezclador.mezclar(frames)

    @property
    def disponible(self) -> bool:
        return self.mezclador is not None

    def reproducir(self, nombre: str) -> None:
        """Lanza un efecto por nombre (sin extensión). No bloquea; ignora errores."""
        if self.mezclador is not None:
            self.mezclador.reproducir(nombre)

    def permitir_musica(self, permitida: bool) -> None:
        """Lo llama main.py al cambiar de escena (la Evaluación y el Desfile van sin música)."""
        if self.mezclador is not None:
            self.mezclador.musica_permitida = permitida

    def poner_pista(self, nombre: str, reiniciar: bool = False) -> None:
        """Música de fondo de la escena (main.py la pone al cambiar de escena)."""
        if self.mezclador is not None:
            self.mezclador.poner_pista(nombre, reiniciar)

    @property
    def sonando_musica(self) -> bool:
        return self.mezclador is not None and self.mezclador.sonando_musica

    def ajustar_musica(self, activada: bool, volumen: float) -> None:
        """Ajustes: música sí/no y volumen (0-1)."""
        if self.mezclador is not None:
            self.mezclador.musica_activada = activada
            self.mezclador.volumen_musica = max(0.0, min(1.0, volumen))

    def alternar_musica(self) -> bool:
        """Tecla M: activa o desactiva la música. Devuelve el estado nuevo."""
        if self.mezclador is None:
            return False
        self.mezclador.musica_activada = not self.mezclador.musica_activada
        return self.mezclador.musica_activada

    def cerrar(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
