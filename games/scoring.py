"""Puntuación SPPB, puntos con multiplicador de estabilidad, rachas y estrellas (lógica pura)."""
from __future__ import annotations

import config as C

# ---------------------------------------------------------------------------
# SPPB (Guralnik et al., 1994): solo equilibrio y silla → 0-8
# ---------------------------------------------------------------------------


def sppb_equilibrio(prueba: str, tiempo_s: float | None) -> int:
    """Puntos SPPB de una postura de equilibrio según el tiempo aguantado."""
    t = tiempo_s or 0.0
    completo = t >= C.PRUEBA_EQUILIBRIO_S
    if prueba == "tandem":
        if completo:
            return 2
        return 1 if t >= C.SPPB_TANDEM_PARCIAL_S else 0
    return 1 if completo else 0


def sppb_silla(tiempo_s: float | None) -> int:
    """Puntos SPPB de 5 levantadas. None = no pudo completarlas."""
    if tiempo_s is None:
        return 0
    t = round(tiempo_s, 2)          # el protocolo mide en centésimas
    for maximo, puntos in C.SPPB_SILLA_CORTES:
        if t <= maximo:
            return puntos
    return 0


def interpretar_sppb(total: int) -> str:
    """Texto orientativo para la puntuación 0-8 (no es un diagnóstico)."""
    for minimo, txt in C.SPPB_INTERPRETACION:
        if total >= minimo:
            return txt
    return C.SPPB_INTERPRETACION[-1][1]


def interpretar_una_pierna(tiempo_s: float | None) -> str:
    """Texto orientativo del equilibrio sobre una pierna (Vellas et al., 1997)."""
    t = tiempo_s or 0.0
    if t < C.UNA_PIERNA_RIESGO_S:
        return f"Menos de {C.UNA_PIERNA_RIESGO_S:.0f} s: riesgo de caídas aumentado"
    if t >= C.UNA_PIERNA_EVAL_S:
        return "Excelente equilibrio sobre una pierna"
    return "Equilibrio sobre una pierna adecuado"


def interpretar_marcha(pasos_der: float | None) -> str:
    """Texto orientativo de la marcha de 2 min (pasos de la rodilla derecha)."""
    n = int(pasos_der or 0)
    if n < C.MARCHA_REFERENCIA_PASOS:
        return f"Por debajo de {C.MARCHA_REFERENCIA_PASOS} pasos: resistencia baja"
    return "Resistencia adecuada"


# ---------------------------------------------------------------------------
# Puntos y rachas (equilibrio)
# ---------------------------------------------------------------------------


def multiplicador_estabilidad(balanceo_abs: float) -> tuple[float, str]:
    """(multiplicador, etiqueta) según el balanceo absoluto en aw."""
    for maximo, mult, etiqueta in C.MULTIPLICADORES_ESTABILIDAD:
        if balanceo_abs < maximo:
            return mult, etiqueta
    return C.MULTIPLICADORES_ESTABILIDAD[-1][1], C.MULTIPLICADORES_ESTABILIDAD[-1][2]


