"""Puntuación SPPB (todos los cortes), protocolo, puntos, rachas y estrellas."""
import pytest

import config as C
from games.chair_counter import Repeticion
from games.protocol import ProtocoloEvaluacion
from games.scoring import (MarcadorEquilibrio, distancia_canon, estrellas_equilibrio,
                           estrellas_marcha, estrellas_silla, interpretar_marcha,
                           interpretar_sppb, interpretar_una_pierna, multiplicador_estabilidad,
                           puntos_marcha, puntos_silla, sppb_equilibrio, sppb_silla)


@pytest.mark.parametrize("prueba", ["pies_juntos", "semitandem"])
@pytest.mark.parametrize("t, puntos", [(10.0, 1), (12.0, 1), (9.99, 0), (0.0, 0), (None, 0)])
def test_sppb_pies_juntos_y_semitandem(prueba, t, puntos):
    assert sppb_equilibrio(prueba, t) == puntos


@pytest.mark.parametrize("t, puntos", [(10.0, 2), (9.99, 1), (3.0, 1), (2.99, 0), (0.0, 0), (None, 0)])
def test_sppb_tandem(t, puntos):
    assert sppb_equilibrio("tandem", t) == puntos


@pytest.mark.parametrize("t, puntos", [
    (5.0, 4), (11.19, 4), (11.20, 3), (13.69, 3), (13.70, 2), (16.69, 2),
    (16.70, 1), (59.99, 1), (60.0, 1), (60.01, 0), (None, 0),
])
def test_sppb_silla(t, puntos):
    assert sppb_silla(t) == puntos


def test_interpretacion():
    assert interpretar_sppb(8) == C.SPPB_INTERPRETACION[0][1]
    assert interpretar_sppb(0) == C.SPPB_INTERPRETACION[-1][1]


def test_protocolo_completo():
    p = ProtocoloEvaluacion()
    assert p.actual() == "pies_juntos"
    assert p.registrar(10.0) == "semitandem"
    assert p.registrar(10.0) == "tandem"
    assert p.registrar(10.0) == "silla"
    assert p.registrar(10.5) == "una_pierna"
    assert p.sppb_terminada
    assert p.registrar(12.0) == "marcha"
    assert p.registrar(80) is None
    r = p.resultado()
    assert r["total"] == 8 and r["omitidas"] == []
    assert r["complementarias"]["una_pierna"]["valor"] == 12.0
    assert r["complementarias"]["marcha"]["valor"] == 80


def test_protocolo_omitir_complementarias():
    p = ProtocoloEvaluacion()
    for v in (10.0, 10.0, 10.0, 12.0):
        p.registrar(v)
    p.omitir_complementarias()
    assert p.terminado
    r = p.resultado()
    assert r["complementarias"] == {} and r["omitidas"] == ["una_pierna", "marcha"]
    assert r["total"] == 7


def test_complementarias_no_cambian_la_sppb():
    a, b = ProtocoloEvaluacion(), ProtocoloEvaluacion()
    for v in (10.0, 10.0, 10.0, 12.0):
        a.registrar(v)
        b.registrar(v)
    a.registrar(1.0)
    a.registrar(10)
    b.registrar(30.0)
    b.registrar(120)
    assert a.resultado()["total"] == b.resultado()["total"]


def test_protocolo_falla_pies_juntos_sigue_con_las_demas_posturas():
    p = ProtocoloEvaluacion()
    assert p.registrar(4.0) == "semitandem"          # ya no se salta al fallar una postura
    assert p.registrar(10.0) == "tandem"
    assert p.registrar(2.0) == "silla"
    p.registrar(None)
    r = p.resultado()
    assert r["omitidas"] == []
    assert r["puntos"] == {"pies_juntos": 0, "semitandem": 1, "tandem": 0, "silla": 0}


def test_protocolo_original_salta_a_silla(monkeypatch):
    monkeypatch.setattr(C, "EVALUACION_SALTAR_TRAS_FALLO", True)
    p = ProtocoloEvaluacion()
    assert p.registrar(4.0) == "silla"
    assert p.omitidas == ["semitandem", "tandem"]
    p.registrar(None)
    assert p.resultado()["total"] == 0


def test_protocolo_falla_semitandem():
    p = ProtocoloEvaluacion()
    p.registrar(10.0)
    assert p.registrar(9.0) == "tandem"
    assert p.registrar(3.5) == "silla"
    p.registrar(14.0)
    r = p.resultado()
    assert r["puntos"] == {"pies_juntos": 1, "semitandem": 0, "tandem": 1, "silla": 2}
    assert r["total"] == 4


def test_protocolo_tandem_parcial_sigue_a_silla():
    p = ProtocoloEvaluacion()
    p.registrar(10.0)
    p.registrar(10.0)
    assert p.registrar(5.0) == "silla"
    p.registrar(12.0)
    assert p.resultado()["total"] == 1 + 1 + 1 + 3


