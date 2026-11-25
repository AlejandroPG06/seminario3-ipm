"""Sprites: usa assets/<nombre>.png si existe; si no, dibuja una versión procedural.

Nombres de PNG reconocidos (con transparencia, cualquier tamaño):
  bandeja, vaso, objeto_0, objeto_1, objeto_2, funambulista, canon, hombre_bala,
  pelota, bailarina, tambor, estrella, estrella_vacia, candado, burbuja, boton, boton_inactivo,
  icono_ajustes, icono_info
Siluetas de pies (vistas desde arriba, negras con transparencia; el juego les pone el contorno):
  pies_juntos, pies_semitandem, pies_tandem
Para sustituir un gráfico basta con dejar el PNG en assets/ con ese nombre.
"""
from __future__ import annotations

import math
import os

import cv2
import numpy as np

import config as C
from ui.text import leer_imagen, pegar_rgba, texto

COLORES_OBJETOS = [(60, 60, 220), (220, 140, 40), (80, 200, 80), (40, 190, 240), (180, 80, 180)]


def rotar(puntos, angulo_deg: float, origen=(0, 0)) -> np.ndarray:
    """Rota puntos locales (en px) alrededor de (0,0) y los traslada a origen.

    Con el eje y hacia abajo, un ángulo positivo gira en sentido horario.
    """
    a = math.radians(angulo_deg)
    c, s = math.cos(a), math.sin(a)
    p = np.asarray(puntos, dtype=np.float32)
    x = p[:, 0] * c - p[:, 1] * s + origen[0]
    y = p[:, 0] * s + p[:, 1] * c + origen[1]
    return np.stack([x, y], axis=1)


def _poli(frame, pts, color, relleno=True, grosor=2) -> None:
    pts = np.round(pts).astype(np.int32).reshape(-1, 1, 2)
    if relleno:
        cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)
    else:
        cv2.polylines(frame, [pts], True, color, grosor, cv2.LINE_AA)