class MarcadorEquilibrio:
    """Acumula puntos por segundo × estabilidad × racha y estadísticas del balanceo."""

    def __init__(self):
        self.puntos = 0.0
        self.racha_s = 0.0
        self.racha_max_s = 0.0
        self.t = 0.0
        self._suma_balanceo = 0.0
        self._suma_signo = 0.0
        self.etiqueta = ""
        self.mult_estabilidad = 1.0

    @property
    def mult_racha(self) -> float:
        escalones = int(self.racha_s // C.RACHA_PASO_S)
        return min(C.RACHA_MULT_MAX, 1.0 + escalones * C.RACHA_INCREMENTO)

    @property
    def multiplicador(self) -> float:
        return self.mult_estabilidad * self.mult_racha

    @property
    def balanceo_medio(self) -> float:
        return self._suma_balanceo / self.t if self.t > 0 else 0.0

    @property
    def balanceo_medio_signo(self) -> float:
        """Media con signo (aw): positivo = el jugador se desplaza hacia su derecha (imagen en espejo)."""
        return self._suma_signo / self.t if self.t > 0 else 0.0

    def actualizar(self, dt: float, balanceo_abs: float, con_signo: float | None = None) -> list[str]:
        """Suma dt segundos; devuelve eventos: "pulso_acero" al entrar en ×2, "racha" al subir escalón."""
        eventos = []
        anterior_etiqueta = self.etiqueta
        anterior_escalon = int(self.racha_s // C.RACHA_PASO_S)
        self.t += dt
        self._suma_balanceo += balanceo_abs * dt
        self._suma_signo += (balanceo_abs if con_signo is None else con_signo) * dt
        self.mult_estabilidad, self.etiqueta = multiplicador_estabilidad(balanceo_abs)
        if balanceo_abs < C.RACHA_UMBRAL:
            self.racha_s += dt
        else:
            self.racha_s = 0.0
        self.racha_max_s = max(self.racha_max_s, self.racha_s)
        self.puntos += C.PUNTOS_POR_SEGUNDO * dt * self.multiplicador
        if self.etiqueta != anterior_etiqueta and self.mult_estabilidad > 1:
            eventos.append("pulso_acero")
        mult_anterior = 1.0 + anterior_escalon * C.RACHA_INCREMENTO
        if int(self.racha_s // C.RACHA_PASO_S) > anterior_escalon and mult_anterior < C.RACHA_MULT_MAX:
            eventos.append("racha")
        return eventos


# ---------------------------------------------------------------------------
# Estrellas
# ---------------------------------------------------------------------------


def estrellas_por_peligro(peligro_max: float, umbrales: tuple[float, float] = C.ESTRELLAS_PELIGRO) -> int:
    """Estrellas (1-3) que da completar el nivel con ese peligro máximo (0 = centro, 1 = caída)."""
    if peligro_max < umbrales[1]:
        return 3
    if peligro_max < umbrales[0]:
        return 2
    return 1


def estrellas_equilibrio(tiempo_s: float, objetivo_s: float, peligro_max: float,
                         umbrales: tuple[float, float] = C.ESTRELLAS_PELIGRO) -> int:
    """0 si no completa; si completa, 1-3 según lo cerca que estuvo de caerse."""
    if tiempo_s < objetivo_s:
        return 0
    return estrellas_por_peligro(peligro_max, umbrales)


def estrellas_silla(tiempo_s: float | None, umbrales_s: tuple[float, float, float]) -> int:
    """Estrellas según el tiempo total; umbrales = tiempo máx. para 1★, 2★ y 3★."""
    if tiempo_s is None:
        return 0
    estrellas = 0
    for i, maximo in enumerate(umbrales_s):
        if tiempo_s <= maximo:
            estrellas = i + 1
    return estrellas


def puntos_silla(repeticiones, tiempo_s: float | None, tiempo_ref_s: float) -> int:
    """Puntos por calidad de cada repetición + bonus de velocidad − penalización por manos."""
    puntos = 0
    for r in repeticiones:
        puntos += C.PUNTOS_SILLA_REPETICION.get(r.calidad, 0)
        if r.manos:
            puntos -= C.PUNTOS_SILLA_PENALIZACION_MANOS
    if tiempo_s is not None and tiempo_s < tiempo_ref_s:
        puntos += int((tiempo_ref_s - tiempo_s) * C.PUNTOS_SILLA_BONUS_POR_S)
    return max(0, puntos)


def estrellas_marcha(pasos: int, umbrales: tuple[int, int, int]) -> int:
    """Estrellas según los pasos dados; umbrales = pasos mínimos para 1★, 2★ y 3★."""
    return sum(1 for minimo in umbrales if pasos >= minimo)


def puntos_marcha(pasos: int, al_compas: int) -> int:
    """Puntos por paso más bonus por cada paso al compás."""
    return pasos * C.PUNTOS_PASO + al_compas * C.PUNTOS_COMPAS


def distancia_canon(tiempo_s: float | None) -> float:
    """Metros que vuela el hombre bala según el tiempo total."""
    if tiempo_s is None:
        return 0.0
    extra = max(0.0, tiempo_s - C.CANON_TIEMPO_REF_S)
    return max(5.0, C.CANON_DISTANCIA_MAX_M - extra * C.CANON_METROS_POR_S)
