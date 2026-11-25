"""Punto de entrada de «El Gran Circo del Equilibrio».

Uso:
    python main.py [--camera N | --video RUTA] [--debug] [--jugador NOMBRE]
    python main.py --headless --frames 300      # prueba de humo sin ventana
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import cv2
import numpy as np

import config as C
from core.camera import FuenteCamara, FuenteSintetica
from core.storage import Almacen
from scenes.base import SALIR, Contexto, Scene
from scenes.menu import EscenaMenu
from ui.audio import Audio
from ui.background import Fondo
from ui.sprites import Sprites
from ui.text import panel, texto

# Códigos de cv2.waitKeyEx para flechas en Linux (GTK/Qt) y Windows
TECLAS_ESPECIALES = {
    65361: "izquierda", 65362: "arriba", 65363: "derecha", 65364: "abajo",
    2424832: "izquierda", 2490368: "arriba", 2555904: "derecha", 2621440: "abajo",
    13: "enter", 10: "enter", 27: "esc", 8: "retroceso", 127: "retroceso", 65288: "retroceso",
    65293: "enter", 65307: "esc",
    65480: "f11", 7995392: "f11",        # F11 en Linux (Qt/GTK) y en Windows
}


def traducir_tecla(codigo: int) -> str | None:
    """Convierte un código de waitKeyEx en una tecla lógica o un carácter."""
    if codigo < 0:
        return None
    if codigo in TECLAS_ESPECIALES:
        return TECLAS_ESPECIALES[codigo]
    c = codigo & 0xFF
    if c in TECLAS_ESPECIALES:
        return TECLAS_ESPECIALES[c]
    if 32 <= c < 127:
        return chr(c).lower() if chr(c).isalpha() else chr(c)
    if codigo in (0xF1, 0xD1):   # ñ / Ñ en Latin-1
        return "ñ"
    return None


def argumentos(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="El Gran Circo del Equilibrio (SPPB gamificada)")
    p.add_argument("--camera", type=int, default=0, help="índice de la webcam (por defecto 0)")
    p.add_argument("--video", type=str, default=None, help="lee de un archivo de vídeo en vez de la cámara")
    p.add_argument("--debug", action="store_true", help="muestra esqueleto, ángulos, balanceo, estados y fps")
    p.add_argument("--headless", action="store_true", help="sin ventana (pruebas de humo)")
    p.add_argument("--frames", type=int, default=0, help="nº de frames a ejecutar y salir (0 = sin límite)")
    p.add_argument("--resolucion", type=str, default=f"{C.CAMARA_ANCHO_PEDIDO}x{C.CAMARA_ALTO_PEDIDO}",
                   help="resolución pedida a la webcam, p. ej. 640x480")
    p.add_argument("--formato", type=str, default=C.CAMARA_FORMATO,
                   help='fourcc pedido a la webcam (MJPG, YUYV o "" para el de la cámara)')
    p.add_argument("--jugador", type=str, default=None,
                   help="nombre del jugador (por defecto, el último que jugó)")
    p.add_argument("--datos", type=str, default=C.DATA_DIR, help="carpeta de perfiles e historial")
    p.add_argument("--sin-sonido", action="store_true", help="desactiva el audio")
    p.add_argument("--sin-musica", action="store_true", help="empieza con la música apagada (tecla M)")
    p.add_argument("--sin-fondo", action="store_true", help="no sustituye el fondo por la carpa")
    p.add_argument("--pantalla-completa", action="store_true", help="empieza a pantalla completa (F11 la alterna)")
    return p.parse_args(argv)


def ruta_modelo(rapido: bool) -> str:
    """Modelo «lite» si se pide detección rápida y está descargado; si no, el «full»."""
    return C.MODEL_PATH_RAPIDO if rapido and os.path.exists(C.MODEL_PATH_RAPIDO) else C.MODEL_PATH


def crear_detector(headless: bool, rapido: bool = False, segmentacion: bool = True):
    """DetectorPose si el modelo existe; en headless puede no haberlo.

    Sin fondo de circo no se pide la máscara de segmentación (MediaPipe va algo más rápido).
    """
    ruta = ruta_modelo(rapido)
    if not os.path.exists(ruta):
        if headless:
            print("Aviso: no se encontró el modelo; se ejecuta sin detección.")
            return None
        sys.exit(f"No se encontró el modelo {ruta}. Ejecuta: python download_models.py")
    from core.pose import DetectorPose
    return DetectorPose(ruta, segmentacion=segmentacion)


def jugador_inicial(almacen: Almacen, ajustes, pedido: str | None) -> str:
    """--jugador si se indica; si no, el último jugador elegido (si su perfil sigue existiendo)."""
    if pedido:
        return pedido
    ultimo = ajustes.ultimo_jugador
    return ultimo if ultimo in almacen.todos_los_perfiles() else "Invitado"


def dibujar_debug(frame: np.ndarray, escena: Scene, pose, fps: float) -> None:
    """Esqueleto, valores internos de la escena y fps."""
    if pose is not None:                  # el esqueleto ya lo dibuja la escena; aquí, la visibilidad
        for i in range(33):
            color = C.VERDE if pose.vis(i) >= C.VISIBILIDAD_MIN else C.ROJO
            cv2.circle(frame, pose.px(i), 4, color, -1, cv2.LINE_AA)
    info = {"escena": type(escena).__name__, "fps": f"{fps:.1f}", **escena.debug_info()}
    H = frame.shape[0]
    alto = 24 * len(info) + 10
    panel(frame, 0, H - alto - 50, 380, H - 50, alfa=0.7)
    for i, (k, v) in enumerate(info.items()):
        texto(frame, f"{k}: {v}", (8, H - alto - 45 + i * 24), 18, C.AMARILLO, sombra=False)


def main(argv=None) -> int:
    args = argumentos(argv)
    if args.headless:
        fuente = FuenteCamara(video=args.video) if args.video else FuenteSintetica()
    else:
        ancho, alto = (int(v) for v in args.resolucion.lower().split("x"))
        fuente = FuenteCamara(camara=args.camera, video=args.video, ancho=ancho, alto=alto, formato=args.formato)
        print(f"Cámara: {fuente.descripcion()}")
    almacen = Almacen(args.datos)
    ajustes = almacen.cargar_ajustes()
    if args.sin_musica:                    # las opciones de la línea de órdenes mandan en esta sesión
        ajustes.musica = False
    if args.sin_fondo or not C.FONDO_SEGMENTACION:
        ajustes.fondo = False
    ctx = Contexto(
        almacen=almacen,
        audio=Audio(activado=not (args.sin_sonido or args.headless), musica=ajustes.musica),
        sprites=Sprites(),
        fondo=Fondo(activado=ajustes.fondo),
        jugador=jugador_inicial(almacen, ajustes, args.jugador),
        debug=args.debug,
        ajustes=ajustes,
    )
    ctx.aplicar_ajustes()
    conf_detector = (ajustes.deteccion_rapida, ajustes.fondo)
    detector = crear_detector(args.headless, *conf_detector)
    if not ctx.audio.disponible and not args.headless:
        print(f"Audio desactivado: {ctx.audio.motivo or 'sin sonidos'}")
    escena: Scene = EscenaMenu(ctx)
    escena.enter()
    ctx.audio.permitir_musica(escena.con_musica)
    ctx.audio.poner_pista(escena.pista_musica)
    if not args.headless:
        from ui.ventana import Ventana
        ventana = Ventana(C.VENTANA_NOMBRE, args.pantalla_completa)
    anterior = time.monotonic()
    fps = 0.0
    n = 0
    ultimo_frame = time.monotonic()
    try:
        while True:
            frame = fuente.leer()
            if frame is None:
                if time.monotonic() - ultimo_frame > C.CAMARA_ESPERA_MAX_S:
                    print("No llegan frames de la cámara. Prueba: python tools/probar_camara.py")
                    break
                if not args.headless:
                    cv2.waitKey(1)
                continue
            ultimo_frame = time.monotonic()
            ahora = time.monotonic()
            dt = min(C.DT_MAXIMO, max(1e-4, ahora - anterior))
            anterior = ahora
            fps = C.FPS_SUAVIZADO * fps + (1 - C.FPS_SUAVIZADO) * (1.0 / dt)
            ctx.fps = fps
            if detector is not None and (ajustes.deteccion_rapida, ajustes.fondo) != conf_detector:
                detector.cerrar()               # se ha cambiado en Ajustes: otro modelo o sin máscara
                conf_detector = (ajustes.deteccion_rapida, ajustes.fondo)
                detector = crear_detector(args.headless, *conf_detector)
            pose = detector.detectar(frame) if detector is not None else None
            siguiente = escena.update(pose, dt)
            salida = escena.draw(frame)
            if args.debug:
                dibujar_debug(salida, escena, pose, fps)
            if not args.headless:
                ventana.mostrar(salida)
                tecla = traducir_tecla(cv2.waitKeyEx(1))
                if tecla == "f11":
                    ventana.alternar()
                    tecla = None
                if tecla is not None and siguiente is None:
                    siguiente = escena.on_key(tecla)
                    if tecla == "m" and siguiente is None and not getattr(escena, "escribiendo", False):
                        ajustes.musica = not ajustes.musica
                        ctx.guardar_ajustes()
                if ventana.cerrada():
                    break
            if siguiente == SALIR:
                break
            if siguiente is not None:
                escena = siguiente
                escena.enter()
                ctx.audio.permitir_musica(escena.con_musica)
                ctx.audio.poner_pista(escena.pista_musica)
            n += 1
            if args.frames and n >= args.frames:
                break
    finally:
        fuente.cerrar()
        ctx.audio.cerrar()
        if detector is not None:
            detector.cerrar()
        if not args.headless:
            cv2.destroyAllWindows()
    if args.headless:
        print(f"Headless OK: {n} frames, escena final {type(escena).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
