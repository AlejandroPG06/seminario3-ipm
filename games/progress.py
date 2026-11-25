"""Progreso del Modo Aventura: estrellas por nivel y desbloqueos (lógica pura).

El progreso es un dict {"acto": {"nivel": estrellas}} con claves str (JSON).
"""
from __future__ import annotations

import copy

import config as C


def estrellas_nivel(progreso: dict, acto: int, nivel: int) -> int:
    return int(progreso.get(str(acto), {}).get(str(nivel), 0))


def mejores_estrellas_acto(progreso: dict, acto: int) -> int:
    """Máximo de estrellas conseguido en cualquier nivel del acto."""
    return max((int(v) for v in progreso.get(str(acto), {}).values()), default=0)


def total_estrellas_acto(progreso: dict, acto: int) -> int:
    return sum(int(v) for v in progreso.get(str(acto), {}).values())


def acto_desbloqueado(progreso: dict, acto: int) -> bool:
    """El acto 1 siempre; los demás si el anterior tiene un nivel con suficientes estrellas."""
    if acto <= 1:
        return True
    return (acto_desbloqueado(progreso, acto - 1)
            and mejores_estrellas_acto(progreso, acto - 1) >= C.ESTRELLAS_DESBLOQUEO_ACTO)


def nivel_desbloqueado(progreso: dict, acto: int, nivel: int) -> bool:
    """El nivel 1 si el acto está abierto; los demás si el anterior tiene estrellas suficientes."""
    if not acto_desbloqueado(progreso, acto):
        return False
    return nivel <= 1 or estrellas_nivel(progreso, acto, nivel - 1) >= C.ESTRELLAS_DESBLOQUEO_NIVEL


def actos_desbloqueados(progreso: dict, n_actos: int = len(C.ACTOS)) -> int:
    return sum(1 for a in range(1, n_actos + 1) if acto_desbloqueado(progreso, a))


def registrar_resultado(progreso: dict, acto: int, nivel: int, estrellas: int) -> tuple[dict, bool]:
    """Devuelve (progreso nuevo, True si mejora el récord de estrellas). No modifica el original."""
    nuevo = copy.deepcopy(progreso)
    anterior = estrellas_nivel(progreso, acto, nivel)
    if estrellas > anterior:
        nuevo.setdefault(str(acto), {})[str(nivel)] = int(estrellas)
        return nuevo, True
    return nuevo, False
