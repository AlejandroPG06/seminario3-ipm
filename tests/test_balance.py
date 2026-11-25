"""Física de bandeja y cuerda floja, posturas, viento y burbujas."""
import math

import numpy as np
import pytest

from games.hazards import Burbujas, Viento
from games.posture import VigilantePies, separacion_pies, verificar_postura
from games.tightrope import CuerdaFloja
from games.tray import Bandeja

DT = 1 / 30


def simular(sistema, balanceos, viento=0.0):
    for b in balanceos:
        if sistema.actualizar(b, DT, viento):
            return True
    return False


def test_bandeja_quieta_no_cae():
    rng = np.random.default_rng(0)
    ruido = rng.normal(0, 0.01, 30 * 20)          # temblor de MediaPipe (dentro de la zona muerta)
    b = Bandeja(1)
    assert not simular(b, ruido)
    assert abs(b.x) < 0.05


def test_bandeja_balanceo_fuerte_cae():
    t = np.arange(30 * 10) * DT
    b = Bandeja(1)
    assert simular(b, 0.3 * np.sin(2 * math.pi * t / 3.0))


def test_bandeja_inclinacion_constante_cae():
    assert simular(Bandeja(1), [0.2] * 30 * 10)


def test_bandeja_signo_derecha():
    b = Bandeja(1)
    simular(b, [0.15] * 15)
    assert b.inclinacion > 0 and b.x > 0


def test_mas_objetos_mas_inercia_y_menos_borde():
    b1, b3 = Bandeja(1), Bandeja(3)
    assert b3.inercia > b1.inercia and b3.borde < b1.borde
    simular(b1, [0.15] * 20)
    simular(b3, [0.15] * 20)
    assert abs(b3.v) < abs(b1.v)       # responde más despacio


def test_bandeja_viento_empuja():
    b = Bandeja(1)
    assert simular(b, [0.0] * 30 * 10, viento=1.0)


def test_cuerda_quieta_y_fuerte():
    rng = np.random.default_rng(1)
    c = CuerdaFloja()
    assert not simular(c, rng.normal(0, 0.01, 30 * 20))
    assert not CuerdaFloja().caido
    assert simular(CuerdaFloja(), [0.5] * 30 * 5)


def test_cuerda_recupera_el_centro():
    c = CuerdaFloja()
    simular(c, [0.12] * 30)
    assert abs(c.angulo) > 1
    simular(c, [0.0] * 30 * 5)
    assert abs(c.angulo) < 0.5


@pytest.mark.parametrize("prueba, dx, dy, ok", [
    ("pies_juntos", 0.2, 0.0, True), ("pies_juntos", 0.8, 0.0, False),
    ("semitandem", 0.3, 0.1, True), ("semitandem", 0.3, 0.0, False),
    ("tandem", 0.1, 0.2, True), ("tandem", 0.5, 0.2, False),
])
def test_verificar_postura(prueba, dx, dy, ok):
    assert verificar_postura(prueba, dx, dy)[0] is ok


def test_separacion_pies():
    dx, dy = separacion_pies(np.array([[0.52, 0.9], [0.48, 0.88]]), 0.1)
    assert dx == pytest.approx(0.4) and dy == pytest.approx(0.2)


def test_vigilante_pies():
    ref = np.array([[0.52, 0.9], [0.48, 0.9]])
    v = VigilantePies(ref, 0.12)
    assert not any(v.actualizar(ref + 0.005) for _ in range(20))
    movido = ref + np.array([[0.08, 0], [0, 0]])
    assert any(v.actualizar(movido) for _ in range(10))


def test_viento_rafagas():
    v = Viento(1.0, np.random.default_rng(0))
    valores = [v.actualizar(DT) for _ in range(30 * 20)]
    assert max(abs(x) for x in valores) > 0.5
    assert Viento(0.0).actualizar(DT) == 0.0


def test_burbujas_se_tocan():
    b = Burbujas(np.random.default_rng(0), intervalo=0.5, vida=10)
    for _ in range(45):
        b.actualizar(DT, [], (640, 300), 150, 30, 1280, 720)
    assert b.items
    objetivo = b.items[0]
    tocadas = b.actualizar(DT, [(objetivo.x, objetivo.y)], (640, 300), 150, 30, 1280, 720)
    assert tocadas and b.tocadas == 1


def test_fisica_independiente_de_los_fps():
    """Con 10 fps o con 60 fps el vaso cae más o menos en el mismo instante."""
    def instante_caida(fps):
        b = Bandeja(1)
        for i in range(fps * 20):
            if b.actualizar(0.1, 1 / fps):
                return i / fps
    t10, t60 = instante_caida(10), instante_caida(60)
    assert t10 is not None and abs(t10 - t60) < 0.15
