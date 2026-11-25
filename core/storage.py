"""Persistencia en data/: perfiles (JSON) e historial de sesiones (CSV)."""
from __future__ import annotations

import copy
import csv
import json
import os
from datetime import datetime

import config as C

CAMPOS_HISTORIAL = [
    "fecha", "jugador", "modo", "prueba", "acto", "nivel",
    "t_pies_juntos", "t_semitandem", "t_tandem", "t_silla", "t_una_pierna", "pasos_marcha",
    "sppb_pies_juntos", "sppb_semitandem", "sppb_tandem", "sppb_silla", "sppb_total",
    "puntos", "estrellas", "balanceo_medio", "racha_max_s", "manos_apoyo",
]


def perfil_vacio(nombre: str) -> dict:
    """Perfil nuevo con progreso vacío."""
    return {
        "nombre": nombre,
        "creado": datetime.now().isoformat(timespec="seconds"),
        "ultima_partida": "",
        "progreso": {},             # {"acto": {"nivel": estrellas}}
        "puntos_mejores": {},       # {"acto-nivel": puntos}
        "logros": [],               # ids de config.LOGROS
        "estadisticas": {"burbujas_total": 0, "racha_max_s": 0.0, "viento_superado": 0, "compas_max": 0},
    }


class Almacen:
    """Lee y escribe perfiles e historial en un directorio (por defecto data/)."""

    def __init__(self, directorio: str = C.DATA_DIR):
        self.directorio = directorio
        os.makedirs(directorio, exist_ok=True)
        self.ruta_perfiles = os.path.join(directorio, C.PERFILES_ARCHIVO)
        self.ruta_historial = os.path.join(directorio, C.HISTORIAL_ARCHIVO)
        self.ruta_ajustes = os.path.join(directorio, C.AJUSTES_ARCHIVO)

    # -- ajustes -------------------------------------------------------------
    def cargar_ajustes(self):
        """Ajustes guardados (o los de por defecto si no hay archivo o está dañado)."""
        from core.settings import Ajustes
        try:
            with open(self.ruta_ajustes, encoding="utf-8") as f:
                return Ajustes.desde_dict(json.load(f))
        except (OSError, json.JSONDecodeError):
            return Ajustes()

    def guardar_ajustes(self, ajustes) -> None:
        tmp = self.ruta_ajustes + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ajustes.a_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.ruta_ajustes)

    # -- perfiles ----------------------------------------------------------
    def _leer_perfiles(self) -> dict:
        if not os.path.exists(self.ruta_perfiles):
            return {}
        try:
            with open(self.ruta_perfiles, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _escribir_perfiles(self, perfiles: dict) -> None:
        tmp = self.ruta_perfiles + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(perfiles, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.ruta_perfiles)

    def jugadores(self) -> list[str]:
        """Nombres de jugadores, del que jugó más recientemente al que menos."""
        perfiles = self._leer_perfiles()
        return sorted(perfiles, key=lambda n: perfiles[n].get("ultima_partida", ""), reverse=True)

    def perfil(self, nombre: str) -> dict:
        """Perfil del jugador (uno nuevo si no existe; no se guarda hasta guardar_perfil)."""
        base = perfil_vacio(nombre)
        guardado = self._leer_perfiles().get(nombre)
        if guardado:
            base.update(copy.deepcopy(guardado))
            base["estadisticas"] = {**perfil_vacio(nombre)["estadisticas"], **guardado.get("estadisticas", {})}
        return base

    def todos_los_perfiles(self) -> dict:
        return self._leer_perfiles()

    def guardar_perfil(self, perfil: dict) -> None:
        perfiles = self._leer_perfiles()
        perfil["ultima_partida"] = datetime.now().isoformat(timespec="seconds")
        perfiles[perfil["nombre"]] = perfil
        self._escribir_perfiles(perfiles)

    # -- historial -----------------------------------------------------------
    def _migrar_cabecera(self) -> None:
        """Si el CSV tiene columnas antiguas, lo reescribe con CAMPOS_HISTORIAL (sin perder filas)."""
        if not os.path.exists(self.ruta_historial):
            return
        with open(self.ruta_historial, newline="", encoding="utf-8") as f:
            lector = csv.DictReader(f)
            if lector.fieldnames == CAMPOS_HISTORIAL:
                return
            filas = list(lector)
        tmp = self.ruta_historial + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS_HISTORIAL, extrasaction="ignore")
            w.writeheader()
            for r in filas:
                w.writerow({k: r.get(k, "") or "" for k in CAMPOS_HISTORIAL})
        os.replace(tmp, self.ruta_historial)

    def registrar_sesion(self, fila: dict) -> None:
        """Añade una fila al CSV (crea la cabecera si el archivo es nuevo)."""
        fila = {"fecha": datetime.now().isoformat(timespec="seconds"), **fila}
        self._migrar_cabecera()
        nuevo = not os.path.exists(self.ruta_historial)
        with open(self.ruta_historial, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS_HISTORIAL, extrasaction="ignore")
            if nuevo:
                w.writeheader()
            w.writerow({k: ("" if fila.get(k) is None else fila.get(k)) for k in CAMPOS_HISTORIAL})

    def historial(self, jugador: str | None = None) -> list[dict]:
        """Filas del historial (opcionalmente de un jugador), en orden cronológico."""
        if not os.path.exists(self.ruta_historial):
            return []
        with open(self.ruta_historial, newline="", encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
        if jugador is not None:
            filas = [r for r in filas if r.get("jugador") == jugador]
        return filas
