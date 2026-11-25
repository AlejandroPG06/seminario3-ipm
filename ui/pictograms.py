"""Pictogramas de los ejercicios: pies vistos desde arriba y muñecos animados.

Sirven para explicar cada ejercicio de un vistazo, sin texto que leer desde
lejos. Los pies usan las siluetas assets/pies_<postura>.png (con contorno) y,
si faltan, un dibujo procedural. Si existe assets/pic_<prueba>.png se usa esa
imagen para todo el pictograma.
"""
from __future__ import annotations

import math

import cv2

import config as C
from ui.dwell_button import anillo
from ui.text import panel, texto

PIEL = (150, 190, 230)
TRAZO = (255, 255, 255)
ACENTO = C.AMARILLO


# ---------------------------------------------------------------------------
# Pies vistos desde arriba (la punta hacia arriba)
# ---------------------------------------------------------------------------


def _pie(frame, centro, largo: float, color=PIEL, discontinuo: bool = False) -> None:
    """Planta de un pie: elipse con cinco dedos en la parte de arriba."""
    cx, cy = centro
    ancho = largo * 0.38
    if discontinuo:
        for a in range(0, 360, 30):
            cv2.ellipse(frame, (int(cx), int(cy)), (int(ancho / 2), int(largo / 2)), 0, a, a + 15,
                        TRAZO, 2, cv2.LINE_AA)
        return
    cv2.ellipse(frame, (int(cx), int(cy)), (int(ancho / 2), int(largo / 2)), 0, 0, 360, color, -1, cv2.LINE_AA)
    cv2.ellipse(frame, (int(cx), int(cy)), (int(ancho / 2), int(largo / 2)), 0, 0, 360, (40, 40, 40), 2, cv2.LINE_AA)
    for k, (dx, r) in enumerate(((-0.30, 0.10), (-0.13, 0.085), (0.03, 0.08), (0.17, 0.07), (0.30, 0.06))):
        x = cx + dx * ancho * 1.5
        y = cy - largo * 0.5 - r * largo * 0.6 + abs(dx) * largo * 0.25
        cv2.circle(frame, (int(x), int(y)), max(2, int(r * largo * 0.6)), color, -1, cv2.LINE_AA)


# Alto de cada silueta respecto a la caja disponible (el tándem ocupa dos pies de largo)
ESCALA_SILUETA = {"pies_juntos": 0.72, "semitandem": 0.85, "tandem": 1.0, "una_pierna": 0.72}


def _pies_png(frame, centro, caja: float, prueba: str, t: float, sprites) -> bool:
    """Siluetas PNG de los pies (True si se han podido dibujar)."""
    if sprites is None:
        return False
    nombre = "pies_juntos" if prueba in ("pies_juntos", "una_pierna") else f"pies_{prueba}"
    if not sprites.tiene(nombre):
        return False
    alto = caja * ESCALA_SILUETA.get(prueba, 0.8)
    cx, cy = centro
    if prueba != "una_pierna":
        sprites.silueta_png(frame, nombre, centro, alto)
        return True
    # Un pie apoyado y el otro «fantasma» que sube y baja con una flecha
    medio = alto * sprites.aspecto(nombre) / 4          # cuarto del ancho: centro de cada pie
    sprites.silueta_png(frame, nombre, (cx - medio * 1.15, cy), alto, mitad="izq")
    sube = alto * 0.08 * (1 + math.sin(t * 4))
    sprites.silueta_png(frame, nombre, (cx + medio * 1.15, cy - sube), alto, mitad="der", fantasma=True)
    x = int(cx + medio * 1.15)
    cv2.arrowedLine(frame, (x, int(cy + alto * 0.2 - sube)), (x, int(cy - alto * 0.25 - sube)),
                    ACENTO, max(3, int(alto * 0.04)), cv2.LINE_AA, tipLength=0.35)
    return True


