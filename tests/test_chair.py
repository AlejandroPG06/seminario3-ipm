"""Contador de la silla con secuencias sintéticas."""
import pytest

from games.chair_counter import DE_PIE, SENTADO, ContadorSilla

DT = 1 / 30


def contar(angulos, manos=False, **kw):
    c = ContadorSilla(**kw)
    for a in angulos:
        c.actualizar(a, DT, manos)
    return c


def ciclos(n, periodo=2.0, ruido=0.0, minimo=90.0, maximo=175.0):
    from tests.sinteticos import ciclos_rodilla
    return ciclos_rodilla(n, periodo, DT, minimo, maximo, ruido)


def test_cinco_ciclos_cinco_repeticiones():
    c = contar(ciclos(5))
    assert c.cuenta == 5
    assert c.estado == SENTADO


def test_ruido_no_cuenta_de_mas():
    c = contar(ciclos(5, ruido=4.0))
    assert c.cuenta == 5


def test_ruido_junto_al_umbral_de_pie():
    # Oscila alrededor de 160° (umbral de pie): sin histéresis contaría muchas veces
    angulos = [90] * 10 + [130, 150] + [158, 162, 157, 163, 159, 161] * 20 + [90] * 10
    assert contar(angulos).cuenta == 1


def test_ruido_junto_al_umbral_sentado():
    angulos = [90] * 10 + [108, 112, 115, 109, 114, 111] * 20
    c = contar(angulos)
    assert c.cuenta == 0 and len(c.incompletas) == 0


def test_subida_incompleta():
    angulos = [90] * 10 + [130, 140, 145, 140, 120, 100, 90]
    c = contar(angulos)
    assert c.cuenta == 0 and len(c.incompletas) == 1


def test_empieza_de_pie_no_cuenta():
    c = contar([175] * 20)
    assert c.estado == DE_PIE and c.cuenta == 0


def test_calidad_perfecta_y_buena():
    rapido = contar(ciclos(1, periodo=2.0))
    assert rapido.repeticiones[0].calidad == "Perfecta"
    lento = contar(ciclos(1, periodo=16.0))   # sube de 125° a 160° en ~2,2 s
    assert lento.repeticiones[0].calidad == "Buena"


def test_manos_marcan_y_pueden_invalidar():
    c = contar(ciclos(2), manos=True)
    assert c.cuenta == 2 and all(r.manos for r in c.repeticiones)
    assert all(r.calidad == "Buena" for r in c.repeticiones)
    estricto = contar(ciclos(2), manos=True, manos_invalida=True)
    assert estricto.cuenta == 0 and len(estricto.incompletas) == 2


def test_ritmo_del_canon():
    from games.chair_counter import Ritmo
    r = Ritmo(3.0, 0.6)
    assert r.al_ritmo(3.2) and r.al_ritmo(5.5) and not r.al_ritmo(4.5) and not r.al_ritmo(1.0)
    assert r.desfase(2.7) == pytest.approx(-0.3)
    assert r.golpe(2.95, 3.01) and not r.golpe(3.01, 3.5) and not r.golpe(0.0, 0.5)
    assert 0 <= r.fase(4.0) < 1


def test_anular_la_ultima_repeticion():
    from games.chair_counter import ContadorSilla
    c = ContadorSilla()
    for a in (90, 130, 170):
        c.actualizar(a, 0.1)
    assert c.cuenta == 1
    rep = c.anular_ultima()
    assert c.cuenta == 0 and rep.calidad == "Fuera de ritmo" and c.incompletas == [rep]
