"""Genera los efectos de sonido WAV en assets/sounds/ con numpy + scipy.

Uso:  python tools/generate_assets.py [--forzar]
Si un WAV ya existe no se sobrescribe (salvo con --forzar), así se pueden
sustituir por sonidos propios con el mismo nombre.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402

SR = 44100   # Hz, frecuencia de muestreo
RNG = np.random.default_rng(1234)


def t(dur: float) -> np.ndarray:
    return np.arange(int(SR * dur)) / SR


def envolvente(n: int, ataque: float = 0.01, caida: float = 0.1) -> np.ndarray:
    """Ataque lineal y caída exponencial (en segundos)."""
    env = np.ones(n)
    a = max(1, int(ataque * SR))
    env[:a] = np.linspace(0, 1, a)
    env *= np.exp(-np.arange(n) / (caida * SR))
    return env


def tono(freq: float, dur: float, caida: float = 0.15, armonicos=(1.0, 0.3, 0.1)) -> np.ndarray:
    x = t(dur)
    s = sum(a * np.sin(2 * np.pi * freq * (k + 1) * x) for k, a in enumerate(armonicos))
    return s * envolvente(len(x), 0.005, caida)


def concatenar(*partes, hueco: float = 0.0) -> np.ndarray:
    silencio = np.zeros(int(hueco * SR))
    salida = []
    for p in partes:
        salida += [p, silencio]
    return np.concatenate(salida)


def ruido_filtrado(dur: float, baja: float, alta: float) -> np.ndarray:
    b, a = butter(4, [baja / (SR / 2), alta / (SR / 2)], btype="band")
    return lfilter(b, a, RNG.normal(0, 1, int(SR * dur)))


def aplausos(dur: float = 2.5) -> np.ndarray:
    """Muchas palmadas cortas de ruido filtrado en instantes aleatorios."""
    n = int(SR * dur)
    salida = np.zeros(n)
    palmada = ruido_filtrado(0.03, 800, 5000) * envolvente(int(0.03 * SR), 0.001, 0.008)
    for _ in range(int(dur * 60)):
        i = RNG.integers(0, n - len(palmada))
        salida[i:i + len(palmada)] += palmada * RNG.uniform(0.3, 1.0)
    return salida * np.linspace(1, 0.2, n)


def canon() -> np.ndarray:
    x = t(1.0)
    golpe = ruido_filtrado(1.0, 40, 400) * envolvente(len(x), 0.002, 0.25)
    grave = np.sin(2 * np.pi * 55 * x) * envolvente(len(x), 0.002, 0.3)
    return golpe + 1.5 * grave


def burbuja() -> np.ndarray:
    x = t(0.12)
    freq = 400 + 2500 * x / x[-1]
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * envolvente(len(x), 0.002, 0.04)


def nota(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def calliope(freq: float, dur: float, volumen: float = 1.0) -> np.ndarray:
    """Timbre de órgano de feria: armónicos impares con vibrato y ataque suave."""
    x = t(dur)
    vibrato = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * x)
    fase = 2 * np.pi * freq * np.cumsum(vibrato) / SR
    s = np.sin(fase) + 0.35 * np.sin(3 * fase) + 0.15 * np.sin(5 * fase)
    env = np.minimum(1.0, x / 0.02) * np.exp(-x * 1.2)
    env[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return s * env * volumen


# Vals de circo ORIGINAL (no es ninguna pieza existente): 16 compases de 3/4.
# Acordes: raíz y tríada; melodía: (nota MIDI, pulsos).
ACORDES = ["C", "C", "G7", "G7", "G7", "G7", "C", "C", "C", "C", "F", "F", "C", "G7", "C", "C"]
TRIADAS = {"C": (48, 60, 64, 67), "G7": (43, 59, 62, 65), "F": (41, 57, 60, 65)}
MELODIA = [
    [(76, 1), (79, 1), (76, 1)], [(72, 2), (67, 1)], [(74, 1), (77, 1), (74, 1)], [(71, 2), (67, 1)],
    [(77, 1), (76, 1), (74, 1)], [(71, 1), (74, 1), (79, 1)], [(76, 1), (74, 1), (72, 1)], [(67, 3)],
    [(76, 1), (79, 1), (84, 1)], [(79, 2), (76, 1)], [(81, 1), (84, 1), (81, 1)], [(77, 2), (72, 1)],
    [(76, 1), (79, 1), (76, 1)], [(74, 1), (77, 1), (71, 1)], [(72, 2), (76, 1)], [(72, 3)],
]


def musica(bpm: float = 132.0) -> np.ndarray:
    """Bucle de ~22 s: bajo «um» en el 1 y acorde «pa-pa» en el 2 y el 3, más la melodía."""
    pulso = 60.0 / bpm
    total = np.zeros(int(SR * pulso * 3 * len(ACORDES)) + SR)
    for c, (acorde, compas) in enumerate(zip(ACORDES, MELODIA)):
        inicio = c * 3 * pulso
        raiz, *tri = TRIADAS[acorde]
        partes = [(inicio, calliope(nota(raiz), pulso * 0.9, 0.9))]
        for b in (1, 2):
            acorde_pa = sum(calliope(nota(m), pulso * 0.45, 0.3) for m in tri)
            partes.append((inicio + b * pulso, acorde_pa))
        t_nota = inicio
        for midi, pulsos in compas:
            partes.append((t_nota, calliope(nota(midi), pulso * pulsos * 0.95, 0.8)))
            t_nota += pulsos * pulso
        for t0, onda in partes:
            i = int(t0 * SR)
            total[i:i + len(onda)] += onda
    return total[:int(SR * pulso * 3 * len(ACORDES))]


def tambor() -> np.ndarray:
    """Golpe de tambor: parche grave que cae de tono más un chasquido de ruido."""
    x = t(0.35)
    freq = 150 * np.exp(-x * 6) + 70
    parche = np.sin(2 * np.pi * np.cumsum(freq) / SR) * envolvente(len(x), 0.001, 0.12)
    chasquido = ruido_filtrado(0.35, 300, 3000) * envolvente(len(x), 0.001, 0.03)
    return parche + 0.5 * chasquido


SONIDOS = {
    "click": lambda: tono(1500, 0.05, 0.01),
    "cuenta": lambda: tono(880, 0.18, 0.08),
    "ya": lambda: tono(1320, 0.45, 0.2),
    "acierto": lambda: concatenar(tono(988, 0.09, 0.05), tono(1319, 0.25, 0.12)),
    "fallo": lambda: concatenar(tono(330, 0.18, 0.1, (1, 0.6, 0.4)), tono(247, 0.4, 0.2, (1, 0.6, 0.4))),
    "fanfarria": lambda: concatenar(*(tono(f, 0.16, 0.12, (1, 0.5, 0.25)) for f in (523, 659, 784)),
                                    tono(1047, 0.7, 0.35, (1, 0.5, 0.25))),
    "aplausos": aplausos,
    "burbuja": burbuja,
    "canon": canon,
    "tambor": tambor,
    "musica": musica,
}
# Una versión de la música por cada tempo de El Desfile, para marchar al compás
for _tempo in sorted({int(n.get("tempo_bpm", 0)) for a in C.ACTOS for n in a["niveles"]} - {0}):
    SONIDOS[f"musica_{_tempo}"] = (lambda bpm=_tempo: musica(bpm))


def guardar(nombre: str, senal: np.ndarray, directorio: str) -> str:
    senal = senal / (np.max(np.abs(senal)) + 1e-9) * 0.8
    ruta = os.path.join(directorio, f"{nombre}.wav")
    wavfile.write(ruta, SR, (senal * 32767).astype(np.int16))
    return ruta


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--forzar", action="store_true", help="sobrescribe los WAV existentes")
    p.add_argument("--destino", default=C.SOUNDS_DIR)
    args = p.parse_args(argv)
    os.makedirs(args.destino, exist_ok=True)
    for nombre, generador in SONIDOS.items():
        ruta = os.path.join(args.destino, f"{nombre}.wav")
        if os.path.exists(ruta) and not args.forzar:
            print(f"  {nombre}.wav ya existe, se conserva")
            continue
        guardar(nombre, generador(), args.destino)
        print(f"  {nombre}.wav generado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