def dibujar_pies(frame, centro, largo: float, prueba: str, t: float = 0.0, sprites=None) -> None:
    """Posición de los pies de cada ejercicio de equilibrio (largo = largo de un pie, px)."""
    if _pies_png(frame, centro, largo * 2.15, prueba, t, sprites):
        return
    cx, cy = centro
    a = largo * 0.38           # ancho del pie
    if prueba == "pies_juntos":
        _pie(frame, (cx - a * 0.55, cy), largo)
        _pie(frame, (cx + a * 0.55, cy), largo)
    elif prueba == "semitandem":     # talón del pie adelantado a la altura del dedo gordo del otro
        _pie(frame, (cx - a * 0.55, cy + largo * 0.4), largo)
        _pie(frame, (cx + a * 0.55, cy - largo * 0.4), largo, ACENTO)
    elif prueba == "tandem":
        _pie(frame, (cx, cy + largo * 0.52), largo)
        _pie(frame, (cx, cy - largo * 0.52), largo, ACENTO)
    elif prueba == "una_pierna":
        _pie(frame, (cx - a * 0.6, cy), largo)
        _pie(frame, (cx + a * 0.6, cy), largo, discontinuo=True)
        y = int(cy - largo * 0.1 - 8 * math.sin(t * 4))
        cv2.arrowedLine(frame, (int(cx + a * 0.6), y + int(largo * 0.3)), (int(cx + a * 0.6), y - int(largo * 0.3)),
                        ACENTO, 5, cv2.LINE_AA, tipLength=0.35)


# ---------------------------------------------------------------------------
# Muñeco (de frente o de lado), con poses simples
# ---------------------------------------------------------------------------


def _muneco(frame, base, alto: float, articulaciones: dict, color=TRAZO) -> None:
    """Dibuja un muñeco a partir de articulaciones en unidades de altura (0 = pies, -1 = cabeza)."""
    def p(nombre):
        x, y = articulaciones[nombre]
        return int(base[0] + x * alto), int(base[1] + y * alto)
    g = max(3, int(alto * 0.045))
    for a, b in (("cuello", "cadera"), ("hombro_i", "hombro_d"), ("hombro_i", "codo_i"), ("codo_i", "mano_i"),
                 ("hombro_d", "codo_d"), ("codo_d", "mano_d"), ("cadera", "rodilla_i"), ("rodilla_i", "pie_i"),
                 ("cadera", "rodilla_d"), ("rodilla_d", "pie_d")):
        cv2.line(frame, p(a), p(b), color, g, cv2.LINE_AA)
    cv2.circle(frame, p("cabeza"), int(alto * 0.075), color, -1, cv2.LINE_AA)


def _de_pie(brazos_arriba: bool = False) -> dict:
    j = {"cabeza": (0, -0.92), "cuello": (0, -0.82), "hombro_i": (-0.12, -0.8), "hombro_d": (0.12, -0.8),
         "cadera": (0, -0.48), "rodilla_i": (-0.06, -0.25), "rodilla_d": (0.06, -0.25),
         "pie_i": (-0.06, 0), "pie_d": (0.06, 0)}
    if brazos_arriba:
        j.update({"codo_i": (-0.2, -0.95), "mano_i": (-0.22, -1.12), "codo_d": (0.2, -0.95), "mano_d": (0.22, -1.12)})
    else:
        j.update({"codo_i": (-0.16, -0.63), "mano_i": (-0.17, -0.47), "codo_d": (0.16, -0.63), "mano_d": (0.17, -0.47)})
    return j


def _rodilla_arriba(j: dict, lado: str, fraccion: float = 1.0) -> dict:
    """Levanta la rodilla de un lado (vista frontal: el muslo se acorta y el pie sube)."""
    j = dict(j)
    s = -1 if lado == "i" else 1
    j[f"rodilla_{lado}"] = (s * 0.08, -0.25 - 0.17 * fraccion)
    j[f"pie_{lado}"] = (s * 0.07, -0.22 * fraccion)
    return j


