import pytest

from core.geometry import angulo, distancia, ema, limitar, normalizar, punto_medio, zona_muerta


def test_distancia():
    assert distancia((0, 0), (3, 4)) == pytest.approx(5.0)
    assert distancia((1, 1), (1, 1)) == 0.0


def test_punto_medio():
    assert list(punto_medio((0, 0), (2, 4))) == [1.0, 2.0]


@pytest.mark.parametrize("c, esperado", [((1, 1), 45.0), ((-1, 1), 135.0), ((0, -1), 90.0)])
def test_angulo_parametrizado(c, esperado):
    assert angulo((1, 0), (0, 0), c) == pytest.approx(esperado)


def test_angulo_casos_fijos():
    assert angulo((0, 1), (0, 0), (1, 0)) == pytest.approx(90.0)
    assert angulo((0, -1), (0, 0), (0, 1)) == pytest.approx(180.0)   # pierna recta
    assert angulo((1, 0), (0, 0), (1, 0)) == pytest.approx(0.0)
    assert angulo((0, 0), (0, 0), (1, 0)) == 0.0                     # puntos coincidentes


def test_normalizar_y_zona_muerta():
    assert normalizar(0.06, 0.12) == pytest.approx(0.5)
    assert normalizar(1.0, 0.0) == 0.0
    assert zona_muerta(0.02, 0.03) == 0.0
    assert zona_muerta(0.05, 0.03) == pytest.approx(0.02)
    assert zona_muerta(-0.05, 0.03) == pytest.approx(-0.02)


def test_ema_y_limitar():
    assert ema(None, 5.0, 0.3) == 5.0
    assert ema(0.0, 10.0, 0.3) == pytest.approx(3.0)
    assert limitar(5, 0, 3) == 3
    assert limitar(-5, 0, 3) == 0
