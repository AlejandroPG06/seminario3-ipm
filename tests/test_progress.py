"""Progreso de la Aventura, logros y persistencia."""
import config as C
from core.storage import Almacen
from games.achievements import estadisticas, nuevos_logros
from games.progress import (acto_desbloqueado, actos_desbloqueados, nivel_desbloqueado,
                            registrar_resultado)


def test_inicio_solo_acto_1_nivel_1():
    assert acto_desbloqueado({}, 1)
    assert not acto_desbloqueado({}, 2)
    assert nivel_desbloqueado({}, 1, 1)
    assert not nivel_desbloqueado({}, 1, 2)
    assert not nivel_desbloqueado({}, 2, 1)


def test_una_estrella_abre_nivel_pero_no_acto():
    p, mejora = registrar_resultado({}, 1, 1, 1)
    assert mejora
    assert nivel_desbloqueado(p, 1, 2)
    assert not acto_desbloqueado(p, 2)


def test_dos_estrellas_abren_acto():
    p, _ = registrar_resultado({}, 1, 1, 2)
    assert acto_desbloqueado(p, 2)
    assert nivel_desbloqueado(p, 2, 1)
    assert not acto_desbloqueado(p, 3)
    assert actos_desbloqueados(p) == 2


def test_no_empeora_record():
    p, _ = registrar_resultado({}, 1, 1, 3)
    p2, mejora = registrar_resultado(p, 1, 1, 1)
    assert not mejora and p2["1"]["1"] == 3
    assert p == {"1": {"1": 3}}            # el original no se modifica


def test_cadena_de_desbloqueo_hasta_acto_4():
    p = {}
    for acto in (1, 2, 3):
        p, _ = registrar_resultado(p, acto, 1, 2)
    assert acto_desbloqueado(p, 4)


def test_logros(tmp_path):
    alm = Almacen(str(tmp_path))
    perfil = alm.perfil("Ana")
    perfil["progreso"] = {"1": {"1": 2}, "2": {"1": 3}, "3": {"1": 3}, "4": {"1": 2}}
    perfil["estadisticas"]["compas_max"] = 45
    perfil["estadisticas"]["racha_max_s"] = 12.0
    alm.registrar_sesion({"jugador": "Ana", "modo": "evaluacion", "sppb_total": 8, "t_silla": "10.50",
                          "t_una_pierna": "30.00"})
    stats = estadisticas(perfil, alm.historial("Ana"))
    assert stats["sesiones"] == 1 and stats["sppb_max"] == 8 and stats["silla_mejor_s"] == 10.5
    ids = {l["id"] for l in nuevos_logros(stats, [])}
    assert {"primera_funcion", "pulso_acero", "funambulista", "bailarina", "flamenco", "tamborilero",
            "muelle_humano", "gran_estreno", "sppb_perfecta"} <= ids
    assert "constancia" not in ids
    assert nuevos_logros(stats, list(ids)) == []


def test_logros_definidos_como_datos():
    claves = {l["clave"] for l in C.LOGROS}
    stats = estadisticas({"progreso": {}, "estadisticas": {}}, [])
    for clave in claves:
        assert clave in stats


def test_almacen_perfiles_e_historial(tmp_path):
    alm = Almacen(str(tmp_path))
    assert alm.jugadores() == []
    p = alm.perfil("Luis")
    p["progreso"] = {"1": {"1": 3}}
    alm.guardar_perfil(p)
    assert alm.jugadores() == ["Luis"]
    assert Almacen(str(tmp_path)).perfil("Luis")["progreso"] == {"1": {"1": 3}}
    alm.registrar_sesion({"jugador": "Luis", "modo": "aventura", "puntos": 120})
    alm.registrar_sesion({"jugador": "Otra", "modo": "aventura", "puntos": 5})
    assert len(alm.historial()) == 2
    assert alm.historial("Luis")[0]["puntos"] == "120"


def test_historial_migra_cabecera_antigua(tmp_path):
    """Un CSV con columnas antiguas se reescribe con las nuevas sin perder filas."""
    ruta = tmp_path / C.HISTORIAL_ARCHIVO
    ruta.write_text("fecha,jugador,modo,t_silla\n2026-11-01,Ana,evaluacion,12.00\n", encoding="utf-8")
    alm = Almacen(str(tmp_path))
    alm.registrar_sesion({"jugador": "Ana", "modo": "practica", "prueba": "marcha", "pasos_marcha": 70})
    filas = alm.historial("Ana")
    assert len(filas) == 2
    assert filas[0]["t_silla"] == "12.00" and filas[1]["pasos_marcha"] == "70"
