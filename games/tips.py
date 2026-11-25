"""Consejos de «qué hacer para mejorar» en todas las pantallas de resultados (lógica pura).

- Aventura: si fallas, qué hacer para conseguir al menos 1 estrella; con 1 o 2,
  qué hace falta para la siguiente; con 3, que pruebes el siguiente nivel.
- Práctica: el siguiente objetivo de puntos SPPB (o de la prueba complementaria).
- Evaluación: qué prueba conviene entrenar en el Modo Práctica.
"""
from __future__ import annotations

import config as C
from games.scoring import referencia_marcha

QUE = {"bandeja": "El vaso", "cuerda": "El funambulista", "pelota": "La bailarina"}

TRUCO = {
    "bandeja": "Mantén la cadera quieta; si el vaso se desliza, mueve la cadera un poco hacia el lado contrario.",
    "cuerda": "Sigue la flecha con la cadera en cuanto aparezca, con movimientos pequeños.",
    "pelota": "Sigue la flecha con la cadera en cuanto aparezca, con movimientos pequeños.",
}
TRUCO_VIENTO = "Cuando veas las flechas amarillas, prepárate: la ráfaga empujará hacia ese lado."


def _s(v: float) -> str:
    """Segundos con coma decimal y sin ceros sobrantes (10, 13,69)."""
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _pct(v: float) -> str:
    return f"{v * 100:.0f} %"


# ---------------------------------------------------------------------------
# Aventura
# ---------------------------------------------------------------------------


def consejos_nivel(acto: dict, nivel: dict, res: dict, estrellas: int) -> list[str]:
    """1-2 frases con lo que hay que hacer para conseguir (más) estrellas en ese nivel."""
    if estrellas >= 3:
        return ["¡Tres estrellas! Prueba el siguiente nivel."]
    mecanica = acto["mecanica"]
    if mecanica == "canon":
        return _consejos_silla(nivel, res, estrellas)
    if mecanica == "tambor":
        return _consejos_marcha(nivel, res, estrellas)
    if nivel.get("cruzar"):
        return _consejos_cruzar(nivel, res, estrellas)
    return _consejos_equilibrio(acto, nivel, res, estrellas)


def _consejos_equilibrio(acto: dict, nivel: dict, res: dict, estrellas: int) -> list[str]:
    mecanica = acto["mecanica"]
    que = QUE.get(mecanica, "El vaso")
    duracion = _s(float(nivel["duracion_s"]))
    truco = TRUCO_VIENTO if nivel.get("viento") else TRUCO.get(mecanica, TRUCO["bandeja"])
    if estrellas == 0:
        motivo = res.get("motivo", "").lower()
        if "pies" in motivo:
            return ["Has movido los pies: colócalos bien antes de empezar y no los muevas; "
                    "si te desequilibras, compensa con el tronco.",
                    f"Aguanta los {duracion} s sin moverlos para conseguir 1 estrella."]
        if "apoyado" in motivo:
            return [f"Has bajado el pie antes de tiempo: aguanta {duracion} s con el pie levantado "
                    "para conseguir 1 estrella.",
                    "Levántalo solo un poco del suelo y fija la mirada en un punto delante de ti."]
        return [f"{que} se ha caído: aguanta los {duracion} s sin que se caiga para conseguir 1 estrella.",
                truco]
    dos, tres = nivel.get("estrellas_peligro", C.ESTRELLAS_PELIGRO)
    llego = f"{que} llegó al {_pct(res.get('peligro_max', 0.0))} de caerse"
    if estrellas == 1:
        objetivo = f"Para 2 estrellas, que no pase del {_pct(dos)}; para 3, del {_pct(tres)}."
    else:
        objetivo = f"Para 3 estrellas, que no pase del {_pct(tres)}."
    return [f"{llego}. {objetivo}", truco]


def _consejos_cruzar(nivel: dict, res: dict, estrellas: int) -> list[str]:
    tiempos = nivel["estrellas_s"]
    if estrellas == 0:
        if "tiempo" in res.get("motivo", "").lower():
            return [f"Llegaste al {_pct(res.get('avance', 0.0))} de la cuerda: el funambulista solo avanza "
                    "cuando está casi recto.",
                    f"Corrige pronto con la cadera y quédate quieto: cruza en {_s(tiempos[0])} s "
                    "para conseguir 1 estrella."]
        return ["El funambulista se ha caído: cruza la cuerda sin que se caiga para conseguir 1 estrella.",
                TRUCO["cuerda"]]
    siguiente = tiempos[estrellas]
    return [f"Has cruzado en {_s(res['tiempo'])} s. Para {estrellas + 1} estrellas, cruza en "
            f"{_s(siguiente)} s o menos.",
            "Cuanto menos se incline, menos se para: corrige antes de que aparezca la flecha naranja."]


