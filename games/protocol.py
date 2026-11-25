"""Secuencia del Modo Evaluación (lógica pura).

1. SPPB reducida (0-8): pies juntos → semitándem → tándem → silla. Se hacen
   siempre las tres posturas y cada una puntúa por separado. Con
   config.EVALUACION_SALTAR_TRAS_FALLO = True se sigue el protocolo original:
   si no se completa una postura, las siguientes se omiten (0 puntos), pero la
   silla se hace igualmente.
2. Pruebas complementarias (opcionales, DESPUÉS de la SPPB para no alterarla
   con el cansancio): sobre una pierna y marcha en el sitio. Tienen su propio
   resultado y no suman a la SPPB.
"""
from __future__ import annotations

import config as C
from games.scoring import (interpretar_marcha, interpretar_sppb, interpretar_una_pierna,
                           sppb_equilibrio, sppb_silla)

PRUEBAS = list(C.PRUEBAS_SPPB)
EQUILIBRIO = ["pies_juntos", "semitandem", "tandem"]
COMPLEMENTARIAS = list(C.PRUEBAS_COMPLEMENTARIAS)


class ProtocoloEvaluacion:
    """Lleva qué prueba toca, los resultados registrados y las omitidas."""

    def __init__(self, complementarias: bool = True):
        self.secuencia = PRUEBAS + (COMPLEMENTARIAS if complementarias else [])
        self.tiempos: dict[str, float | None] = {}        # SPPB: segundos
        self.complementarias: dict[str, float | None] = {}  # una_pierna: s, marcha: pasos dcha.
        self.omitidas: list[str] = []
        self.manos_silla = False
        self._indice = 0

    def actual(self) -> str | None:
        """Prueba que toca ahora, o None si se ha terminado."""
        return self.secuencia[self._indice] if self._indice < len(self.secuencia) else None

    @property
    def terminado(self) -> bool:
        return self.actual() is None

    @property
    def sppb_terminada(self) -> bool:
        """True cuando ya solo quedan (o no quedan) pruebas complementarias."""
        return self.actual() is None or self.actual() in COMPLEMENTARIAS

    def registrar(self, valor: float | None) -> str | None:
        """Registra el resultado de la prueba actual (None = no pudo) y devuelve la siguiente.

        Para la SPPB y la pierna, valor = segundos; para la marcha, pasos de la rodilla derecha.
        """
        prueba = self.actual()
        if prueba is None:
            return None
        if prueba in COMPLEMENTARIAS:
            self.complementarias[prueba] = valor
        else:
            self.tiempos[prueba] = valor
        self._indice += 1
        if (C.EVALUACION_SALTAR_TRAS_FALLO and prueba in EQUILIBRIO
                and (valor or 0.0) < C.PRUEBA_EQUILIBRIO_S):
            while self.actual() in EQUILIBRIO:
                self.omitidas.append(self.actual())
                self.tiempos[self.actual()] = None
                self._indice += 1
        return self.actual()

    def omitir_complementarias(self) -> None:
        """Salta las pruebas complementarias que queden."""
        while self.actual() in COMPLEMENTARIAS:
            self.omitidas.append(self.actual())
            self._indice += 1

    def resultado(self) -> dict:
        """Puntos SPPB por prueba, total 0-8, interpretación y complementarias."""
        puntos = {p: sppb_equilibrio(p, self.tiempos.get(p)) for p in EQUILIBRIO}
        puntos["silla"] = sppb_silla(self.tiempos.get("silla"))
        total = sum(puntos.values())
        comp = {}
        if "una_pierna" in self.complementarias:
            t = self.complementarias["una_pierna"]
            comp["una_pierna"] = {"valor": t, "texto": interpretar_una_pierna(t)}
        if "marcha" in self.complementarias:
            n = self.complementarias["marcha"]
            comp["marcha"] = {"valor": n, "texto": interpretar_marcha(n)}
        return {
            "tiempos": dict(self.tiempos),
            "puntos": puntos,
            "total": total,
            "interpretacion": interpretar_sppb(total),
            "omitidas": list(self.omitidas),
            "manos_silla": self.manos_silla,
            "complementarias": comp,
        }
