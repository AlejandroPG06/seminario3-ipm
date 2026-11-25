"""Generación de sonidos y carga de sprites/fondo sin archivos."""
import os

import numpy as np
import pytest
from scipy.io import wavfile

from tools.generate_assets import SONIDOS, main as generar
from ui.audio import Audio, Mezclador
from ui.background import Fondo
from ui.sprites import Sprites


def test_genera_todos_los_wav(tmp_path):
    generar(["--destino", str(tmp_path)])
    for nombre in SONIDOS:
        sr, datos = wavfile.read(os.path.join(tmp_path, f"{nombre}.wav"))
        assert sr == 44100 and len(datos) > 1000 and datos.dtype == np.int16


def test_audio_sin_dispositivo_no_falla():
    a = Audio(activado=False)
    a.reproducir("acierto")          # silencio, sin excepción
    assert not a.disponible


def test_sprites_png_sustituye_al_procedural(tmp_path):
    import cv2
    png = np.zeros((40, 40, 4), np.uint8)
    png[..., 2] = 255
    png[..., 3] = 255
    cv2.imwrite(os.path.join(tmp_path, "estrella.png"), png)
    sp = Sprites(str(tmp_path))
    assert sp.tiene("estrella") and not sp.tiene("vaso")
    frame = np.zeros((200, 200, 3), np.uint8)
    sp.estrella(frame, (100, 100), 30)
    assert frame[100, 100, 2] == 255      # se ha pegado el PNG rojo


def test_fondo_compone_con_mascara():
    f = Fondo(activado=True, directorio=None)
    frame = np.full((90, 160, 3), 50, np.uint8)
    mascara = np.zeros((90, 160), np.float32)
    mascara[:, :80] = 1.0
    out = f.componer(frame, mascara)
    assert (out[:, :70] == 50).all() and not (out[:, 100:] == 50).all()
    assert f.componer(frame, None) is frame


def test_mezclador_musica_y_efectos_a_la_vez():
    import config as C
    musica = np.full(1000, 0.5, np.float32)
    efecto = np.full(300, 0.5, np.float32)
    m = Mezclador({"musica": musica, "acierto": efecto})
    solo_musica = m.mezclar(100)
    assert solo_musica[0] == pytest.approx(0.5 * C.VOLUMEN_MUSICA)
    m.reproducir("acierto")
    m.reproducir("acierto")                       # dos efectos superpuestos
    mezcla = m.mezclar(100)
    assert mezcla[0] == pytest.approx(min(1.0, 0.5 * C.VOLUMEN_MUSICA + 2 * 0.5 * C.VOLUMEN_EFECTOS))
    for _ in range(5):
        m.mezclar(100)
    assert m.mezclar(100)[0] == pytest.approx(0.5 * C.VOLUMEN_MUSICA)   # los efectos ya acabaron
    m.reproducir("no_existe")                     # se ignora


def test_mezclador_silencia_musica():
    m = Mezclador({"musica": np.ones(500, np.float32)})
    m.musica_permitida = False
    assert not m.mezclar(50).any()
    m.musica_permitida, m.musica_activada = True, False
    assert not m.mezclar(50).any()
    m.musica_activada = True
    assert m.mezclar(50).all()


def test_musica_en_bucle():
    m = Mezclador({"musica": np.arange(10, dtype=np.float32)})
    a = m.mezclar(15)
    assert a[12] == a[2]


def test_musica_en_todas_las_escenas_y_desfile_al_tempo(ctx):
    from scenes.balance_scene import EscenaEquilibrio
    from scenes.march_scene import EscenaMarcha
    from scenes.menu import EscenaMenu
    from core.calibration import Calibrador
    from tests.sinteticos import pose_de_pie
    import config as C
    c = Calibrador("frente")
    cal = None
    while cal is None:
        cal = c.actualizar(pose_de_pie(), 1 / 30)
    assert EscenaMenu(ctx).con_musica
    assert EscenaEquilibrio(ctx, cal, "tandem", "evaluacion", None, None).con_musica
    assert EscenaMarcha(ctx, cal, "evaluacion", None, None).pista_musica == "musica"
    nivel = C.ACTOS[3]["niveles"][1]
    m = EscenaMarcha(ctx, cal, "aventura", None, None, nivel, C.ACTOS[3])
    assert m.con_musica and m.pista_musica == f"musica_{nivel['tempo_bpm']}"


def test_mezclador_cambia_de_pista():
    m = Mezclador({"musica": np.full(100, 0.1, np.float32), "musica_100": np.arange(100, dtype=np.float32) / 100})
    m.mezclar(30)
    m.poner_pista("musica_100", reiniciar=True)
    assert m.pista == "musica_100" and m.mezclar(5)[0] == 0.0     # empieza desde el principio
    m.poner_pista("no_existe")
    assert m.pista == "musica"


def test_genera_una_musica_por_tempo_del_desfile():
    import config as C
    tempos = {n["tempo_bpm"] for n in C.ACTOS[3]["niveles"] if n["tempo_bpm"]}
    assert {f"musica_{t}" for t in tempos} <= set(SONIDOS)


def test_rutas_con_caracteres_no_ascii(tmp_path):
    """Regresión: carpetas como «3º TERCERO» o con tildes no deben romper la carga."""
    import shutil
    import cv2
    import config as C
    from ui.text import leer_imagen
    carpeta = tmp_path / "3º TERCERO" / "Interacción"
    carpeta.mkdir(parents=True)
    png = np.zeros((10, 10, 4), np.uint8)
    ok, buf = cv2.imencode(".png", png)
    (carpeta / "estrella.png").write_bytes(buf.tobytes())
    assert leer_imagen(str(carpeta / "estrella.png"), cv2.IMREAD_UNCHANGED).shape == (10, 10, 4)
    assert Sprites(str(carpeta)).tiene("estrella")
    assert leer_imagen(str(carpeta / "no_existe.png")) is None
    if os.path.exists(C.MODEL_PATH):
        from core.pose import DetectorPose
        modelo = carpeta / "pose_landmarker_full.task"
        shutil.copy(C.MODEL_PATH, modelo)
        det = DetectorPose(str(modelo))
        assert det.detectar(np.zeros((360, 640, 3), np.uint8)) is None
        det.cerrar()


def test_encajar_en_pantalla():
    from ui.ventana import encajar
    img = np.zeros((720, 1280, 3), np.uint8)
    assert encajar(img, 1920, 1080, rellenar=True).shape == (1080, 1920, 3)
    assert encajar(img, 1920, 1200, rellenar=True).shape == (1200, 1920, 3)      # 16:10 con bandas negras
    assert encajar(img, 1689, 950, rellenar=False).shape[:2] == (950, 1688)