def _sentado_lado(fraccion_de_pie: float) -> dict:
    """Vista de lado: interpola entre sentado (0) y de pie (1), brazos cruzados."""
    f = fraccion_de_pie
    cadera = (-0.05 * (1 - f), -0.45 - 0.05 * f)
    rodilla = (0.2 * (1 - f) + 0.02 * f, -0.45 * (1 - f) - 0.25 * f + 0.0)
    cuello = (cadera[0] + 0.1 * (1 - f), cadera[1] - 0.34)
    return {"cabeza": (cuello[0] + 0.02, cuello[1] - 0.1), "cuello": cuello,
            "hombro_i": cuello, "hombro_d": cuello,
            "codo_i": (cuello[0] + 0.1, cuello[1] + 0.1), "mano_i": (cuello[0] - 0.02, cuello[1] + 0.14),
            "codo_d": (cuello[0] + 0.1, cuello[1] + 0.1), "mano_d": (cuello[0] - 0.02, cuello[1] + 0.14),
            "cadera": cadera, "rodilla_i": rodilla, "rodilla_d": rodilla,
            "pie_i": (0.2 * (1 - f) + 0.02 * f, 0), "pie_d": (0.2 * (1 - f) + 0.02 * f, 0)}


def _silla(frame, base, alto: float) -> None:
    x, y = base
    a = alto
    color = (60, 110, 160)
    g = max(3, int(a * 0.035))
    cv2.line(frame, (int(x - a * 0.12), int(y - a * 0.43)), (int(x + a * 0.12), int(y - a * 0.43)), color, g, cv2.LINE_AA)
    cv2.line(frame, (int(x - a * 0.12), int(y - a * 0.43)), (int(x - a * 0.12), int(y - a * 0.9)), color, g, cv2.LINE_AA)
    for dx in (-0.12, 0.12):
        cv2.line(frame, (int(x + dx * a), int(y - a * 0.43)), (int(x + dx * a), int(y)), color, g, cv2.LINE_AA)


def dibujar_figura(frame, base, alto: float, prueba: str, t: float = 0.0) -> None:
    """Muñeco del ejercicio con los pies en `base`. Se anima con t (s)."""
    if prueba == "una_pierna":
        _muneco(frame, base, alto, _rodilla_arriba(_de_pie(), "d"))
    elif prueba == "marcha":
        fase = (t % 1.0) / 1.0
        lado = "i" if fase < 0.5 else "d"
        subida = math.sin(math.pi * ((fase * 2) % 1.0))
        _muneco(frame, base, alto, _rodilla_arriba(_de_pie(), lado, subida))
        cv2.line(frame, (int(base[0] - alto * 0.25), int(base[1] - alto * 0.33)),
                 (int(base[0] + alto * 0.25), int(base[1] - alto * 0.33)), ACENTO, 3, cv2.LINE_AA)
    elif prueba == "silla":
        f = 0.5 - 0.5 * math.cos(2 * math.pi * (t % 2.0) / 2.0)
        _silla(frame, (base[0] - alto * 0.05, base[1]), alto)
        _muneco(frame, base, alto, _sentado_lado(f))
    elif prueba == "brazos_arriba":
        _muneco(frame, base, alto, _de_pie(brazos_arriba=True), ACENTO)
    else:
        _muneco(frame, base, alto, _de_pie())


