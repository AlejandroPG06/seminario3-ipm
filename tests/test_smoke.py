"""Prueba de humo: recorre todas las escenas con poses sintéticas sobre un frame negro.

Sin cámara ni ventana. Comprueba que update()/draw() no fallan y que los
flujos completos (Evaluación y Aventura) llegan a sus pantallas de resultados
y guardan los datos.
"""
import numpy as np
import pytest

import config as C
from scenes.base import SALIR
from tests.sinteticos import ALTO, ANCHO, pose_de_pie, pose_sentado_lado

DT = 1 / 30


def frame_negro():
    return np.zeros((ALTO, ANCHO, 3), np.uint8)


def ejecutar(escena, pose_fn, segundos, dibujar_cada=5):
    """Ejecuta la escena hasta que cambie o pase el tiempo. pose_fn(t) → PoseFrame|None."""
    pasos = int(segundos / DT)
    for i in range(pasos):
        sig = escena.update(pose_fn(i * DT), DT)
        if i % dibujar_cada == 0:
            out = escena.draw(frame_negro())
            assert out.shape == (ALTO, ANCHO, 3) and out.dtype == np.uint8
            escena.debug_info()
        if sig is not None:
            if sig != SALIR:
                sig.enter()
                sig.draw(frame_negro())
            return sig
    return escena


def tecla(escena, t):
    """Como en el bucle real: la escena nueva entra y se dibuja antes de la siguiente tecla."""
    sig = escena.on_key(t)
    if sig is not None and sig != SALIR:
        sig.enter()
        sig.draw(frame_negro())
    return sig if sig is not None else escena


def de_pie(t):
    return pose_de_pie(mascara=True)


def silla_ciclos(periodo=2.0, inicio=0.0):
    def f(t):
        tt = max(0.0, t - inicio)
        a = 90 + 85 * (1 - np.cos(2 * np.pi * tt / periodo)) / 2 if t >= inicio else 90
        return pose_sentado_lado(a)
    return f


def nombre(escena):
    return type(escena).__name__


def test_menu_y_navegacion(ctx):
    from scenes.menu import EscenaMenu
    m = EscenaMenu(ctx)
    m.enter()
    assert nombre(ejecutar(m, lambda t: None, 0.5)) == "EscenaMenu"
    m.draw(frame_negro())
    assert nombre(tecla(m, "abajo")) == "EscenaMenu"
    assert nombre(tecla(m, "enter")) == "EscenaMapa"       # Modo Aventura
    assert m.on_key("esc") == SALIR


def test_menu_dwell_con_la_mano(ctx):
    from scenes.menu import EscenaMenu
    m = EscenaMenu(ctx)
    m.draw(frame_negro())
    b = next(b for b in m.menu.botones if b.accion == "historial")
    cx, cy = b.rect[0] + b.rect[2] // 2, b.rect[1] + b.rect[3] // 2

    def mano(t):
        p = pose_de_pie()
        p.lm[C.INDICE_DER, 0], p.lm[C.INDICE_DER, 1] = cx / ANCHO, cy / ALTO
        return p
    sig = ejecutar(m, mano, C.DWELL_BLOQUEO_S + C.DWELL_S + 0.5)
    assert nombre(sig) == "EscenaHistorial"


def test_manos_en_reposo_no_tocan_botones(ctx):
    """Con los brazos caídos (de pie, de frente) ninguna mano queda sobre un botón de menú."""
    from core.gestures import manos_px
    from scenes.menu import EscenaMenu
    m = EscenaMenu(ctx)
    m.draw(frame_negro())
    for dx in (-0.05, 0.0, 0.05):
        manos = manos_px(pose_de_pie(dx_cadera=dx))
        assert manos and not any(b.contiene(p) for b in m.menu.botones for p in manos)
    sig = ejecutar(m, lambda t: pose_de_pie(), C.DWELL_BLOQUEO_S + C.DWELL_S + 1)
    assert nombre(sig) == "EscenaMenu"


def test_jugador_nuevo_con_teclado(ctx):
    from scenes.menu import EscenaJugador
    j = EscenaJugador(ctx)
    j.draw(frame_negro())
    j.menu.indice = len(j.menu.botones) - 2                 # «Nuevo jugador»
    tecla(j, "enter")
    assert j.escribiendo
    for c in "Ana":
        j.on_key(c)
    j.on_key("retroceso")
    j.on_key("a")
    j.draw(frame_negro())
    sig = tecla(j, "enter")
    assert nombre(sig) == "EscenaMenu" and ctx.jugador == "Ana"
    assert "Ana" in ctx.almacen.jugadores()


