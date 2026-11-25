"""Logros definidos como datos en config.LOGROS (lógica pura)."""
from __future__ import annotations

import operator

import config as C
from games.progress import actos_desbloqueados, mejores_estrellas_acto

_OPERADORES = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt, "==": operator.eq}


def _float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def estadisticas(perfil: dict, historial: list[dict]) -> dict:
    """Calcula las estadísticas que usan las condiciones de los logros."""
    sppb = [_float(f.get("sppb_total")) for f in historial if f.get("modo") == "evaluacion"]
    sppb = [v for v in sppb if v is not None]
    silla = [_float(f.get("t_silla")) for f in historial]
    silla = [v for v in silla if v is not None]
    pierna = [_float(f.get("t_una_pierna")) for f in historial]
    pierna = [v for v in pierna if v is not None]
    progreso = perfil.get("progreso", {})
    est = perfil.get("estadisticas", {})
    stats = {
        "sesiones": len(historial),
        "sppb_max": max(sppb, default=None),
        "silla_mejor_s": min(silla, default=None),
        "racha_max_s": float(est.get("racha_max_s", 0.0)),
        "actos_desbloqueados": actos_desbloqueados(progreso),
        "viento_superado": int(est.get("viento_superado", 0)),
        "burbujas_total": int(est.get("burbujas_total", 0)),
        "una_pierna_max_s": max(pierna, default=None),
        "compas_max": int(est.get("compas_max", 0)),
    }
    for acto in C.ACTOS:
        stats[f"estrellas_acto_{acto['id']}"] = mejores_estrellas_acto(progreso, acto["id"])
    return stats


def cumple(logro: dict, stats: dict) -> bool:
    """True si las estadísticas cumplen la condición del logro (las ausentes no cumplen)."""
    valor = stats.get(logro["clave"])
    if valor is None:
        return False
    return _OPERADORES[logro["op"]](valor, logro["valor"])


def nuevos_logros(stats: dict, ya_tenidos: list[str], logros: list[dict] = C.LOGROS) -> list[dict]:
    """Logros que se cumplen ahora y no se tenían."""
    return [l for l in logros if l["id"] not in ya_tenidos and cumple(l, stats)]