def test_multiplicador():
    assert multiplicador_estabilidad(0.01)[0] == 2.0
    assert multiplicador_estabilidad(0.10)[0] == 1.0
    assert multiplicador_estabilidad(0.5)[0] == 0.5


def test_marcador_puntos_y_racha():
    m = MarcadorEquilibrio()
    eventos = []
    for _ in range(30 * 10):
        eventos += m.actualizar(1 / 30, 0.01)
    assert m.puntos > C.PUNTOS_POR_SEGUNDO * 10 * 2       # x2 y racha
    assert m.racha_s == pytest.approx(10, abs=0.05)
    assert m.mult_racha > 1
    assert "pulso_acero" in eventos and "racha" in eventos
    m.actualizar(1 / 30, 0.3)                              # balanceo fuerte → racha a 0
    assert m.racha_s == 0 and m.racha_max_s == pytest.approx(10, abs=0.05)


def test_racha_tope():
    m = MarcadorEquilibrio()
    for _ in range(30 * 60):
        m.actualizar(1 / 30, 0.0)
    assert m.mult_racha == C.RACHA_MULT_MAX


def test_estrellas_equilibrio():
    assert estrellas_equilibrio(9.0, 10, 0.0) == 0          # no completa → 0
    assert estrellas_equilibrio(10.0, 10, 0.9) == 1         # el vaso casi se cae
    assert estrellas_equilibrio(10.0, 10, 0.5) == 2
    assert estrellas_equilibrio(10.0, 10, 0.1) == 3         # siempre cerca del centro
    assert estrellas_equilibrio(10.0, 10, 0.5, (0.6, 0.55)) == 3   # umbrales propios del nivel


def test_estrellas_intermedias_con_la_bandeja():
    """Con balanceos que no tiran el vaso se pueden conseguir 1, 2 o 3 estrellas."""
    import math
    from games.tray import Bandeja
    obtenidas = set()
    for amplitud in (0.02, 0.06, 0.10, 0.12):
        b, pmax, t = Bandeja(1), 0.0, 0.0
        while t < 10:
            assert not b.actualizar(amplitud * math.sin(2 * math.pi * 0.2 * t), 1 / 30)
            pmax = max(pmax, b.peligro)
            t += 1 / 30
        obtenidas.add(estrellas_equilibrio(10, 10, pmax))
    assert obtenidas == {1, 2, 3}


def test_estrellas_silla():
    umbrales = (60, 16.69, 13.69)
    assert estrellas_silla(None, umbrales) == 0
    assert estrellas_silla(30, umbrales) == 1
    assert estrellas_silla(15, umbrales) == 2
    assert estrellas_silla(10, umbrales) == 3
    assert estrellas_silla(61, umbrales) == 0


def test_puntos_silla_y_canon():
    perfecta = Repeticion(1.0, False, "Perfecta", 1)
    con_manos = Repeticion(2.0, True, "Buena", 2)
    p = puntos_silla([perfecta, con_manos], 10.0, 13.69)
    esperado = 150 + 100 - C.PUNTOS_SILLA_PENALIZACION_MANOS + int(3.69 * C.PUNTOS_SILLA_BONUS_POR_S)
    assert p == esperado
    assert distancia_canon(5.0) == C.CANON_DISTANCIA_MAX_M
    assert distancia_canon(20.0) < distancia_canon(10.0)
    assert distancia_canon(None) == 0.0


def test_interpretaciones_complementarias():
    assert "riesgo" in interpretar_una_pierna(3.0)
    assert "riesgo" not in interpretar_una_pierna(C.UNA_PIERNA_RIESGO_S)
    assert "Excelente" in interpretar_una_pierna(30.0)
    assert "baja" in interpretar_marcha(C.MARCHA_REFERENCIA_PASOS - 1)
    assert "adecuada" in interpretar_marcha(C.MARCHA_REFERENCIA_PASOS)
    assert "baja" in interpretar_marcha(None)


def test_estrellas_y_puntos_marcha():
    assert estrellas_marcha(10, (25, 35, 45)) == 0
    assert estrellas_marcha(25, (25, 35, 45)) == 1
    assert estrellas_marcha(50, (25, 35, 45)) == 3
    assert puntos_marcha(10, 4) == 10 * C.PUNTOS_PASO + 4 * C.PUNTOS_COMPAS


def test_balanceo_medio_con_signo():
    m = MarcadorEquilibrio()
    for _ in range(30):
        m.actualizar(1 / 30, 0.1, -0.1)
    assert m.balanceo_medio == pytest.approx(0.1) and m.balanceo_medio_signo == pytest.approx(-0.1)