class Sprites:
    """Carga los PNG una vez al iniciar y ofrece funciones de dibujo con alternativa procedural."""

    def __init__(self, directorio: str | None = C.ASSETS_DIR):
        self._png: dict[str, np.ndarray] = {}
        if directorio and os.path.isdir(directorio):
            for f in os.listdir(directorio):
                if f.lower().endswith(".png") and f != "fondo.png":
                    img = leer_imagen(os.path.join(directorio, f), cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        if img.ndim == 2:
                            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
                        elif img.shape[2] == 3:
                            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                        self._png[os.path.splitext(f)[0]] = img
        self._siluetas: dict[tuple, np.ndarray] = {}

    def tiene(self, nombre: str) -> bool:
        return nombre in self._png

    def aspecto(self, nombre: str) -> float:
        """Ancho / alto del PNG."""
        h, w = self._png[nombre].shape[:2]
        return w / h

    def silueta_png(self, frame, nombre: str, centro, alto_px: float, mitad: str | None = None,
                fantasma: bool = False, relleno=C.SILUETA_RELLENO, contorno=C.SILUETA_CONTORNO) -> None:
        """Dibuja la silueta de un PNG (su canal alfa) rellena y con contorno, escalada a alto_px.

        mitad: "izq"/"der" para usar solo media imagen (p. ej. un pie de pies_juntos).
        fantasma: solo el contorno y un relleno muy tenue (el pie que se levanta).
        """
        alto = max(8, int(alto_px))
        clave = (nombre, alto, mitad, fantasma, relleno, contorno)
        img = self._siluetas.get(clave)
        if img is None:
            img = self._crear_silueta(nombre, alto, mitad, fantasma, relleno, contorno)
            if len(self._siluetas) > 64:
                self._siluetas.clear()
            self._siluetas[clave] = img
        h, w = img.shape[:2]
        pegar_rgba(frame, img[:, :, :3], img[:, :, 3:4].astype(np.float32) / 255.0,
                   int(centro[0] - w / 2), int(centro[1] - h / 2))

    def _crear_silueta(self, nombre, alto, mitad, fantasma, relleno, contorno) -> np.ndarray:
        alfa = self._png[nombre][:, :, 3]
        if mitad is not None:     # corta por la columna más vacía cerca del centro (el hueco entre pies)
            w = alfa.shape[1]
            centro = alfa[:, int(w * 0.4):int(w * 0.6)].sum(axis=0)
            m = int(w * 0.4) + int(np.argmin(centro))
            alfa = alfa[:, :m] if mitad == "izq" else alfa[:, m:]
        g = max(2, int(round(alto * C.SILUETA_GROSOR)))      # px de contorno
        interior = max(4, alto - 2 * g)
        ancho = max(2, int(alfa.shape[1] * interior / alfa.shape[0]))
        a = cv2.resize(alfa, (ancho, interior), interpolation=cv2.INTER_AREA)
        a = cv2.copyMakeBorder(a, g, g, g, g, cv2.BORDER_CONSTANT, value=0)
        nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * g + 1, 2 * g + 1))
        borde = cv2.dilate(a, nucleo).astype(np.float32) / 255.0
        dentro = a.astype(np.float32) / 255.0
        if fantasma:
            dentro *= 0.25
        color = (np.array(relleno, np.float32) * dentro[..., None]
                 + np.array(contorno, np.float32) * (1.0 - dentro[..., None]))
        opacidad = borde if not fantasma else np.maximum(borde - a.astype(np.float32) / 255.0 * 0.8, 0)
        out = np.dstack([np.clip(color, 0, 255), opacidad * 255]).astype(np.uint8)
        return out

    def png(self, frame, nombre: str, centro, alto_px: float, angulo: float = 0.0) -> None:
        """Dibuja un PNG escalado a alto_px y rotado alrededor de su centro."""
        img = self._png[nombre]
        esc = max(alto_px, 2) / img.shape[0]
        w, h = max(1, int(img.shape[1] * esc)), max(1, int(img.shape[0] * esc))
        img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
        if abs(angulo) > 0.5:
            diag = int(math.hypot(w, h)) + 2
            M = cv2.getRotationMatrix2D((w / 2, h / 2), -angulo, 1.0)
            M[0, 2] += (diag - w) / 2
            M[1, 2] += (diag - h) / 2
            img = cv2.warpAffine(img, M, (diag, diag), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            w = h = diag
        alfa = img[:, :, 3:4].astype(np.float32) / 255.0
        pegar_rgba(frame, img[:, :, :3], alfa, int(centro[0] - w / 2), int(centro[1] - h / 2))

    # -- bandeja y objetos -----------------------------------------------------
    def bandeja(self, frame, centro, ancho: float, angulo: float) -> None:
        """Bandeja centrada en `centro`, inclinada `angulo` grados."""
        if self.tiene("bandeja"):
            self.png(frame, "bandeja", centro, ancho * 0.12, angulo)
            return
        m = ancho / 2
        pts = rotar([(-m, -6), (m, -6), (m * 0.92, 10), (-m * 0.92, 10)], angulo, centro)
        _poli(frame, pts, (170, 170, 185))
        _poli(frame, pts, (90, 90, 100), relleno=False, grosor=3)

    def objeto(self, frame, base, alto: float, angulo: float, indice: int = 0) -> None:
        """Objeto apoyado con su base en `base`: indice 0 = vaso, otros = cajas/pelotas."""
        nombre = "vaso" if indice == 0 else f"objeto_{(indice - 1) % 3}"
        centro = rotar([(0, -alto / 2)], angulo, base)[0]
        if self.tiene(nombre):
            self.png(frame, nombre, centro, alto, angulo)
            return
        a = alto
        if indice == 0:   # vaso: trapecio con agua
            pts = rotar([(-a * 0.3, -a), (a * 0.3, -a), (a * 0.2, 0), (-a * 0.2, 0)], angulo, base)
            _poli(frame, pts, (235, 220, 200))
            agua = rotar([(-a * 0.27, -a * 0.6), (a * 0.27, -a * 0.6), (a * 0.2, 0), (-a * 0.2, 0)], angulo, base)
            _poli(frame, agua, (230, 160, 60))
            _poli(frame, pts, (120, 100, 90), relleno=False, grosor=2)
        elif indice % 2 == 1:   # caja
            pts = rotar([(-a * 0.45, -a), (a * 0.45, -a), (a * 0.45, 0), (-a * 0.45, 0)], angulo, base)
            _poli(frame, pts, COLORES_OBJETOS[indice % len(COLORES_OBJETOS)])
            _poli(frame, pts, (30, 30, 30), relleno=False, grosor=2)
        else:   # pelota
            cv2.circle(frame, tuple(int(v) for v in centro), int(a / 2), COLORES_OBJETOS[indice % len(COLORES_OBJETOS)], -1, cv2.LINE_AA)
            cv2.circle(frame, tuple(int(v) for v in centro), int(a / 2), (30, 30, 30), 2, cv2.LINE_AA)

    # -- cuerda floja --------------------------------------------------------
    def cuerda(self, frame, x0: int, x1: int, y: int, amplitud: float, fase: float, postes: int = 200) -> None:
        """Cuerda que ondula con la amplitud dada (px); postes = altura de los postes (px)."""
        xs = np.linspace(x0, x1, 40)
        t = (xs - x0) / max(1, x1 - x0)
        ys = y + amplitud * np.sin(math.pi * t) * math.sin(fase)
        pts = np.stack([xs, ys], 1).astype(np.int32)
        cv2.polylines(frame, [pts], False, (60, 110, 150), 6, cv2.LINE_AA)
        for x in (x0, x1):
            cv2.line(frame, (int(x), y), (int(x), y + postes), (50, 50, 60), 10)

    def funambulista(self, frame, pies, alto: float, angulo: float) -> None:
        """Funambulista con pértiga, pivotando sobre los pies con el ángulo dado."""
        centro = rotar([(0, -alto / 2)], angulo, pies)[0]
        if self.tiene("funambulista"):
            self.png(frame, "funambulista", centro, alto, angulo)
            return
        h = alto
        cuello = rotar([(0, -h * 0.75)], angulo, pies)[0]
        cadera = rotar([(0, -h * 0.4)], angulo, pies)[0]
        cabeza = rotar([(0, -h * 0.87)], angulo, pies)[0]
        p = lambda v: tuple(int(round(c)) for c in v)  # noqa: E731
        cv2.line(frame, p(pies), p(cadera), (40, 40, 40), 6, cv2.LINE_AA)
        cv2.line(frame, p(cadera), p(cuello), (40, 40, 200), 10, cv2.LINE_AA)
        cv2.circle(frame, p(cabeza), int(h * 0.09), (150, 190, 230), -1, cv2.LINE_AA)
        pertiga = rotar([(-h * 0.8, -h * 0.62 + h * 0.08), (0, -h * 0.62), (h * 0.8, -h * 0.62 + h * 0.08)], angulo, pies)
        cv2.polylines(frame, [pertiga.astype(np.int32)], False, (40, 90, 140), 5, cv2.LINE_AA)
        for extremo in (pertiga[0], pertiga[2]):
            cv2.circle(frame, p(extremo), 8, C.DORADO, -1, cv2.LINE_AA)

    # -- pelota y bailarina (acto 3) --------------------------------------------
    def pelota(self, frame, centro, radio: float, giro: float) -> None:
        """Pelota de circo con gajos que giran `giro` grados."""
        if self.tiene("pelota"):
            self.png(frame, "pelota", centro, radio * 2, giro)
            return
        c, r = (int(centro[0]), int(centro[1])), int(radio)
        colores = [(60, 60, 220), (240, 240, 240), (220, 140, 40), (40, 200, 250)]
        for k in range(8):
            ini = giro + k * 45
            cv2.ellipse(frame, c, (r, r), 0, ini, ini + 45, colores[k % 4], -1, cv2.LINE_AA)
        cv2.circle(frame, c, r, (30, 30, 30), 3, cv2.LINE_AA)
        cv2.circle(frame, (c[0] - r // 3, c[1] - r // 3), max(3, r // 6), (255, 255, 255), -1, cv2.LINE_AA)

    def bailarina(self, frame, pies, alto: float, angulo: float) -> None:
        """Bailarina sobre una pierna con tutú, pivotando sobre el pie."""
        centro = rotar([(0, -alto / 2)], angulo, pies)[0]
        if self.tiene("bailarina"):
            self.png(frame, "bailarina", centro, alto, angulo)
            return
        h = alto
        p = lambda v: tuple(int(round(c)) for c in v)  # noqa: E731
        cadera = rotar([(0, -h * 0.45)], angulo, pies)[0]
        cuello = rotar([(0, -h * 0.78)], angulo, pies)[0]
        cabeza = rotar([(0, -h * 0.88)], angulo, pies)[0]
        rodilla = rotar([(h * 0.18, -h * 0.32)], angulo, pies)[0]     # pierna levantada
        pie_alto = rotar([(h * 0.05, -h * 0.25)], angulo, pies)[0]
        cv2.line(frame, p(pies), p(cadera), (180, 160, 240), 5, cv2.LINE_AA)
        cv2.line(frame, p(cadera), p(rodilla), (180, 160, 240), 5, cv2.LINE_AA)
        cv2.line(frame, p(rodilla), p(pie_alto), (180, 160, 240), 5, cv2.LINE_AA)
        tutu = rotar([(-h * 0.22, -h * 0.42), (h * 0.22, -h * 0.42), (0, -h * 0.55)], angulo, pies)
        _poli(frame, tutu, (200, 120, 255))
        cv2.line(frame, p(cadera), p(cuello), (200, 120, 255), 9, cv2.LINE_AA)
        brazos = rotar([(-h * 0.25, -h * 0.98), (0, -h * 0.74), (h * 0.25, -h * 0.98)], angulo, pies)
        cv2.polylines(frame, [brazos.astype(np.int32)], False, (150, 190, 230), 4, cv2.LINE_AA)
        cv2.circle(frame, p(cabeza), int(h * 0.07), (150, 190, 230), -1, cv2.LINE_AA)

    # -- tambor (acto 4) ---------------------------------------------------------
    def tambor(self, frame, centro, radio: float, golpe: float = 0.0) -> None:
        """Tambor visto de frente; `golpe` (0-1) lo ilumina al sonar."""
        if self.tiene("tambor"):
            self.png(frame, "tambor", centro, radio * 2 * (1 + 0.1 * golpe))
            return
        x, y, r = int(centro[0]), int(centro[1]), int(radio * (1 + 0.1 * golpe))
        cuerpo = (40, 40, 200) if golpe < 0.5 else (80, 80, 255)
        cv2.rectangle(frame, (x - r, y - r // 3), (x + r, y + r // 2), cuerpo, -1)
        for k in range(-r, r, max(8, r // 4)):
            cv2.line(frame, (x + k, y - r // 3), (x + k + r // 4, y + r // 2), C.DORADO, 2, cv2.LINE_AA)
        cv2.ellipse(frame, (x, y + r // 2), (r, r // 4), 0, 0, 180, (30, 30, 120), 3, cv2.LINE_AA)
        cv2.ellipse(frame, (x, y - r // 3), (r, r // 4), 0, 0, 360, (235, 235, 245), -1, cv2.LINE_AA)
        cv2.ellipse(frame, (x, y - r // 3), (r, r // 4), 0, 0, 360, (90, 90, 90), 2, cv2.LINE_AA)
        if golpe > 0:
            cv2.ellipse(frame, (x, y - r // 3), (int(r * (1 + golpe * 0.5)), int(r // 4 * (1 + golpe))),
                        0, 0, 360, C.AMARILLO, 3, cv2.LINE_AA)

    # -- cañón ---------------------------------------------------------------
    def canon(self, frame, base, tam: float, carga: float, angulo: float = -35.0) -> None:
        """Cañón con barra de carga (0-1)."""
        if self.tiene("canon"):
            self.png(frame, "canon", base, tam, angulo)
        else:
            L, R = tam, tam * 0.22
            tubo = rotar([(0, -R), (L, -R * 0.8), (L, R * 0.8), (0, R)], angulo, base)
            _poli(frame, tubo, (50, 50, 60))
            _poli(frame, tubo, (20, 20, 20), relleno=False, grosor=3)
            cv2.circle(frame, (int(base[0]), int(base[1] + R)), int(R * 1.1), (40, 80, 130), -1, cv2.LINE_AA)
            cv2.circle(frame, (int(base[0]), int(base[1] + R)), int(R * 1.1), (20, 20, 20), 3, cv2.LINE_AA)
        x, y = int(base[0] - tam * 0.4), int(base[1] + tam * 0.5)
        w, h = int(tam * 1.2), 18
        cv2.rectangle(frame, (x, y), (x + w, y + h), (40, 40, 40), -1)
        cv2.rectangle(frame, (x, y), (x + int(w * min(1, carga)), y + h), C.NARANJA, -1)
        cv2.rectangle(frame, (x, y), (x + w, y + h), C.BLANCO, 2)

    def hombre_bala(self, frame, centro, tam: float, angulo: float) -> None:
        if self.tiene("hombre_bala"):
            self.png(frame, "hombre_bala", centro, tam, angulo)
            return
        cuerpo = rotar([(-tam / 2, -tam * 0.15), (tam / 2, -tam * 0.15), (tam / 2, tam * 0.15), (-tam / 2, tam * 0.15)], angulo, centro)
        _poli(frame, cuerpo, (40, 40, 200))
        cabeza = rotar([(tam * 0.6, 0)], angulo, centro)[0]
        cv2.circle(frame, (int(cabeza[0]), int(cabeza[1])), int(tam * 0.17), (150, 190, 230), -1, cv2.LINE_AA)
        cv2.circle(frame, (int(cabeza[0]), int(cabeza[1])), int(tam * 0.19), C.BLANCO, 3, cv2.LINE_AA)

    # -- iconos --------------------------------------------------------------
    def icono(self, frame, nombre: str, centro, tam: float) -> None:
        """Icono de botón: «ajustes» (engranaje) o «info» (interrogación). PNG: icono_<nombre>."""
        if self.tiene(f"icono_{nombre}"):
            self.png(frame, f"icono_{nombre}", centro, tam)
            return
        cx, cy = centro
        r = tam / 2
        if nombre == "ajustes":
            pts = []
            dientes = 8
            for k in range(dientes * 4):
                a = 2 * math.pi * k / (dientes * 4)
                radio = r if (k % 4) in (0, 1) else r * 0.74
                pts.append((cx + radio * math.cos(a), cy + radio * math.sin(a)))
            _poli(frame, np.array(pts), C.CREMA_CARPA)
            cv2.circle(frame, (int(cx), int(cy)), max(2, int(r * 0.32)), C.ROJO_CARPA, -1, cv2.LINE_AA)
        elif nombre == "info":
            cv2.circle(frame, (int(cx), int(cy)), int(r), C.CREMA_CARPA, -1, cv2.LINE_AA)
            texto(frame, "?", (int(cx), int(cy - r * 0.8)), int(tam * 0.8), C.ROJO_CARPA, "centro", sombra=False)

    def estrella(self, frame, centro, radio: float, llena: bool = True) -> None:
        nombre = "estrella" if llena else "estrella_vacia"
        if self.tiene(nombre):
            self.png(frame, nombre, centro, radio * 2)
            return
        pts = []
        for i in range(10):
            r = radio if i % 2 == 0 else radio * 0.45
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((centro[0] + r * math.cos(a), centro[1] + r * math.sin(a)))
        pts = np.array(pts)
        if llena:
            _poli(frame, pts, C.DORADO)
            _poli(frame, pts, (20, 120, 160), relleno=False, grosor=2)
        else:
            _poli(frame, pts, (90, 90, 90))
            _poli(frame, pts, (160, 160, 160), relleno=False, grosor=2)

    def candado(self, frame, centro, tam: float) -> None:
        if self.tiene("candado"):
            self.png(frame, "candado", centro, tam)
            return
        x, y = int(centro[0]), int(centro[1])
        s = int(tam / 2)
        cv2.ellipse(frame, (x, y - s // 3), (s // 2, s // 2), 0, 180, 360, (200, 200, 200), max(3, s // 6), cv2.LINE_AA)
        cv2.rectangle(frame, (x - s * 2 // 3, y - s // 3), (x + s * 2 // 3, y + s * 2 // 3), (60, 160, 200), -1)
        cv2.circle(frame, (x, y + s // 6), max(2, s // 6), (30, 30, 30), -1)

    def burbuja(self, frame, centro, radio: float) -> None:
        if self.tiene("burbuja"):
            self.png(frame, "burbuja", centro, radio * 2)
            return
        c = (int(centro[0]), int(centro[1]))
        r = int(radio)
        capa = frame.copy()
        cv2.circle(capa, c, r, (250, 220, 180), -1, cv2.LINE_AA)
        cv2.addWeighted(capa, 0.35, frame, 0.65, 0, frame)
        cv2.circle(frame, c, r, (255, 240, 210), 3, cv2.LINE_AA)
        cv2.circle(frame, (c[0] - r // 3, c[1] - r // 3), max(2, r // 5), C.BLANCO, -1, cv2.LINE_AA)

    def boton(self, frame, rect, activo: bool, resaltado: bool) -> None:
        x, y, w, h = rect
        nombre = "boton" if activo else "boton_inactivo"
        if self.tiene(nombre):
            self.png(frame, nombre, (x + w / 2, y + h / 2), h)
        else:
            color = C.ROJO_CARPA if activo else (90, 90, 90)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(frame, (x + 4, y + 4), (x + w - 4, y + h - 4), C.CREMA_CARPA if activo else GRIS_CLARO, 1)
        borde = C.DORADO if resaltado else C.BLANCO
        cv2.rectangle(frame, (x, y), (x + w, y + h), borde, 5 if resaltado else 2)

    # -- silueta guía --------------------------------------------------------
    def silueta(self, frame, vista: str, color) -> None:
        """Silueta de colocación: de pie de frente o sentado de lado."""
        H, W = frame.shape[:2]
        capa = frame.copy()
        if vista == "lado":
            pts = _silueta_sentado(W, H)
        else:
            pts = _silueta_de_pie(W, H)
        for linea in pts["lineas"]:
            cv2.polylines(capa, [np.array(linea, np.int32)], False, color, int(H * 0.05), cv2.LINE_AA)
        cv2.circle(capa, pts["cabeza"], int(H * 0.055), color, -1, cv2.LINE_AA)
        cv2.addWeighted(capa, 0.35, frame, 0.65, 0, frame)


GRIS_CLARO = (180, 180, 180)


def _silueta_de_pie(W: int, H: int) -> dict:
    cx = W // 2
    y = lambda f: int(H * f)  # noqa: E731
    s = int(H * 0.09)
    return {
        "cabeza": (cx, y(0.15)),
        "lineas": [
            [(cx, y(0.21)), (cx, y(0.50))],                          # tronco
            [(cx - s, y(0.25)), (cx + s, y(0.25))],                  # hombros
            [(cx - s, y(0.25)), (cx - s - s // 3, y(0.50))],         # brazo izq.
            [(cx + s, y(0.25)), (cx + s + s // 3, y(0.50))],         # brazo dcho.
            [(cx - s // 2, y(0.50)), (cx + s // 2, y(0.50))],        # cadera
            [(cx - s // 2, y(0.50)), (cx - s // 4, y(0.88))],        # pierna izq.
            [(cx + s // 2, y(0.50)), (cx + s // 4, y(0.88))],        # pierna dcha.
        ],
    }


def _silueta_sentado(W: int, H: int) -> dict:
    cx = W // 2
    y = lambda f: int(H * f)  # noqa: E731
    u = int(H * 0.17)
    return {
        "cabeza": (cx, y(0.25)),
        "lineas": [
            [(cx, y(0.31)), (cx, y(0.58))],                  # tronco
            [(cx, y(0.58)), (cx + u, y(0.58))],              # muslo
            [(cx + u, y(0.58)), (cx + u, y(0.85))],          # pierna
            [(cx, y(0.38)), (cx + u // 2, y(0.42)), (cx, y(0.45))],   # brazos cruzados
        ],
    }
