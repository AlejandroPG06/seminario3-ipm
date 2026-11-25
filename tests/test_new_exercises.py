"""Ejercicios nuevos: sobre una pierna, marcha en el sitio y consejos de la Práctica."""
import pytest

from games.march import ContadorMarcha, elevacion
from games.one_leg import APOYADO, DOS_PIES, UNA_PIERNA, DetectorUnaPierna
from games.practice import consejos, valor_en_evaluacion

DT = 1 / 30
AW = 0.16      # anchura de hombros (altos de imagen)


def test_una_pierna_levantar_y_apoyar():
    d = DetectorUnaPierna()
    assert d.actualizar(0.87, 0.87, AW) == DOS_PIES
    assert d.actualizar(0.80, 0.87, AW) == UNA_PIERNA      # tobillo izq. 0,07 más alto = 0,44 aw
    assert d.pie_levantado == "izq"
    for _ in range(2):                                       # baja un instante: no basta
        d.actualizar(0.87, 0.87, AW)
    d.actualizar(0.80, 0.87, AW)
    assert d.estado == UNA_PIERNA
    for _ in range(4):
        d.actualizar(0.87, 0.87, AW)
    assert d.estado == APOYADO


def test_una_pierna_ruido_no_cuenta():
    d = DetectorUnaPierna()
    for k in range(60):
        d.actualizar(0.87 + 0.01 * (-1) ** k, 0.87, AW)     # temblor de 0,06 aw
    assert d.estado == DOS_PIES


def test_una_pierna_derecha():
    d = DetectorUnaPierna()
    d.actualizar(0.87, 0.79, AW)
    assert d.levantado and d.pie_levantado == "der"


def test_elevacion():
    assert elevacion(0.69, 0.69, 0.50) == pytest.approx(0.0)
    assert elevacion(0.595, 0.69, 0.50) == pytest.approx(0.5)
    assert elevacion(0.50, 0.69, 0.50) == pytest.approx(1.0)
    assert elevacion(0.6, 0.5, 0.5) == 0.0


def marchar(contador, pasos, periodo=0.6, altura=0.7):
    """Alterna rodillas: cada paso sube una rodilla durante medio periodo."""
    n = int(periodo / DT)
    for k in range(pasos):
        for i in range(n):
            e = altura if i < n // 2 else 0.0
            contador.actualizar(e if k % 2 == 0 else 0.0, e if k % 2 == 1 else 0.0, DT)


def test_marcha_cuenta_pasos_por_pierna():
    c = ContadorMarcha()
    marchar(c, 10)
    assert c.total == 10 and c.pasos_der == 5


def test_marcha_rodilla_baja_no_cuenta():
    c = ContadorMarcha()
    marchar(c, 10, altura=0.4)          # no llega a la mitad
    assert c.total == 0


def test_marcha_histeresis():
    c = ContadorMarcha()
    for k in range(60):                 # oscila alrededor del umbral de subida
        c.actualizar(0.5 + 0.03 * (-1) ** k, 0.0, DT)
    assert c.total == 1


def test_marcha_al_compas():
    c = ContadorMarcha(tempo_bpm=100)   # un pulso cada 0,6 s
    marchar(c, 10, periodo=0.6)
    assert c.al_compas >= 8
    c2 = ContadorMarcha(tempo_bpm=100)
    marchar(c2, 10, periodo=0.85)       # a destiempo
    assert c2.al_compas < c.al_compas
    assert ContadorMarcha().al_compas == 0


def test_valor_en_evaluacion():
    assert "1/1" in valor_en_evaluacion("pies_juntos", {"tiempo": 10.0})
    assert "1/2" in valor_en_evaluacion("tandem", {"tiempo": 5.0})
    assert "4/4" in valor_en_evaluacion("silla", {"tiempo": 10.0, "repeticiones": 5})
    assert "0/4" in valor_en_evaluacion("silla", {"tiempo": None, "repeticiones": 3})
    assert "riesgo" in valor_en_evaluacion("una_pierna", {"tiempo": 2.0})
    assert "Resistencia" in valor_en_evaluacion("marcha", {"pasos_der": 80})


def test_consejos():
    assert any("pies" in c for c in consejos("tandem", {"motivo": "Has movido los pies", "balanceo_medio": 0.0}))
    assert any("derecha" in c for c in consejos("pies_juntos", {"motivo": "", "balanceo_signo": 0.1}))
    assert any("manos" in c for c in consejos("silla", {"manos": True, "incompletas": 0, "tiempo": 10}))
    assert consejos("pies_juntos", {"motivo": "¡Conseguido!", "tiempo": 10.0}) == ["¡Muy bien! Repite para afianzarlo."]
    assert len(consejos("silla", {"manos": True, "incompletas": 2, "tiempo": 20})) <= 3


def _menu_dos_botones():
    from ui.dwell_button import BotonDwell, MenuDwell
    return MenuDwell([BotonDwell((0, 0, 100, 100), "A", "a"), BotonDwell((200, 0, 100, 100), "B", "b")])


def test_dwell_bloqueo_inicial():
    import config as C
    m = _menu_dos_botones()
    t, accion = 0.0, None
    while accion is None and t < 10:
        accion = m.actualizar([(50, 50)], DT)
        t += DT
    assert accion == "a" and t == pytest.approx(C.DWELL_BLOQUEO_S + C.DWELL_S, abs=0.1)


def test_dwell_exclusivo_con_dos_manos():
    """Con una mano en cada botón solo uno carga; no se pulsan dos a la vez."""
    m = _menu_dos_botones()
    acciones = [m.actualizar([(50, 50), (250, 50)], DT) for _ in range(30 * 6)]
    pulsadas = [a for a in acciones if a]
    assert pulsadas and set(pulsadas) == {pulsadas[0]}
    assert min(b.progreso for b in m.botones) == 0.0


def test_dwell_bloqueo_tras_pulsar():
    import config as C
    m = _menu_dos_botones()
    while m.actualizar([(50, 50)], DT) is None:
        pass
    # la mano sigue encima: no vuelve a pulsar hasta bloqueo + dwell
    pasos = int((C.DWELL_BLOQUEO_S + C.DWELL_S - 0.2) / DT)
    assert all(m.actualizar([(50, 50)], DT) is None for _ in range(pasos))
