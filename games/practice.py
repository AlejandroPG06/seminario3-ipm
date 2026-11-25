"""Modo Práctica: qué valdría el intento en la Evaluación y consejos (lógica pura)."""
from __future__ import annotations

import config as C
from games.scoring import (interpretar_marcha, interpretar_una_pierna, sppb_equilibrio,
                           sppb_silla)

MAXIMOS_SPPB = {"pies_juntos": 1, "semitandem": 1, "tandem": 2, "silla": 4}


def valor_en_evaluacion(prueba: str, res: dict) -> str:
    """Frase con lo que el intento valdría en el Modo Evaluación."""
    if prueba == "silla":
        tiempo = res.get("tiempo") if res.get("repeticiones", 0) >= C.SILLA_REPETICIONES else None
        return f"En la evaluación: {sppb_silla(tiempo)}/{MAXIMOS_SPPB['silla']} puntos SPPB"
    if prueba in MAXIMOS_SPPB:
        return f"En la evaluación: {sppb_equilibrio(prueba, res.get('tiempo'))}/{MAXIMOS_SPPB[prueba]} puntos SPPB"
    if prueba == "una_pierna":
        return "Prueba complementaria: " + interpretar_una_pierna(res.get("tiempo"))
    if prueba == "marcha":
        return "Prueba complementaria: " + interpretar_marcha(res.get("pasos_der"))
    return ""


def consejos(prueba: str, res: dict) -> list[str]:
    """Consejos breves según cómo ha ido el intento (máximo 3)."""
    lista: list[str] = []
    motivo = res.get("motivo", "")
    if prueba == "silla":
        if res.get("manos"):
            lista.append("No apoyes las manos en las rodillas: crúzalas sobre el pecho.")
        if res.get("incompletas"):
            lista.append("Estira del todo las piernas al levantarte para que cuente.")
        if res.get("tiempo") is not None and res["tiempo"] > 13.69:
            lista.append("Prueba a levantarte un poco más rápido: echa el tronco hacia delante.")
    elif prueba == "marcha":
        if res.get("pasos_der", 0) < C.MARCHA_REFERENCIA_PASOS * res.get("tiempo", 0) / C.MARCHA_REFERENCIA_S:
            lista.append("Sube las rodillas hasta la línea y mantén un ritmo constante.")
        lista.append("Si te cansas, baja el ritmo, pero no te pares.")
    else:
        if "pies" in motivo.lower():
            lista.append("No muevas los pies: si pierdes el equilibrio, compensa con el tronco.")
        if "apoyado" in motivo.lower():
            lista.append("Fija la mirada en un punto delante de ti para aguantar más.")
        signo = res.get("balanceo_signo", 0.0)
        if abs(signo) > C.MULTIPLICADORES_ESTABILIDAD[0][0]:
            lado = "derecha" if signo > 0 else "izquierda"
            lista.append(f"Tiendes a irte hacia tu {lado}: reparte el peso.")
        elif res.get("balanceo_medio", 0.0) > C.MULTIPLICADORES_ESTABILIDAD[1][0]:
            lista.append("Te balanceas bastante: contrae el abdomen y respira tranquilo.")
    from games.tips import objetivo_practica
    objetivo = objetivo_practica(prueba, res)
    if objetivo:
        lista.insert(0, objetivo)
    if not lista:
        lista.append("¡Muy bien! Repite para afianzarlo.")
    return lista[:3]
