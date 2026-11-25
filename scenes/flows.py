"""Controladores de flujo: encadenan escenas y guardan resultados.

FlujoEvaluacion: explicación de la SPPB → SPPB (pies juntos → semitándem →
    tándem → silla) y, si el jugador quiere, pruebas complementarias (una pierna → marcha).
FlujoAventura: mapa → nivel → resultados → mapa/repetir/siguiente.
FlujoPractica: elegir cualquier ejercicio → hacerlo con criterios clínicos → consejos.
"""
from __future__ import annotations

import config as C
from core.calibration import Calibracion
from games.achievements import estadisticas, nuevos_logros
from games.progress import nivel_desbloqueado, registrar_resultado
from games.protocol import COMPLEMENTARIAS, ProtocoloEvaluacion
from games.scoring import estrellas_equilibrio, estrellas_marcha, estrellas_silla
from scenes.base import Scene

TEXTO_VISTA = {
    "frente": "Ponte de FRENTE a la cámara, de pie, con todo el cuerpo a la vista.",
    "lado": "Siéntate de LADO a la cámara, con los brazos cruzados.",
}


def actualizar_logros(ctx, perfil: dict) -> list[dict]:
    """Comprueba logros nuevos, los añade al perfil y lo guarda."""
    stats = estadisticas(perfil, ctx.almacen.historial(perfil["nombre"]))
    nuevos = nuevos_logros(stats, perfil.get("logros", []))
    perfil.setdefault("logros", []).extend(l["id"] for l in nuevos)
    ctx.almacen.guardar_perfil(perfil)
    return nuevos


def _menu(ctx) -> Scene:
    from scenes.menu import EscenaMenu
    return EscenaMenu(ctx)


def _fmt(v) -> str:
    return "" if v is None else f"{v:.2f}"


def vista_de(prueba: str) -> str:
    return "lado" if prueba == "silla" else "frente"


def escena_ejercicio(ctx, prueba: str, cal: Calibracion, modo: str, al_terminar, al_cancelar,
                     nivel: dict | None = None, acto: dict | None = None) -> Scene:
    """Escena que corresponde a cada ejercicio (equilibrio, marcha o silla)."""
    from scenes.balance_scene import EscenaEquilibrio
    from scenes.chair_scene import EscenaSilla
    from scenes.march_scene import EscenaMarcha
    if prueba == "silla":
        return EscenaSilla(ctx, cal, modo, al_terminar, al_cancelar, nivel, acto)
    if prueba == "marcha":
        return EscenaMarcha(ctx, cal, modo, al_terminar, al_cancelar, nivel, acto)
    return EscenaEquilibrio(ctx, cal, prueba, modo, al_terminar, al_cancelar, nivel, acto)


def valor_resultado(prueba: str, res: dict):
    """Lo que se registra de cada prueba: segundos, o pasos de la rodilla derecha en la marcha."""
    if prueba == "marcha":
        return res.get("pasos_der")
    return res.get("tiempo")


def fila_resultado(prueba: str, res: dict) -> dict:
    """Columnas del historial con el resultado de un ejercicio."""
    if prueba == "marcha":
        return {"pasos_marcha": res.get("pasos_der")}
    if prueba == "silla":
        fila = {"manos_apoyo": int(bool(res.get("manos")))}
        if res.get("repeticiones") == C.SILLA_REPETICIONES:   # solo 5 levantadas es comparable con la SPPB
            fila["t_silla"] = _fmt(res.get("tiempo"))
        return fila
    return {f"t_{prueba}": _fmt(res.get("tiempo")),
            "balanceo_medio": f"{res.get('balanceo_medio', 0.0):.3f}"}


