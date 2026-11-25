"""Ajustes (persistencia y pantalla), último jugador, pantalla de la SPPB y siluetas de pies."""
import json

import numpy as np
import pytest

import config as C
from core.settings import Ajustes
from core.storage import Almacen
from tests.sinteticos import ALTO, ANCHO, pose_de_pie


def frame_negro():
    return np.zeros((ALTO, ANCHO, 3), np.uint8)


# -- Ajustes -------------------------------------------------------------------

def test_ajustes_por_defecto_y_volumen_limitado():
    a = Ajustes()
    assert a.musica and a.fondo and a.animaciones and not a.deteccion_rapida
    assert a.factor_volumen == pytest.approx(C.VOLUMEN_MUSICA)      # 50 % = volumen de siempre
    for _ in range(20):
        a.cambiar_volumen(+1)
    assert a.volumen_musica == 100 and a.factor_volumen == pytest.approx(C.VOLUMEN_MUSICA_MAX)
    for _ in range(20):
        a.cambiar_volumen(-1)
    assert a.volumen_musica == 0 and a.factor_volumen == 0


def test_ajustes_se_guardan_y_se_leen(tmp_path):
    alm = Almacen(str(tmp_path))
    a = alm.cargar_ajustes()
    a.fondo, a.volumen_musica, a.ultimo_jugador = False, 30, "Ana"
    alm.guardar_ajustes(a)
    b = Almacen(str(tmp_path)).cargar_ajustes()
    assert (b.fondo, b.volumen_musica, b.ultimo_jugador) == (False, 30, "Ana")


def test_ajustes_dañados_o_con_tipos_erroneos(tmp_path):
    alm = Almacen(str(tmp_path))
    with open(alm.ruta_ajustes, "w", encoding="utf-8") as f:
        f.write("{esto no es json")
    assert alm.cargar_ajustes() == Ajustes()
    with open(alm.ruta_ajustes, "w", encoding="utf-8") as f:
        json.dump({"fondo": "no", "volumen_musica": 500, "desconocida": 1}, f)
    a = alm.cargar_ajustes()
    assert a.fondo is True and a.volumen_musica == 100


def test_volumen_del_mezclador():
    from ui.audio import Mezclador
    m = Mezclador({"musica": np.ones(100, np.float32)})
    m.volumen_musica = 0.2
    assert m.mezclar(10)[0] == pytest.approx(0.2)
    m.volumen_musica = 0.0
    assert m.mezclar(10)[0] == 0.0


# -- Último jugador -------------------------------------------------------------

def test_se_recuerda_el_ultimo_jugador(ctx):
    from main import jugador_inicial
    from scenes.menu import EscenaJugador
    e = EscenaJugador(ctx)
    e.draw(frame_negro())
    e._elegir("Ana")
    alm = ctx.almacen
    ajustes = alm.cargar_ajustes()
    assert ajustes.ultimo_jugador == "Ana"
    assert jugador_inicial(alm, ajustes, None) == "Ana"
    assert jugador_inicial(alm, ajustes, "Luis") == "Luis"           # --jugador manda
    ajustes.ultimo_jugador = "Borrado"
    assert jugador_inicial(alm, ajustes, None) == "Invitado"         # perfil que ya no existe


# -- Pantalla de ajustes -----------------------------------------------------------

def test_pantalla_de_ajustes(ctx):
    from scenes.settings_scene import EscenaAjustes
    e = EscenaAjustes(ctx)
    e.update(pose_de_pie(), 1 / 30)
    e.draw(frame_negro())
    assert ctx.fondo.activado
    e.accion("fondo")
    assert not ctx.fondo.activado and not ctx.almacen.cargar_ajustes().fondo
    assert any(b.etiqueta == "Fondo circo: No" for b in e.menu.botones)
    e.accion("subir")
    assert ctx.almacen.cargar_ajustes().volumen_musica == 50 + C.AJUSTES_VOLUMEN_PASO
    e.accion("animaciones")
    assert not ctx.animaciones
    e.draw(frame_negro())
    assert type(e.on_key("esc")).__name__ == "EscenaMenu"


def test_sin_animaciones_no_hay_confeti():
    from ui.particles import Confeti
    c = Confeti(1, activo=False)
    c.lanzar(1280)
    assert len(c.pos) == 0
    c = Confeti(1)
    c.lanzar(1280)
    assert len(c.pos) == C.CONFETI_PARTICULAS


def test_menu_principal_abre_ajustes_e_info(ctx):
    from scenes.menu import EscenaMenu
    m = EscenaMenu(ctx)
    m.draw(frame_negro())
    assert {b.accion for b in m.menu.botones} >= {"ajustes", "info", "evaluacion", "salir"}
    assert type(m._ejecutar("ajustes")).__name__ == "EscenaAjustes"
    info = m._ejecutar("info")
    assert type(info).__name__ == "EscenaInfoSPPB" and info.empezar is None


# -- Pantalla «¿Qué es la SPPB?» ------------------------------------------------------

def test_evaluacion_empieza_explicando_la_sppb(ctx):
    from scenes.flows import FlujoEvaluacion
    e = FlujoEvaluacion(ctx).iniciar()
    assert type(e).__name__ == "EscenaInfoSPPB"
    e.update(pose_de_pie(), 1 / 30)
    e.draw(frame_negro())
    e.accion("pagina")                       # página de la puntuación
    assert e.pagina == 1
    e.draw(frame_negro())
    assert type(e.accion("empezar")).__name__ == "EscenaColocacion"
    assert type(e.accion("volver")).__name__ == "EscenaMenu"


# -- Siluetas de pies ------------------------------------------------------------------

@pytest.mark.parametrize("prueba", ["pies_juntos", "semitandem", "tandem", "una_pierna"])
def test_siluetas_de_pies_con_contorno(prueba):
    from ui import pictograms
    from ui.sprites import Sprites
    sp = Sprites()                                           # carga assets/pies_*.png
    nombre = "pies_juntos" if prueba in ("pies_juntos", "una_pierna") else f"pies_{prueba}"
    assert sp.tiene(nombre)
    for tam in (40, 180, 400):
        f = frame_negro()
        pictograms.dibujar_pies(f, (ANCHO // 2, ALTO // 2), tam * 0.42, prueba, 0.5, sp)
        assert (f.min(axis=2) > 200).any()                   # se ve el contorno claro
    f = frame_negro()
    pictograms.instrucciones(f, prueba, "Título", "Línea", 0.2, 0.5, "", sp)
    pictograms.recordatorio(f, prueba, 0.2, sp)


# -- Esqueleto ----------------------------------------------------------------------------

def test_el_esqueleto_se_dibuja_en_todas_las_escenas(ctx):
    from scenes.menu import EscenaMenu
    m = EscenaMenu(ctx)
    m.update(pose_de_pie(), 1 / 30)
    con = m.fondo(frame_negro())
    azul = (con == C.ESQUELETO_COLOR).all(axis=2).sum()
    assert azul > 200                                    # líneas del cuerpo, no solo puntos
    ctx.ajustes.esqueleto = False
    sin = m.fondo(frame_negro())
    assert (sin == C.ESQUELETO_COLOR).all(axis=2).sum() == 0
