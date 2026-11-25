"""Consejos de mejora: existen en TODOS los niveles de la Aventura, ejercicios de Práctica y la Evaluación."""
import pytest

import config as C
from games.practice import MAXIMOS_SPPB, consejos
from games.tips import consejo_evaluacion, consejos_nivel


def resultado_tipo(acto: dict, nivel: dict, estrellas: int) -> dict:
    """Resultado verosímil para ese nivel con ese número de estrellas."""
    m = acto["mecanica"]
    if m == "canon" and nivel.get("ritmo_s"):
        fuera = {0: 0, 1: 5, 2: 1, 3: 0}[estrellas]
        return {"prueba": "silla", "tiempo": None if estrellas == 0 else 20.0, "completado": estrellas > 0,
                "repeticiones": 3 if estrellas == 0 else 5, "objetivo": 5, "fuera_ritmo": fuera, "ritmo": True}
    if m == "canon":
        t = {0: None, 1: nivel["estrellas_s"][0] - 1, 2: nivel["estrellas_s"][1] - 0.5, 3: 5.0}[estrellas]
        return {"prueba": "silla", "tiempo": t, "completado": t is not None, "repeticiones": 3 if t is None else 5,
                "objetivo": nivel["repeticiones"], "incompletas": 0, "manos": False,
                "motivo": "Se acabó el tiempo" if t is None else "¡Conseguido!"}
    if m == "tambor":
        p = [nivel["estrellas_pasos"][0] - 5, *nivel["estrellas_pasos"]][estrellas]
        return {"prueba": "marcha", "pasos": p, "tiempo": nivel["duracion_s"], "completado": True}
    if nivel.get("cruzar"):
        t = {0: nivel["duracion_s"], 1: nivel["estrellas_s"][0] - 1, 2: nivel["estrellas_s"][1] - 1, 3: 10.0}[estrellas]
        return {"prueba": acto["prueba"], "tiempo": t, "completado": estrellas > 0, "avance": 0.6,
                "motivo": "Se acabó el tiempo" if estrellas == 0 else "¡Has cruzado la cuerda!"}
    pel = {0: 1.0, 1: 0.9, 2: 0.6, 3: 0.1}[estrellas]
    return {"prueba": acto["prueba"], "tiempo": nivel["duracion_s"], "completado": estrellas > 0,
            "peligro_max": pel, "motivo": "¡Se ha caído el vaso!" if estrellas == 0 else "¡Conseguido!"}


@pytest.mark.parametrize("acto_id", [a["id"] for a in C.ACTOS])
@pytest.mark.parametrize("estrellas", [0, 1, 2, 3])
def test_todos_los_niveles_tienen_consejo(acto_id, estrellas):
    acto = C.ACTOS[acto_id - 1]
    for nivel in acto["niveles"]:
        lista = consejos_nivel(acto, nivel, resultado_tipo(acto, nivel, estrellas), estrellas)
        assert lista and all(isinstance(c, str) and len(c) > 15 for c in lista)
        if estrellas == 0:
            assert "1 estrella" in " ".join(lista)              # qué hacer para no fallar
        elif estrellas < 3:
            assert f"{estrellas + 1} estrellas" in " ".join(lista)   # qué hace falta para la siguiente


def test_consejos_concretos():
    camarero, cuerda, bailarina = C.ACTOS[0], C.ACTOS[1], C.ACTOS[2]
    c = consejos_nivel(camarero, camarero["niveles"][0], {"peligro_max": 0.83, "motivo": "¡Conseguido!"}, 1)
    assert "83 %" in c[0] and "75 %" in c[0] and "40 %" in c[0]
    c = consejos_nivel(cuerda, cuerda["niveles"][0], {"motivo": "Has movido los pies"}, 0)
    assert "pies" in c[0]
    c = consejos_nivel(bailarina, bailarina["niveles"][0], {"motivo": "Has apoyado el pie"}, 0)
    assert "pie levantado" in c[0]
    silla = C.ACTOS[4]
    c = consejos_nivel(silla, silla["niveles"][0], {"repeticiones": 5, "objetivo": 5, "tiempo": 15.0,
                                                    "incompletas": 2}, 2)
    assert "13,69" in c[0] and "no contaron" in c[1]


@pytest.mark.parametrize("prueba", C.EJERCICIOS_PRACTICA)
def test_practica_dice_el_siguiente_objetivo(prueba):
    if prueba == "marcha":
        flojo = {"pasos": 20, "pasos_der": 10, "tiempo": C.MARCHA_EVAL_S}
    elif prueba == "silla":
        flojo = {"repeticiones": 5, "tiempo": 15.0, "incompletas": 0, "manos": False}
    else:
        flojo = {"motivo": "Pérdida de equilibrio", "tiempo": 2.0}
    lista = consejos(prueba, flojo)
    assert any(any(ch.isdigit() for ch in c) for c in lista)        # objetivo con un número concreto


def test_practica_silla_incompleta_y_maxima():
    assert "Completa las 5" in consejos("silla", {"repeticiones": 3, "tiempo": None})[0]
    assert "11,19" in consejos("silla", {"repeticiones": 5, "tiempo": 12.5})[0]
    assert not any("puntos" in c for c in consejos("silla", {"repeticiones": 5, "tiempo": 9.0}))


def test_evaluacion_recomienda_que_entrenar():
    txt = consejo_evaluacion({"pies_juntos": 1, "semitandem": 1, "tandem": 2, "silla": 1}, MAXIMOS_SPPB)
    assert C.NOMBRES_PRUEBA["silla"] in txt and "Práctica" in txt
    assert "máxima" in consejo_evaluacion(dict(MAXIMOS_SPPB), MAXIMOS_SPPB)