class FlujoEvaluacion:
    """Modo Evaluación: SPPB reducida (0-8) sin elementos de juego, más complementarias opcionales."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.protocolo = ProtocoloEvaluacion()
        self.calib_frente: Calibracion | None = None
        self._pregunta_hecha = False

    def iniciar(self) -> Scene:
        """Primero explica qué es la SPPB; desde ahí se empieza la primera prueba."""
        from scenes.info_scene import EscenaInfoSPPB
        return EscenaInfoSPPB(self.ctx, self._cancelar, empezar=self.empezar)

    def empezar(self) -> Scene:
        """Primera prueba de la SPPB (colocación de frente)."""
        return self._escena_para(self.protocolo.actual())

    def _cancelar(self) -> Scene:
        return _menu(self.ctx)

    def _escena_para(self, prueba: str | None) -> Scene:
        from scenes.calibration_scene import EscenaColocacion
        from scenes.results_scene import EscenaPregunta
        if prueba is None:
            return self._finalizar()
        if prueba in COMPLEMENTARIAS and not self._pregunta_hecha:
            return EscenaPregunta(
                self.ctx, "Pruebas complementarias",
                ["La SPPB ha terminado. ¿Quieres hacer dos pruebas más?",
                 f"Equilibrio sobre una pierna ({C.UNA_PIERNA_EVAL_S:.0f} s) y marcha en el sitio ({C.MARCHA_EVAL_S:.0f} s).",
                 "No cambian tu puntuación SPPB.", C.AVISO_SEGURIDAD],
                [("Sí, hacerlas", self._aceptar_complementarias),
                 ("No, ver resultados", self._omitir_complementarias)])
        fin, cancelar = self.terminar_prueba, self._cancelar
        if prueba == "silla":
            return EscenaColocacion(
                self.ctx, "lado", "Prueba de la silla", TEXTO_VISTA["lado"],
                lambda cal: escena_ejercicio(self.ctx, "silla", cal, "evaluacion", fin, cancelar), cancelar)

        def con_calibracion(cal: Calibracion) -> Scene:
            self.calib_frente = cal
            return escena_ejercicio(self.ctx, prueba, cal, "evaluacion", fin, cancelar)

        if self.calib_frente is None:
            return EscenaColocacion(self.ctx, "frente", "Modo Evaluación", TEXTO_VISTA["frente"],
                                    con_calibracion, cancelar)
        return con_calibracion(self.calib_frente)

    def _aceptar_complementarias(self) -> Scene:
        self._pregunta_hecha = True
        return self._escena_para(self.protocolo.actual())

    def _omitir_complementarias(self) -> Scene:
        self.protocolo.omitir_complementarias()
        return self._finalizar()

    def terminar_prueba(self, resultado: dict) -> Scene:
        """Registra el resultado de la prueba actual y pasa a la siguiente."""
        prueba = resultado.get("prueba")
        if prueba == "silla":
            self.protocolo.manos_silla = bool(resultado.get("manos"))
            self.calib_frente = None        # tras la silla (de lado) hay que volver a colocarse de frente
        return self._escena_para(self.protocolo.registrar(valor_resultado(prueba, resultado)))

    def _finalizar(self) -> Scene:
        from scenes.results_scene import EscenaResultadosEvaluacion
        res = self.protocolo.resultado()
        t, p, comp = res["tiempos"], res["puntos"], res["complementarias"]
        self.ctx.almacen.registrar_sesion({
            "jugador": self.ctx.jugador, "modo": "evaluacion",
            "t_pies_juntos": _fmt(t.get("pies_juntos")), "t_semitandem": _fmt(t.get("semitandem")),
            "t_tandem": _fmt(t.get("tandem")), "t_silla": _fmt(t.get("silla")),
            "t_una_pierna": _fmt(comp.get("una_pierna", {}).get("valor")),
            "pasos_marcha": comp.get("marcha", {}).get("valor", ""),
            "sppb_pies_juntos": p["pies_juntos"], "sppb_semitandem": p["semitandem"],
            "sppb_tandem": p["tandem"], "sppb_silla": p["silla"], "sppb_total": res["total"],
            "manos_apoyo": int(res["manos_silla"]),
        })
        nuevos = actualizar_logros(self.ctx, self.ctx.perfil())
        return EscenaResultadosEvaluacion(self.ctx, res, nuevos)


class FlujoAventura:
    """Modo Aventura: actos y niveles con puntos y estrellas."""

    def __init__(self, ctx):
        self.ctx = ctx

    def mapa(self, acto_id: int | None = None) -> Scene:
        from scenes.adventure_map import EscenaMapa
        return EscenaMapa(self.ctx, self, acto_id)

    def jugar(self, acto_id: int, n_nivel: int) -> Scene:
        """Escena de colocación que lleva al nivel indicado (1-based)."""
        from scenes.calibration_scene import EscenaColocacion
        acto = C.ACTOS[acto_id - 1]
        nivel = acto["niveles"][n_nivel - 1]
        fin = lambda r: self.terminar(acto_id, n_nivel, r)   # noqa: E731
        volver = lambda: self.mapa(acto_id)                  # noqa: E731
        vista = acto["vista"]
        return EscenaColocacion(
            self.ctx, vista, f"{acto['nombre']} · Nivel {n_nivel}", TEXTO_VISTA[vista],
            lambda cal: escena_ejercicio(self.ctx, acto["prueba"], cal, "aventura", fin, volver, nivel, acto),
            volver)

    def hay_siguiente(self, acto_id: int, n_nivel: int) -> tuple[int, int] | None:
        """(acto, nivel) siguiente si existe y está desbloqueado."""
        progreso = self.ctx.perfil().get("progreso", {})
        acto = C.ACTOS[acto_id - 1]
        if n_nivel < len(acto["niveles"]):
            cand = (acto_id, n_nivel + 1)
        elif acto_id < len(C.ACTOS):
            cand = (acto_id + 1, 1)
        else:
            return None
        return cand if nivel_desbloqueado(progreso, *cand) else None

    def calcular_estrellas(self, acto: dict, nivel: dict, res: dict) -> int:
        if acto["mecanica"] == "canon":
            if nivel.get("ritmo_s"):          # «Al ritmo del cañón»: estrellas por levantadas fuera de ritmo
                if not res.get("completado"):
                    return 0
                return sum(1 for maximo in nivel["estrellas_fallos"] if res.get("fuera_ritmo", 0) <= maximo)
            return estrellas_silla(res.get("tiempo"), tuple(nivel["estrellas_s"]))
        if acto["mecanica"] == "tambor":
            return estrellas_marcha(res["pasos"], tuple(nivel["estrellas_pasos"]))
        if nivel.get("cruzar"):            # «Cruza la cuerda»: cuanto antes llegues, más estrellas
            return estrellas_silla(res["tiempo"] if res.get("completado") else None, tuple(nivel["estrellas_s"]))
        umbrales = tuple(nivel.get("estrellas_peligro", C.ESTRELLAS_PELIGRO))
        return estrellas_equilibrio(res["tiempo"], float(nivel["duracion_s"]), res.get("peligro_max", 0.0), umbrales)

    def terminar(self, acto_id: int, n_nivel: int, res: dict) -> Scene:
        """Calcula estrellas, actualiza el perfil e historial y muestra los resultados."""
        from scenes.results_scene import EscenaResultadosNivel
        acto = C.ACTOS[acto_id - 1]
        nivel = acto["niveles"][n_nivel - 1]
        estrellas = self.calcular_estrellas(acto, nivel, res)
        perfil = self.ctx.perfil()
        perfil["progreso"], mejora = registrar_resultado(perfil.get("progreso", {}), acto_id, n_nivel, estrellas)
        clave = f"{acto_id}-{n_nivel}"
        record = res["puntos"] > perfil["puntos_mejores"].get(clave, 0)
        if record:
            perfil["puntos_mejores"][clave] = res["puntos"]
        est = perfil["estadisticas"]
        est["racha_max_s"] = max(float(est.get("racha_max_s", 0)), float(res.get("racha_max_s", 0)))
        est["burbujas_total"] = int(est.get("burbujas_total", 0)) + int(res.get("burbujas", 0))
        est["compas_max"] = max(int(est.get("compas_max", 0)), int(res.get("al_compas", 0)))
        if res.get("viento") and estrellas > 0:
            est["viento_superado"] = 1
        fila = {"jugador": self.ctx.jugador, "modo": "aventura", "prueba": acto["prueba"],
                "acto": acto_id, "nivel": n_nivel, "puntos": res["puntos"], "estrellas": estrellas,
                "racha_max_s": f"{res.get('racha_max_s', 0):.1f}"}
        if acto["mecanica"] != "tambor" and not nivel.get("ritmo_s"):   # no comparables con la Evaluación
            fila.update(fila_resultado(acto["prueba"], res))
        self.ctx.almacen.registrar_sesion(fila)
        nuevos = actualizar_logros(self.ctx, perfil)
        return EscenaResultadosNivel(self.ctx, self, acto_id, n_nivel, res, estrellas, nuevos, record or mejora)


class FlujoPractica:
    """Modo Práctica: cualquier ejercicio, sin candados, con criterios clínicos y consejos."""

    def __init__(self, ctx):
        self.ctx = ctx

    def menu(self) -> Scene:
        from scenes.practice_scene import EscenaPractica
        return EscenaPractica(self.ctx, self)

    def jugar(self, prueba: str) -> Scene:
        from scenes.calibration_scene import EscenaColocacion
        vista = vista_de(prueba)
        fin = lambda r: self.terminar(prueba, r)   # noqa: E731
        return EscenaColocacion(
            self.ctx, vista, f"Práctica · {C.NOMBRES_PRUEBA[prueba]}", TEXTO_VISTA[vista],
            lambda cal: escena_ejercicio(self.ctx, prueba, cal, "practica", fin, self.menu), self.menu)

    def terminar(self, prueba: str, res: dict) -> Scene:
        from scenes.practice_scene import EscenaResultadoPractica
        fila = {"jugador": self.ctx.jugador, "modo": "practica", "prueba": prueba}
        fila.update(fila_resultado(prueba, res))
        self.ctx.almacen.registrar_sesion(fila)
        nuevos = actualizar_logros(self.ctx, self.ctx.perfil())
        return EscenaResultadoPractica(self.ctx, self, prueba, res, nuevos)