def icono_pausa(frame, centro, tam: float) -> None:
    x, y = int(centro[0]), int(centro[1])
    w, h = int(tam * 0.22), int(tam * 0.7)
    for dx in (-int(tam * 0.22), int(tam * 0.22)):
        cv2.rectangle(frame, (x + dx - w // 2, y - h // 2), (x + dx + w // 2, y + h // 2), C.AMARILLO, -1)


# ---------------------------------------------------------------------------
# Composiciones para las escenas
# ---------------------------------------------------------------------------


def pictograma(frame, centro, tam: float, prueba: str, t: float = 0.0, sprites=None) -> None:
    """Pictograma compacto (pies o muñeco) de una prueba, dentro de un cuadrado de lado `tam`."""
    if sprites is not None and sprites.tiene(f"pic_{prueba}"):
        sprites.png(frame, f"pic_{prueba}", centro, tam)
        return
    if prueba in ("pies_juntos", "semitandem", "tandem"):
        dibujar_pies(frame, centro, tam * 0.42, prueba, t, sprites)
    else:
        dibujar_figura(frame, (centro[0], centro[1] + tam * 0.45), tam * 0.85, prueba, t)


def instrucciones(frame, prueba: str, encabezado: str, linea: str, t: float,
                  progreso_brazos: float, subtitulo: str = "", sprites=None) -> None:
    """Pantalla de instrucciones visual: muñeco + pies + una línea corta + gesto de empezar."""
    H, W = frame.shape[:2]
    panel(frame, W // 2 - 470, 18, W // 2 + 470, H - 18, alfa=0.55)
    texto(frame, encabezado, (W // 2, 30), C.TAM_TITULO - 6, C.DORADO, "centro")
    if subtitulo:
        texto(frame, subtitulo, (W // 2, 98), C.TAM_PEQUENO + 2, C.CREMA_CARPA, "centro")
    alto_fig = H * 0.42
    base_y = int(H * 0.66)
    if prueba in ("pies_juntos", "semitandem", "tandem", "una_pierna"):
        dibujar_figura(frame, (W // 2 - 230, base_y), alto_fig, "una_pierna" if prueba == "una_pierna" else "de_pie", t)
        if sprites is not None and sprites.tiene(f"pic_{prueba}"):
            sprites.png(frame, f"pic_{prueba}", (W // 2 + 110, base_y - alto_fig / 2), alto_fig)
        else:
            dibujar_pies(frame, (W // 2 + 110, base_y - alto_fig * 0.45), alto_fig * 0.42, prueba, t, sprites)
    else:
        pictograma(frame, (W // 2 - 60, base_y - alto_fig / 2), alto_fig, prueba, t, sprites)
    # Gesto para empezar: muñeco con brazos arriba y anillo de progreso
    cx, cy = W // 2 + 360, int(H * 0.40)
    dibujar_figura(frame, (cx, cy + 60), 110, "brazos_arriba")
    anillo(frame, (cx, cy), 82, progreso_brazos, C.AMARILLO, 8)
    texto(frame, "¡Empezar!", (cx, cy + 95), C.TAM_PEQUENO + 2, C.AMARILLO, "centro")
    texto(frame, linea, (W // 2, H - 96), C.TAM_TEXTO + 10, C.BLANCO, "centro")


def recordatorio(frame, prueba: str, t: float, sprites=None) -> None:
    """Pictograma pequeño en la esquina inferior derecha durante el ejercicio."""
    H, W = frame.shape[:2]
    tam = int(H * 0.28)
    x0, y0 = W - tam - 16, H - tam - 16
    panel(frame, x0, y0, W - 16, H - 16, alfa=0.55)
    pictograma(frame, (x0 + tam / 2, y0 + tam / 2), tam * 0.9, prueba, t, sprites)


def cuenta_atras(frame, restante: float, prueba: str, t: float, sprites=None) -> None:
    """Número grande y pictograma de la postura que hay que adoptar."""
    H, W = frame.shape[:2]
    texto(frame, f"{int(restante) + 1}", (W // 2, H // 2 - 110), 170, C.AMARILLO, "centro")
    recordatorio(frame, prueba, t, sprites)


def pausa(frame, motivo: str, repetir: bool) -> None:
    """Icono de pausa, el motivo y cómo seguir, en grande."""
    H, W = frame.shape[:2]
    panel(frame, W // 2 - 430, H // 2 - 150, W // 2 + 430, H // 2 + 150, alfa=0.8)
    icono_pausa(frame, (W // 2, H // 2 - 80), 90)
    texto(frame, motivo or "Pausa", (W // 2, H // 2 - 10), C.TAM_TEXTO + 6, C.AMARILLO, "centro")
    seguir = "Brazos arriba: repetir" if repetir else "Brazos arriba: seguir"
    texto(frame, seguir, (W // 2, H // 2 + 60), C.TAM_TEXTO, C.BLANCO, "centro")