def _consejos_silla(nivel: dict, res: dict, estrellas: int) -> list[str]:
    tiempos = nivel["estrellas_s"]
    objetivo = int(res.get("objetivo", nivel.get("repeticiones", C.SILLA_REPETICIONES)))
    lista: list[str] = []
    if estrellas == 0:
        lista.append(f"Hiciste {res.get('repeticiones', 0)} de {objetivo} levantadas: completa las "
                     f"{objetivo} en menos de {_s(tiempos[0])} s para conseguir 1 estrella.")
    else:
        lista.append(f"Has tardado {_s(res['tiempo'])} s. Para {estrellas + 1} estrellas, hazlas en "
                     f"{_s(tiempos[estrellas])} s o menos.")
    if res.get("incompletas"):
        lista.append(f"{res['incompletas']} levantadas no contaron: estira del todo las piernas al subir.")
    elif res.get("manos") and nivel.get("manos_falla"):
        lista.append("En este nivel no vale apoyar las manos: crúzalas sobre el pecho.")
    else:
        lista.append("Echa el tronco hacia delante al levantarte y no te pares arriba.")
    return lista


def _consejos_marcha(nivel: dict, res: dict, estrellas: int) -> list[str]:
    pasos_estrella = nivel["estrellas_pasos"]
    pasos = int(res.get("pasos", 0))
    necesarios = pasos_estrella[estrellas]
    if estrellas == 0:
        primera = f"Diste {pasos} pasos: necesitas {necesarios} para conseguir 1 estrella."
    else:
        primera = f"Diste {pasos} pasos. Para {estrellas + 1} estrellas, necesitas {necesarios}."
    if nivel.get("tempo_bpm"):
        segunda = "Sube la rodilla hasta la línea en cada paso y sigue el ritmo del tambor."
    else:
        segunda = "Sube la rodilla hasta la línea en cada paso y no te pares: un ritmo constante suma más."
    return [primera, segunda]


# ---------------------------------------------------------------------------
# Práctica
# ---------------------------------------------------------------------------


def objetivo_practica(prueba: str, res: dict) -> str:
    """Siguiente objetivo concreto (puntos SPPB o referencia clínica), o "" si ya está al máximo."""
    t = res.get("tiempo") or 0.0
    if prueba in ("pies_juntos", "semitandem"):
        if t < C.PRUEBA_EQUILIBRIO_S:
            return f"Aguanta {_s(C.PRUEBA_EQUILIBRIO_S)} s para sumar 1 punto en la evaluación (llevas {_s(t)} s)."
        return ""
    if prueba == "tandem":
        if t < C.SPPB_TANDEM_PARCIAL_S:
            return (f"Aguanta al menos {_s(C.SPPB_TANDEM_PARCIAL_S)} s para 1 punto y "
                    f"{_s(C.PRUEBA_EQUILIBRIO_S)} s para 2 (llevas {_s(t)} s).")
        if t < C.PRUEBA_EQUILIBRIO_S:
            return f"Aguanta {_s(C.PRUEBA_EQUILIBRIO_S)} s para conseguir los 2 puntos (llevas {_s(t)} s)."
        return ""
    if prueba == "silla":
        completas = res.get("repeticiones", 0) >= C.SILLA_REPETICIONES and res.get("tiempo") is not None
        if not completas:
            return (f"Completa las {C.SILLA_REPETICIONES} levantadas en menos de "
                    f"{_s(C.SILLA_TIEMPO_MAX_S)} s para puntuar en la evaluación.")
        for maximo, puntos in C.SPPB_SILLA_CORTES:
            if res["tiempo"] > maximo:
                continue
            if puntos == 4:
                return ""
            mejor = next(m for m, p in C.SPPB_SILLA_CORTES if p == puntos + 1)
            return f"Para {puntos + 1} puntos en la evaluación, hazlas en {_s(mejor)} s o menos."
        return ""
    if prueba == "una_pierna":
        if t < C.UNA_PIERNA_RIESGO_S:
            return f"Intenta llegar a {_s(C.UNA_PIERNA_RIESGO_S)} s: por debajo hay más riesgo de caídas."
        if t < C.UNA_PIERNA_EVAL_S:
            return f"Siguiente reto: aguantar {_s(C.UNA_PIERNA_EVAL_S)} s sobre una pierna."
        return ""
    if prueba == "marcha":
        ref = referencia_marcha(res.get("tiempo") or C.MARCHA_EVAL_S)
        if res.get("pasos_der", 0) < ref:
            return f"Llega a {ref} pasos con la rodilla derecha para una resistencia adecuada."
        return ""
    return ""


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------


def consejo_evaluacion(puntos: dict[str, int], maximos: dict[str, int]) -> str:
    """Qué prueba entrenar en el Modo Práctica (la que más puntos deja por el camino)."""
    perdidos = {p: maximos[p] - puntos.get(p, 0) for p in maximos}
    peor = max(perdidos, key=lambda p: perdidos[p])
    if perdidos[peor] == 0:
        return "¡Puntuación máxima! Sigue practicando en la Aventura para mantenerla."
    return (f"Lo que más puedes mejorar: {C.NOMBRES_PRUEBA[peor]} ({puntos.get(peor, 0)}/{maximos[peor]}). "
            "Entrénala en el Modo Práctica.")