def pasar_equilibrio(escena, pose_fn=de_pie, segundos=C.PRUEBA_EQUILIBRIO_S):
    assert nombre(escena) == "EscenaEquilibrio"
    escena = tecla(escena, "enter")                         # empezar (alternativa a brazos arriba)
    assert escena.fase == "cuenta"
    return ejecutar(escena, pose_fn, C.CUENTA_ATRAS_S + segundos + 4)


def test_flujo_evaluacion_completo(ctx):
    from scenes.flows import FlujoEvaluacion
    e = FlujoEvaluacion(ctx).empezar()
    assert nombre(e) == "EscenaColocacion"
    e = ejecutar(e, de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    for _ in range(3):                                      # pies juntos, semitándem, tándem
        e = pasar_equilibrio(e)
    assert nombre(e) == "EscenaColocacion" and e.vista == "lado"
    e = ejecutar(e, lambda t: pose_sentado_lado(90), C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    assert nombre(e) == "EscenaSilla"
    e = tecla(e, "enter")
    e = ejecutar(e, silla_ciclos(2.0, C.SILLA_CUENTA_ATRAS_S), C.SILLA_CUENTA_ATRAS_S + 15)
    assert nombre(e) == "EscenaPregunta"                    # ¿pruebas complementarias?
    e.draw(frame_negro())
    e = tecla(e, "derecha")
    e = tecla(e, "enter")                                   # «No, ver resultados»
    assert nombre(e) == "EscenaResultadosEvaluacion"
    assert e.res["total"] == 8, e.res
    assert e.res["complementarias"] == {}
    filas = ctx.almacen.historial("Test")
    assert len(filas) == 1 and filas[0]["sppb_total"] == "8"
    assert "sppb_perfecta" in ctx.perfil()["logros"]
    assert nombre(tecla(e, "enter")) == "EscenaHistorial"


def una_pierna_tras(inicio):
    """Pose que levanta el pie izquierdo a partir de `inicio` segundos."""
    return lambda t: pose_de_pie(elev_izq=0.5 if t >= inicio else 0.0)


def corrigiendo(escena, pose_fn, k=0.01):
    """Jugador sintético que mueve la cadera en contra del funambulista o la bailarina (k = aw por grado)."""
    def f(t):
        p = pose_fn(t)
        c = getattr(escena, "cuerda", None)
        if c is not None:
            dx = -k * c.angulo * escena.calib.anchura_hombros / p.aspecto     # aw → x normalizada
            p.lm[[C.CADERA_IZQ, C.CADERA_DER], 0] += max(-0.05, min(0.05, dx))
        return p
    return f


def marchando(periodo=0.6, altura=0.7):
    """Pose que alterna rodillas: cada paso dura `periodo` s."""
    def f(t):
        k, resto = divmod(t, periodo)
        e = altura if resto < periodo / 2 else 0.0
        return pose_de_pie(elev_izq=e if int(k) % 2 == 0 else 0.0, elev_der=e if int(k) % 2 == 1 else 0.0)
    return f


def test_evaluacion_con_complementarias(ctx):
    from scenes.flows import FlujoEvaluacion
    flujo = FlujoEvaluacion(ctx)
    for v in (10.0, 10.0, 10.0):
        flujo.protocolo.registrar(v)                        # SPPB de equilibrio ya hecha
    e = flujo.terminar_prueba({"prueba": "silla", "tiempo": 12.0, "manos": False})
    assert nombre(e) == "EscenaPregunta"
    e.draw(frame_negro())
    e = tecla(e, "enter")                                   # «Sí, hacerlas»
    assert nombre(e) == "EscenaColocacion" and e.vista == "frente"
    e = ejecutar(e, de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    assert nombre(e) == "EscenaEquilibrio" and e.prueba == "una_pierna"
    e = tecla(e, "enter")
    e = ejecutar(e, una_pierna_tras(C.CUENTA_ATRAS_S + 1), C.CUENTA_ATRAS_S + 1 + 8)
    assert e.t == pytest.approx(8, abs=0.3)                 # solo cuenta con el pie levantado (de t=4 a t=12)
    e = ejecutar(e, lambda t: pose_de_pie(), 4)             # baja el pie → fin
    assert nombre(e) == "EscenaMarcha"
    e = tecla(e, "enter")
    e = ejecutar(e, marchando(), C.CUENTA_ATRAS_S + C.MARCHA_EVAL_S + 4, dibujar_cada=15)
    assert nombre(e) == "EscenaResultadosEvaluacion"
    comp = e.res["complementarias"]
    assert comp["una_pierna"]["valor"] == pytest.approx(8, abs=0.5)
    esperado = C.MARCHA_EVAL_S / 0.6 / 2                           # un paso cada 0,6 s, la mitad con la dcha.
    assert comp["marcha"]["valor"] == pytest.approx(esperado, abs=3)
    fila = ctx.almacen.historial("Test")[-1]
    assert fila["t_una_pierna"] != "" and fila["pasos_marcha"] != ""


def test_evaluacion_falla_pies_juntos_sigue_con_semitandem(ctx):
    from scenes.flows import FlujoEvaluacion
    e = ejecutar(FlujoEvaluacion(ctx).empezar(), de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    e = tecla(e, "enter")
    e = ejecutar(e, de_pie, C.CUENTA_ATRAS_S + 2)
    assert e.fase == "jugando"
    e = tecla(e, "f")                                       # el evaluador marca pérdida de equilibrio
    e = ejecutar(e, de_pie, 4)
    assert nombre(e) == "EscenaEquilibrio" and e.prueba == "semitandem"   # sin recolocarse


def test_evaluacion_pausa_si_se_pierden_los_pies(ctx):
    from scenes.flows import FlujoEvaluacion
    e = ejecutar(FlujoEvaluacion(ctx).empezar(), de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    e = tecla(e, "enter")
    e = ejecutar(e, de_pie, C.CUENTA_ATRAS_S + 1)
    sin_pies = pose_de_pie()
    sin_pies.lm[[C.TOBILLO_IZQ, C.TOBILLO_DER], 2] = 0.1
    ejecutar(e, lambda t: sin_pies, 1.0)
    assert e.fase == "pausa" and "pies" in e.motivo_pausa
    e.draw(frame_negro())
    ejecutar(e, lambda t: pose_de_pie(brazos_arriba=True), C.BRAZOS_ARRIBA_S + 0.3)
    assert e.fase == "cuenta" and e.t == 0.0                # en Evaluación se repite la prueba


def test_aventura_nivel_1_tres_estrellas_y_desbloqueo(ctx):
    from scenes.flows import FlujoAventura
    mapa = FlujoAventura(ctx).mapa()
    mapa.draw(frame_negro())
    actos = tecla(mapa, "enter")
    assert nombre(actos) == "EscenaMapa" and actos.acto_id == 1
    actos.draw(frame_negro())
    e = tecla(actos, "enter")
    assert nombre(e) == "EscenaColocacion"
    e = ejecutar(e, de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    e = pasar_equilibrio(e)
    assert nombre(e) == "EscenaResultadosNivel"
    assert e.estrellas == 3 and e.res["puntos"] > 0
    e = ejecutar(e, lambda t: None, 2)
    p = ctx.perfil()
    assert p["progreso"] == {"1": {"1": 3}}
    from games.progress import acto_desbloqueado
    assert acto_desbloqueado(p["progreso"], 2)
    assert nombre(tecla(e, "enter")) == "EscenaColocacion"  # Repetir


def test_aventura_balanceo_tira_el_vaso(ctx):
    from scenes.flows import FlujoAventura
    e = FlujoAventura(ctx).jugar(1, 1)
    e = ejecutar(e, de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    e = tecla(e, "enter")
    e = ejecutar(e, de_pie, C.CUENTA_ATRAS_S + 0.2)
    e = ejecutar(e, lambda t: pose_de_pie(dx_cadera=0.04), 8)   # ~0,33 aw hacia un lado
    assert nombre(e) == "EscenaResultadosNivel"
    assert e.estrellas == 0 and "vaso" in e.res["motivo"]


@pytest.mark.parametrize("acto, nivel", [(1, 2), (1, 3), (1, 4), (2, 1), (2, 3)])
def test_aventura_niveles_equilibrio(ctx, acto, nivel):
    from scenes.flows import FlujoAventura
    e = FlujoAventura(ctx).jugar(acto, nivel)
    e = ejecutar(e, de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    duracion = C.ACTOS[acto - 1]["niveles"][nivel - 1]["duracion_s"]
    e = pasar_equilibrio(e, segundos=duracion)
    assert nombre(e) == "EscenaResultadosNivel"
    e.draw(frame_negro())


@pytest.mark.parametrize("nivel", [1, 3, 4])
def test_aventura_bailarina(ctx, nivel):
    from scenes.flows import FlujoAventura
    e = FlujoAventura(ctx).jugar(3, nivel)
    e = ejecutar(e, de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    assert nombre(e) == "EscenaEquilibrio" and e.mecanica == "pelota"
    e = tecla(e, "enter")
    duracion = C.ACTOS[2]["niveles"][nivel - 1]["duracion_s"]
    e = ejecutar(e, corrigiendo(e, una_pierna_tras(C.CUENTA_ATRAS_S + 0.5)), C.CUENTA_ATRAS_S + duracion + 5)
    assert nombre(e) == "EscenaResultadosNivel"
    assert e.res["completado"] and e.estrellas >= 1


def test_bailarina_apoyar_el_pie_termina(ctx):
    from scenes.flows import FlujoAventura
    e = ejecutar(FlujoAventura(ctx).jugar(3, 1), de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    e = tecla(e, "enter")
    e = ejecutar(e, una_pierna_tras(C.CUENTA_ATRAS_S + 0.5), C.CUENTA_ATRAS_S + 3)
    e = ejecutar(e, lambda t: pose_de_pie(), 4)
    assert nombre(e) == "EscenaResultadosNivel"
    assert e.estrellas == 0 and "apoyado" in e.res["motivo"]


@pytest.mark.parametrize("nivel", [1, 2, 4])
def test_aventura_desfile(ctx, nivel):
    from scenes.flows import FlujoAventura
    e = FlujoAventura(ctx).jugar(4, nivel)
    e = ejecutar(e, de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    assert nombre(e) == "EscenaMarcha"
    e = tecla(e, "enter")
    niv = C.ACTOS[3]["niveles"][nivel - 1]
    e = ejecutar(e, marchando(), C.CUENTA_ATRAS_S + niv["duracion_s"] + 4, dibujar_cada=10)
    assert nombre(e) == "EscenaResultadosNivel"
    assert e.res["pasos"] >= niv["estrellas_pasos"][0] and e.estrellas >= 1
    if niv["tempo_bpm"] == 100:
        assert e.res["al_compas"] > e.res["pasos"] // 2     # marchando a 100 ppm exactos
    e.draw(frame_negro())


@pytest.mark.parametrize("nivel", [1, 3])
def test_aventura_canon(ctx, nivel):
    from scenes.flows import FlujoAventura
    e = FlujoAventura(ctx).jugar(5, nivel)
    e = ejecutar(e, lambda t: pose_sentado_lado(90), C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    assert nombre(e) == "EscenaSilla"
    e = tecla(e, "enter")
    reps = C.ACTOS[4]["niveles"][nivel - 1]["repeticiones"]
    e = ejecutar(e, silla_ciclos(2.0, C.SILLA_CUENTA_ATRAS_S),
                 C.SILLA_CUENTA_ATRAS_S + reps * 2 + C.CANON_VUELO_S + 5, dibujar_cada=3)
    assert nombre(e) == "EscenaResultadosNivel"
    assert e.res["repeticiones"] == reps and e.estrellas >= 1


def test_historial_con_datos(ctx):
    from scenes.results_scene import EscenaHistorial
    ctx.almacen.registrar_sesion({"jugador": "Test", "modo": "evaluacion", "sppb_total": 5})
    ctx.almacen.registrar_sesion({"jugador": "Test", "modo": "evaluacion", "sppb_total": 7})
    p = ctx.perfil()
    p["puntos_mejores"] = {"1-1": 300}
    ctx.almacen.guardar_perfil(p)
    h = EscenaHistorial(ctx)
    h.enter()
    out = h.draw(frame_negro())
    assert out.shape == (ALTO, ANCHO, 3)
    assert h.ranking[0] == ("Test", 300)
    assert h.on_key("esc") is not None


def test_colocacion_mensajes(ctx):
    from core.calibration import evaluar_encuadre
    assert evaluar_encuadre(None, "frente")
    assert evaluar_encuadre(pose_de_pie(), "frente") == ""
    lejos = pose_de_pie()
    lejos.lm[:, 1] = 0.4 + (lejos.lm[:, 1] - 0.4) * 0.5     # persona pequeña
    assert "Acércate" in evaluar_encuadre(lejos, "frente")
    sin_pies = pose_de_pie()
    sin_pies.lm[[C.TOBILLO_IZQ, C.TOBILLO_DER], 2] = 0.1
    assert "pies" in evaluar_encuadre(sin_pies, "frente")
    assert "lado" in evaluar_encuadre(pose_de_pie(), "lado")
    assert evaluar_encuadre(pose_sentado_lado(90), "lado") == ""
    assert "frente" in evaluar_encuadre(pose_sentado_lado(90), "frente")


def test_superposicion_debug(ctx):
    from main import dibujar_debug, traducir_tecla
    from scenes.chair_scene import EscenaSilla
    from core.calibration import Calibrador
    cal = None
    c = Calibrador("lado")
    while cal is None:
        cal = c.actualizar(pose_sentado_lado(90), DT)
    e = EscenaSilla(ctx, cal, "aventura", lambda r: None, lambda: None, C.ACTOS[3]["niveles"][0], C.ACTOS[3])
    e.update(pose_sentado_lado(120), DT)
    out = e.draw(frame_negro())
    dibujar_debug(out, e, pose_sentado_lado(120), 29.5)
    assert traducir_tecla(13) == "enter" and traducir_tecla(65362) == "arriba"
    assert traducir_tecla(2621440) == "abajo" and traducir_tecla(ord("A")) == "a" and traducir_tecla(-1) is None


def test_proporciones_reales_16_9():
    """Regresión: en 16:9 las x vienen encogidas; una persona real de frente debe pasar el encuadre
    y el ángulo de rodilla medido debe ser el real."""
    from core.calibration import anchura_hombros, altura_torso, evaluar_encuadre
    from core.geometry import angulo
    p = pose_de_pie()
    assert anchura_hombros(p) / altura_torso(p) == pytest.approx(0.16 / 0.22, rel=0.01)
    assert evaluar_encuadre(p, "frente") == ""
    for real in (90, 120, 160):
        s = pose_sentado_lado(real)
        assert angulo(s.q(23), s.q(25), s.q(27)) == pytest.approx(real, abs=0.5)


def test_menu_practica_y_ejercicios(ctx):
    from scenes.menu import EscenaMenu
    m = EscenaMenu(ctx)
    m.draw(frame_negro())
    m.menu.indice = 2
    p = tecla(m, "enter")
    assert nombre(p) == "EscenaPractica"
    p.draw(frame_negro())
    assert len(p.menu.botones) == len(C.EJERCICIOS_PRACTICA) + 1
    assert all(b.activo for b in p.menu.botones)            # sin candados
    p.menu.indice = 1                                       # semitándem
    e = tecla(p, "enter")
    assert nombre(e) == "EscenaColocacion"


@pytest.mark.parametrize("prueba", ["semitandem", "una_pierna", "marcha", "silla"])
def test_practica_completa(ctx, prueba):
    from scenes.flows import FlujoPractica
    flujo = FlujoPractica(ctx)
    e = flujo.jugar(prueba)
    inicial = (lambda t: pose_sentado_lado(90)) if prueba == "silla" else de_pie
    e = ejecutar(e, inicial, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    e = tecla(e, "enter")
    if prueba == "silla":
        e = ejecutar(e, silla_ciclos(2.0, C.SILLA_CUENTA_ATRAS_S), C.SILLA_CUENTA_ATRAS_S + 15)
    elif prueba == "marcha":
        e = ejecutar(e, marchando(), C.CUENTA_ATRAS_S + C.MARCHA_EVAL_S + 4, dibujar_cada=20)
    elif prueba == "una_pierna":
        e = ejecutar(e, una_pierna_tras(C.CUENTA_ATRAS_S + 0.5), C.CUENTA_ATRAS_S + C.UNA_PIERNA_EVAL_S + 5,
                     dibujar_cada=10)
    else:
        e = ejecutar(e, de_pie, C.CUENTA_ATRAS_S + C.PRUEBA_EQUILIBRIO_S + 4)
    assert nombre(e) == "EscenaResultadoPractica"
    assert e.valor and e.consejos
    e.draw(frame_negro())
    fila = ctx.almacen.historial("Test")[-1]
    assert fila["modo"] == "practica" and fila["prueba"] == prueba
    assert nombre(tecla(e, "enter")) == "EscenaColocacion"  # Repetir


# -- Cuerda floja con física inestable ---------------------------------------------------

def _nivel_cuerda(ctx, nivel):
    from scenes.flows import FlujoAventura
    e = ejecutar(FlujoAventura(ctx).jugar(2, nivel), de_pie, C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    assert nombre(e) == "EscenaEquilibrio" and e.mecanica == "cuerda"
    return tecla(e, "enter")


def test_cuerda_sin_corregir_se_cae(ctx):
    e = _nivel_cuerda(ctx, 4)
    e = ejecutar(e, de_pie, C.CUENTA_ATRAS_S + 25)
    assert nombre(e) == "EscenaResultadosNivel" and not e.res["completado"] and e.estrellas == 0


@pytest.mark.parametrize("nivel", [1, 3, 4])
def test_cuerda_corrigiendo_se_supera(ctx, nivel):
    e = _nivel_cuerda(ctx, nivel)
    duracion = C.ACTOS[1]["niveles"][nivel - 1]["duracion_s"]
    e = ejecutar(e, corrigiendo(e, de_pie), C.CUENTA_ATRAS_S + duracion + 5, dibujar_cada=3)
    assert nombre(e) == "EscenaResultadosNivel" and e.res["completado"] and e.estrellas >= 1


def test_cruza_la_cuerda(ctx):
    e = _nivel_cuerda(ctx, 2)
    assert e.cruzar
    niv = C.ACTOS[1]["niveles"][1]
    e = ejecutar(e, corrigiendo(e, de_pie), C.CUENTA_ATRAS_S + niv["duracion_s"] + 5, dibujar_cada=3)
    assert nombre(e) == "EscenaResultadosNivel" and e.res["completado"]
    assert e.res["avance"] == pytest.approx(1.0)
    assert niv["avance_s"] - 0.1 <= e.res["tiempo"] < niv["duracion_s"]
    assert e.estrellas >= 2                                   # el jugador sintético corrige bien
    e.draw(frame_negro())


# -- El Hombre Bala, nivel 4: al ritmo del cañón ------------------------------------------

def _nivel_ritmo(ctx):
    from scenes.flows import FlujoAventura
    e = FlujoAventura(ctx).jugar(5, 4)
    e = ejecutar(e, lambda t: pose_sentado_lado(90), C.ENCUADRE_OK_S + C.CALIB_DURACION_S + 1)
    assert nombre(e) == "EscenaSilla" and e.ritmo is not None
    return tecla(e, "enter")


def test_canon_al_ritmo_tres_estrellas(ctx):
    e = _nivel_ritmo(ctx)
    periodo = C.ACTOS[4]["niveles"][3]["ritmo_s"]
    # de pie (pico del ciclo) justo en cada golpe: t de juego = periodo, 2·periodo…
    e = ejecutar(e, silla_ciclos(periodo, C.SILLA_CUENTA_ATRAS_S + periodo / 2),
                 C.SILLA_CUENTA_ATRAS_S + periodo * 6 + C.CANON_VUELO_S + 5, dibujar_cada=3)
    assert nombre(e) == "EscenaResultadosNivel"
    assert e.res["repeticiones"] == 5 and e.res["fuera_ritmo"] == 0 and e.estrellas == 3


def test_canon_fuera_de_ritmo_no_cuenta(ctx):
    e = _nivel_ritmo(ctx)
    e = ejecutar(e, silla_ciclos(2.0, C.SILLA_CUENTA_ATRAS_S), C.SILLA_CUENTA_ATRAS_S + 20, dibujar_cada=3)
    assert nombre(e) == "EscenaSilla" and e.fuera_ritmo >= 2          # a su aire: varias no valen
    assert e.contador.cuenta < 5 + e.fuera_ritmo
