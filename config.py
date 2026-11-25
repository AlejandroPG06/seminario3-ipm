"""Constantes del juego «El Gran Circo del Equilibrio».

Este archivo contiene SOLO constantes (nada de estado de partida).
Cada valor lleva un comentario con su unidad. Las distancias del cuerpo se
expresan en «anchuras de hombros» (aw), medidas en la calibración, para que
no dependan de lo lejos que esté el jugador de la cámara.
"""
import os

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "pose_landmarker_full.task")
MODEL_PATH_RAPIDO = os.path.join(BASE_DIR, "models", "pose_landmarker_lite.task")   # Ajustes → detección rápida
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
DATA_DIR = os.path.join(BASE_DIR, "data")
PERFILES_ARCHIVO = "perfiles.json"      # dentro de DATA_DIR
HISTORIAL_ARCHIVO = "historial.csv"     # dentro de DATA_DIR
AJUSTES_ARCHIVO = "ajustes.json"        # dentro de DATA_DIR: volumen, fondo, animaciones, último jugador

# ---------------------------------------------------------------------------
# Ventana y cámara
# ---------------------------------------------------------------------------
VENTANA_NOMBRE = "El Gran Circo del Equilibrio"
VENTANA_FRACCION_PANTALLA = 0.88    # Linux (Qt): la ventana ocupa como mucho esta fracción de la pantalla (F11: completa)
CAMARA_ANCHO_PEDIDO = 1280      # px, resolución que se pide a la webcam
CAMARA_ALTO_PEDIDO = 720        # px
CAMARA_FORMATO = "MJPG"         # fourcc pedido a la webcam: MJPG va comprimido (mejor por USB/usbipd); "" = el de la cámara
CAMARA_ESPERA_MAX_S = 5.0       # s sin recibir frames de la cámara antes de rendirse
ALTO_LIENZO = 720               # px, el frame se reescala a esta altura (manteniendo proporción)
DT_MAXIMO = 0.5                 # s, tope del dt por frame (solo para congelaciones; los cronómetros usan el dt real)
FISICA_PASO_MAX = 1 / 60        # s, la física se subdivide en pasos de como mucho este tamaño
FPS_SUAVIZADO = 0.9             # adimensional, EMA del contador de fps de depuración

# ---------------------------------------------------------------------------
# Pose Landmarker
# ---------------------------------------------------------------------------
POSE_MIN_DETECCION = 0.5        # confianza mínima de detección (0-1)
POSE_MIN_PRESENCIA = 0.5        # confianza mínima de presencia (0-1)
POSE_MIN_SEGUIMIENTO = 0.5      # confianza mínima de seguimiento (0-1)
EMA_ALFA = 0.3                  # 0-1, peso del frame nuevo en el suavizado (más alto = menos suave)
VISIBILIDAD_MIN = 0.5           # 0-1, por debajo se considera que el landmark no se ve
FRAMES_PERDIDA_PAUSA = 12       # frames seguidos sin ver landmarks clave para pausar

# Índices de landmarks
NARIZ = 0
HOMBRO_IZQ, HOMBRO_DER = 11, 12
CODO_IZQ, CODO_DER = 13, 14
MUNECA_IZQ, MUNECA_DER = 15, 16
INDICE_IZQ, INDICE_DER = 19, 20
CADERA_IZQ, CADERA_DER = 23, 24
RODILLA_IZQ, RODILLA_DER = 25, 26
TOBILLO_IZQ, TOBILLO_DER = 27, 28
TALON_IZQ, TALON_DER = 29, 30
PUNTA_IZQ, PUNTA_DER = 31, 32

# Grupos de landmarks clave y el aviso que se muestra si se pierden
GRUPOS_CLAVE_EQUILIBRIO = {
    "hombros": ((HOMBRO_IZQ, HOMBRO_DER), "No te veo los hombros: colócate de frente"),
    "caderas": ((CADERA_IZQ, CADERA_DER), "No te veo la cadera: aléjate un poco"),
    "pies": ((TOBILLO_IZQ, TOBILLO_DER), "No te veo los pies: aléjate de la cámara"),
}
GRUPOS_CLAVE_MARCHA = {
    "hombros": ((HOMBRO_IZQ, HOMBRO_DER), "No te veo los hombros: colócate de frente"),
    "caderas": ((CADERA_IZQ, CADERA_DER), "No te veo la cadera: aléjate un poco"),
    "rodillas": ((RODILLA_IZQ, RODILLA_DER), "No te veo las rodillas: aléjate de la cámara"),
}

# ---------------------------------------------------------------------------
# Colocación y calibración
# ---------------------------------------------------------------------------
CALIB_DURACION_S = 2.0          # s que hay que estar quieto para calibrar
CALIB_MOVIMIENTO_MAX = 0.08     # aw, desplazamiento de la cadera que reinicia la calibración
ENCUADRE_OK_S = 1.0             # s con encuadre correcto antes de empezar a calibrar
ENCUADRE_ALTURA_MIN = 0.55      # fracción del alto de imagen (nariz→tobillos) mínima: si menos, «acércate»
ENCUADRE_ALTURA_MAX = 0.90      # fracción máxima: si más, «aléjate»
ENCUADRE_MARGEN = 0.03          # fracción del borde de imagen que no debe tocar el cuerpo
ENCUADRE_CENTRO_MAX = 0.20      # fracción del ancho: distancia máx. de la cadera al centro
VISTA_FRENTE_RATIO_MIN = 0.45   # anchura hombros / altura torso mínima para estar «de frente»
VISTA_LADO_RATIO_MAX = 0.30     # anchura hombros / altura torso máxima para estar «de lado»

# ---------------------------------------------------------------------------
# Gestos
# ---------------------------------------------------------------------------
DWELL_S = 1.5                   # s con la mano sobre un botón para pulsarlo
DWELL_DECAIMIENTO = 2.0         # factor: velocidad a la que se vacía el anillo al quitar la mano
DWELL_BLOQUEO_S = 1.0           # s sin aceptar dwell al abrir un menú o tras pulsar (evita pulsaciones encadenadas)
# Menús en dos columnas a los lados: con las manos en reposo (junto a la cadera) no se toca ningún botón
MENU_COLUMNAS_X = (0.20, 0.80)  # fracción del ancho: centro de la columna izquierda y derecha
MENU_FILAS_Y = (0.17, 0.66)     # fracción del alto: zona vertical de los botones (alcanzable estirando el brazo)
MENU_BOTON_ANCHO = 260          # px
MENU_BOTON_ALTO = 84            # px
MENU_FILAS_Y_4 = (0.17, 0.72)   # fracción del alto: zona de los botones cuando hay 4 filas por columna
MENU_BOTON_ALTO_4 = 72          # px, alto de los botones cuando hay 4 filas por columna
MENU_TROFEO_TAM = 84            # px, botón del trofeo (logros) en la esquina inferior derecha del menú
MENU_TROFEO_MARGEN = 24         # px desde los bordes de la imagen
BRAZOS_ARRIBA_S = 1.0           # s con las dos muñecas por encima de la nariz para el gesto
BRAZOS_ARRIBA_MARGEN = 0.05     # fracción del alto de imagen por encima de la nariz

# ---------------------------------------------------------------------------
# Equilibrio (actos 1-3)
# ---------------------------------------------------------------------------
PRUEBA_EQUILIBRIO_S = 10.0      # s, duración clínica de cada postura de equilibrio (SPPB)
# Protocolo original (Guralnik 1994): si no se aguanta una postura, se saltan las siguientes.
# False = se hacen siempre las tres posturas y cada una puntúa por separado.
EVALUACION_SALTAR_TRAS_FALLO = False
CUENTA_ATRAS_S = 3.0            # s de cuenta atrás antes de cada prueba
ZONA_MUERTA_BALANCEO = 0.03     # aw, balanceo por debajo del cual se considera 0
BALANCEO_EMA_ALFA = 0.25        # 0-1, suavizado adicional del balanceo
REFERENCIA_EMA_ALFA = 0.05      # 0-1, suavizado de la cadera de reposo durante la cuenta atrás

# Verificación de postura de pies (relativa a la anchura de hombros)
VERIFICACION_POSTURA_ESTRICTA = False   # True: no deja empezar sin postura correcta (plan A)
PIES_JUNTOS_DX_MAX = 0.45       # aw, separación horizontal máx. de tobillos con pies juntos
SEMITANDEM_DX_MAX = 0.45        # aw, separación horizontal máx. en semitándem
SEMITANDEM_DY_MIN = 0.03        # aw, desfase vertical mín. (un pie adelantado) en semitándem
TANDEM_DX_MAX = 0.25            # aw, separación horizontal máx. en tándem (un pie delante del otro)
TANDEM_DY_MIN = 0.06            # aw, desfase vertical mín. en tándem
PIES_MOVIDOS_MAX = 0.35         # aw, desplazamiento de un tobillo que cuenta como «ha movido los pies»
PIES_MOVIDOS_FRAMES = 6         # frames seguidos por encima del umbral para darlo por movido

# Física de la bandeja (unidades: x en «medias bandejas», -1..1 es la bandeja)
BANDEJA_GANANCIA = 140.0        # grados de inclinación por aw de balanceo
BANDEJA_INCLINACION_MAX = 30.0  # grados, inclinación máxima
BANDEJA_GRAVEDAD = 4.0          # medias bandejas/s² por unidad de seno de inclinación
BANDEJA_ROZAMIENTO = 1.0        # 1/s, amortiguación exponencial de la velocidad
BANDEJA_BORDE = 1.0             # medias bandejas, el vaso cae si |x| > borde
BANDEJA_INERCIA_POR_OBJETO = 0.6   # inercia extra por cada objeto apilado adicional
BANDEJA_BORDE_POR_OBJETO = 0.08    # medias bandejas que se pierden de borde por objeto extra
BANDEJA_VEL_REPOSO = 0.02       # medias bandejas/s: por debajo y sin inclinación se para

# Física de la cuerda floja (ángulo del funambulista en grados)
CUERDA_GANANCIA = 900.0         # grados/s² por aw de balanceo (alta: en tándem la cadera apenas se puede mover)
CUERDA_RIGIDEZ = 4.0            # 1/s², fuerza recuperadora hacia el centro
CUERDA_AMORTIGUACION = 2.5      # 1/s, amortiguación de la velocidad angular
CUERDA_ANGULO_MAX = 35.0        # grados, si se supera el funambulista cae
CUERDA_ZONA_MUERTA = 0.012      # aw, zona muerta en la cuerda y la pelota (más fina: hay que corregir con precisión)
CUERDA_TEMBLOR = 8.0            # grados/s², perturbación aleatoria cuando hay inestabilidad
CUERDA_TEMBLOR_TAU_S = 1.5      # s, lo que tarda el temblor en cambiar de lado
CUERDA_AVISO_PELIGRO = 0.35     # fracción del ángulo máximo a partir de la que se indica hacia dónde corregir
# Inestabilidad por nivel (clave "inestabilidad", 1/s²): por encima de CUERDA_RIGIDEZ el
# funambulista se cae solo si no se corrige. Cuanto más alta, más rápido se va.

# ---------------------------------------------------------------------------
# Equilibrio sobre una pierna (acto 3 «La Bailarina» y prueba complementaria)
# Single Leg Stance: no aguantar 5 s se asocia a más caídas (Vellas et al., 1997).
# ---------------------------------------------------------------------------
UNA_PIERNA_EVAL_S = 30.0        # s, duración máxima de la prueba en Evaluación/Práctica
UNA_PIERNA_RIESGO_S = 5.0       # s, por debajo: riesgo de caídas aumentado (orientativo)
UNA_PIERNA_LEVANTADO = 0.25     # aw, diferencia de altura entre tobillos para dar el pie por levantado
UNA_PIERNA_APOYADO = 0.10       # aw, por debajo de esta diferencia el pie ha vuelto al suelo (histéresis)
UNA_PIERNA_APOYO_FRAMES = 4     # frames seguidos con el pie abajo para darlo por apoyado
PELOTA_GANANCIA = 650.0         # grados/s² por aw: la pelota de la bailarina (más suave que la cuerda)

# ---------------------------------------------------------------------------
# Marcha en el sitio (acto 4 «El Desfile» y prueba complementaria)
# 2-Minute Step Test (Rikli y Jones): rodilla hasta la mitad entre rótula y cresta ilíaca.
# ---------------------------------------------------------------------------
MARCHA_EVAL_S = 50.0            # s, duración de la prueba en la Evaluación (versión corta del test de 2 min)
MARCHA_REFERENCIA_S = 120.0     # s, duración del 2-Minute Step Test original (a la que se refieren los pasos)
MARCHA_SUBIDA = 0.5             # fracción (0 = rodilla en reposo, 1 = a la altura de la cadera) para contar el paso
MARCHA_BAJADA = 0.2             # fracción por debajo de la cual la rodilla vuelve a «abajo» (histéresis)
MARCHA_REFERENCIA_PASOS = 65    # pasos de la rodilla derecha en 2 min; se escala a MARCHA_EVAL_S (orientativo, verificar)
MARCHA_TOLERANCIA_S = 0.15      # s de margen respecto al tiempo para que un paso esté «al compás»
PUNTOS_PASO = 10                # puntos por paso válido
PUNTOS_COMPAS = 10              # puntos extra por paso al compás

# ---------------------------------------------------------------------------
# Silla (acto 4)
# ---------------------------------------------------------------------------
SILLA_REPETICIONES = 5          # levantadas de la prueba clínica
SILLA_TIEMPO_MAX_S = 60.0       # s, límite de la prueba (SPPB)
SILLA_ANGULO_DE_PIE = 160.0     # grados de rodilla para pasar a «de pie»
SILLA_ANGULO_SENTADO = 110.0    # grados de rodilla para volver a «sentado»
SILLA_ANGULO_SUBIENDO = 125.0   # grados: desde «sentado», por encima empieza «subiendo» (histéresis)
SILLA_ANGULO_BAJANDO = 150.0    # grados: desde «de pie», por debajo empieza «bajando»
SILLA_SUBIDA_PERFECTA_S = 1.5   # s, subida igual o más rápida y sin manos = «Perfecta»
SILLA_MANOS_RODILLA_MAX = 0.35  # longitudes de muslo: muñeca más cerca de la rodilla = apoyo
SILLA_RITMO_TOLERANCIA_S = 0.6  # s, «Al ritmo del cañón»: margen para estar de pie respecto al golpe de tambor
SILLA_CUENTA_ATRAS_S = 5.0      # s para sentarse y cruzar los brazos tras dar la orden

# ---------------------------------------------------------------------------
# Puntuación SPPB (Guralnik et al., 1994). ¡No tocar: son criterios clínicos!
# ---------------------------------------------------------------------------
SPPB_TANDEM_PARCIAL_S = 3.0     # s, tándem entre 3 y 9,99 s = 1 punto
SPPB_SILLA_CORTES = [           # (tiempo máximo en s, puntos)
    (11.19, 4),
    (13.69, 3),
    (16.69, 2),
    (60.0, 1),
]
# Interpretación ORIENTATIVA de la versión reducida 0-8 (no validada clínicamente)
SPPB_INTERPRETACION = [         # (puntuación mínima, texto)
    (7, "Buen rendimiento físico"),
    (5, "Limitación leve"),
    (3, "Limitación moderada"),
    (0, "Limitación importante: conviene consultar con un profesional"),
]

# ---------------------------------------------------------------------------
# Puntos, rachas y estrellas (Modo Aventura)
# ---------------------------------------------------------------------------
PUNTOS_POR_SEGUNDO = 10         # puntos por segundo aguantado (antes de multiplicadores)
MULTIPLICADORES_ESTABILIDAD = [  # (balanceo máx. en aw, multiplicador, etiqueta)
    (0.05, 2.0, "Pulso de acero"),
    (0.15, 1.0, "Estable"),
    (float("inf"), 0.5, "Inestable"),
]
RACHA_UMBRAL = 0.08             # aw, balanceo por debajo del cual la racha sigue
RACHA_PASO_S = 3.0              # s de racha para subir un escalón de multiplicador
RACHA_INCREMENTO = 0.25         # multiplicador extra por escalón de racha
RACHA_MULT_MAX = 2.0            # tope del multiplicador por racha
# Estrellas de equilibrio (si completa el nivel): según lo cerca que llegó a caerse el vaso,
# el funambulista o la bailarina (peligro 0 = centro, 1 = se cae). Peligro máximo < 1º valor → 2★,
# < 2º valor → 3★; si no, 1★. Un nivel puede llevar su propia clave "estrellas_peligro".
ESTRELLAS_PELIGRO = (0.75, 0.40)
ESTRELLAS_DESBLOQUEO_ACTO = 2   # estrellas en algún nivel del acto anterior para desbloquear el siguiente
ESTRELLAS_DESBLOQUEO_NIVEL = 1  # estrellas en el nivel anterior para desbloquear el siguiente

PUNTOS_SILLA_REPETICION = {"Perfecta": 150, "Buena": 100, "Incompleta": 0}  # puntos por repetición
PUNTOS_SILLA_BONUS_POR_S = 20   # puntos por cada segundo por debajo del tiempo límite de 3★
PUNTOS_SILLA_PENALIZACION_MANOS = 50   # puntos que se restan por repetición con apoyo de manos
PUNTOS_BURBUJA = 25             # puntos por burbuja tocada (doble tarea)

# Cañón (acto 4): distancia en metros según el tiempo total
CANON_DISTANCIA_MAX_M = 50.0    # m con tiempo <= CANON_TIEMPO_REF_S
CANON_TIEMPO_REF_S = 8.0        # s
CANON_METROS_POR_S = 2.5        # m que se pierden por cada segundo de más
CANON_VUELO_S = 2.5             # s que dura la animación del disparo

# ---------------------------------------------------------------------------
# Peligros: viento y doble tarea
# ---------------------------------------------------------------------------
VIENTO_INTERVALO_S = (3.0, 6.0)     # s, rango aleatorio entre ráfagas
VIENTO_DURACION_S = 1.5             # s, duración de cada ráfaga
VIENTO_AVISO_S = 1.2                # s antes de una ráfaga en que se avisa (niveles con "aviso_viento")
CRUZAR_PELIGRO_MAX = 0.45           # 0-1, en «Cruza la cuerda» el funambulista avanza si el peligro es menor
BURBUJA_INTERVALO_S = 2.5           # s entre burbujas
BURBUJA_VIDA_S = 4.0                # s antes de que una burbuja desaparezca
BURBUJA_RADIO = 0.045               # fracción del ancho de imagen
BURBUJA_ALCANCE = (1.3, 2.0)        # aw, distancia desde el hombro de ese lado (≈ brazo estirado)
BURBUJA_ANGULO = (-65.0, 40.0)      # grados respecto a la horizontal hacia fuera (negativo = por encima del hombro)
BURBUJA_SEPARACION = 3.0            # radios de burbuja: distancia mínima entre dos burbujas a la vez

# ---------------------------------------------------------------------------
# Modo Aventura: actos y niveles (datos; añadir/editar aquí)
# ---------------------------------------------------------------------------
# Claves de nivel de equilibrio: duracion_s, objetos, viento (fuerza en medias bandejas/s²
# o grados/s² en la cuerda), burbujas (bool), estrellas_peligro (opcional, ver ESTRELLAS_PELIGRO).
# Claves de nivel de silla: repeticiones, tiempo_limite_s, estrellas_s (tiempos para 1★,2★,3★),
# manos_falla (bool: apoyar las manos invalida la repetición).
ACTOS = [
    {
        "id": 1, "nombre": "El Camarero", "prueba": "pies_juntos", "mecanica": "bandeja",
        "vista": "frente", "objetos_apilados": "vasos",
        "descripcion": "Pies juntos. Que no se caiga el vaso.",
        "niveles": [
            {"nombre": "Primer servicio", "duracion_s": 10, "objetos": 1, "viento": 0.0, "burbujas": False},
            {"nombre": "Hora punta", "duracion_s": 20, "objetos": 3, "viento": 0.0, "burbujas": False},
            {"nombre": "Terraza con viento", "duracion_s": 15, "objetos": 1, "viento": 0.8, "burbujas": False},
            {"nombre": "Servir y cobrar", "duracion_s": 20, "objetos": 1, "viento": 0.0, "burbujas": True},
        ],
    },
    {
        "id": 2, "nombre": "La Cuerda Floja", "prueba": "tandem", "mecanica": "cuerda",
        "vista": "frente",
        "descripcion": "Tándem. Cruza la cuerda sin caer.",
        "niveles": [
            # inestabilidad > CUERDA_RIGIDEZ (4): el funambulista se cae solo si no corriges con la cadera
            {"nombre": "Primeros pasos", "duracion_s": 10, "objetos": 1, "viento": 0.0, "burbujas": False,
             "inestabilidad": 4.2},
            # cruzar: el funambulista solo avanza mientras está estable; hay que llegar al otro lado
            # (avance_s de estabilidad) antes de duracion_s; estrellas_s = tiempos para 1★, 2★, 3★
            {"nombre": "Cruza la cuerda", "duracion_s": 40, "objetos": 1, "viento": 0.0, "burbujas": False,
             "inestabilidad": 4.4, "cruzar": True, "avance_s": 12, "estrellas_s": (40, 22, 15)},
            # aviso_viento: flechas un segundo antes de cada ráfaga para anticiparse
            {"nombre": "Vendaval", "duracion_s": 15, "objetos": 1, "viento": 35.0, "burbujas": False,
             "inestabilidad": 4.4, "aviso_viento": True},
            {"nombre": "Malabarista", "duracion_s": 20, "objetos": 1, "viento": 0.0, "burbujas": True,
             "inestabilidad": 4.6},
        ],
    },
    {
        "id": 3, "nombre": "La Bailarina", "prueba": "una_pierna", "mecanica": "pelota",
        "vista": "frente",
        "descripcion": "Una pierna. No te caigas de la pelota.",
        "niveles": [
            {"nombre": "Puntillas", "duracion_s": 8, "objetos": 1, "viento": 0.0, "burbujas": False},
            {"nombre": "A la pata coja", "duracion_s": 15, "objetos": 1, "viento": 0.0, "burbujas": False,
             "inestabilidad": 4.2},
            {"nombre": "Brisa en la pista", "duracion_s": 12, "objetos": 1, "viento": 30.0, "burbujas": False,
             "inestabilidad": 4.2, "aviso_viento": True},
            {"nombre": "Baile de burbujas", "duracion_s": 15, "objetos": 1, "viento": 0.0, "burbujas": True,
             "inestabilidad": 4.4},
        ],
    },
    {
        "id": 4, "nombre": "El Desfile", "prueba": "marcha", "mecanica": "tambor",
        "vista": "frente",
        "descripcion": "Marcha al ritmo del tambor.",
        # tempo_bpm: pasos por minuto (0 = libre); estrellas_pasos: pasos para 1★, 2★, 3★
        "niveles": [
            {"nombre": "Calentamiento", "duracion_s": 30, "tempo_bpm": 0, "estrellas_pasos": (25, 35, 45), "burbujas": False},
            {"nombre": "Marcha militar", "duracion_s": 45, "tempo_bpm": 100, "estrellas_pasos": (45, 60, 70), "burbujas": False},
            {"nombre": "Redoble", "duracion_s": 45, "tempo_bpm": 120, "estrellas_pasos": (55, 75, 85), "burbujas": False},
            {"nombre": "Banda completa", "duracion_s": 45, "tempo_bpm": 100, "estrellas_pasos": (40, 55, 65), "burbujas": True},
        ],
    },
    {
        "id": 5, "nombre": "El Hombre Bala", "prueba": "silla", "mecanica": "canon",
        "vista": "lado",
        "descripcion": "Levántate para cargar el cañón.",
        "niveles": [
            {"nombre": "Carga básica", "repeticiones": 5, "tiempo_limite_s": 60, "estrellas_s": (60, 16.69, 13.69), "manos_falla": False},
            {"nombre": "Doble carga", "repeticiones": 8, "tiempo_limite_s": 60, "estrellas_s": (60, 26.0, 21.0), "manos_falla": False},
            {"nombre": "Carga exprés", "repeticiones": 5, "tiempo_limite_s": 30, "estrellas_s": (30, 13.69, 11.19), "manos_falla": False},
            # ritmo_s: un golpe de tambor cada ritmo_s s; solo cuentan las levantadas que acaban de pie
            # en el golpe (± SILLA_RITMO_TOLERANCIA_S). estrellas_fallos = fuera de ritmo máx. para 1★, 2★, 3★
            {"nombre": "Al ritmo del cañón", "repeticiones": 5, "tiempo_limite_s": 60, "estrellas_s": (60, 16.69, 13.69),
             "manos_falla": True, "ritmo_s": 3.0, "estrellas_fallos": (99, 2, 0)},
        ],
    },
]

NOMBRES_PRUEBA = {
    "pies_juntos": "Pies juntos",
    "semitandem": "Semitándem",
    "tandem": "Tándem",
    "una_pierna": "Sobre una pierna",
    "marcha": "Marcha en el sitio",
    "silla": "Levantarse de la silla",
}
INSTRUCCIONES_PRUEBA = {
    "pies_juntos": "Junta los pies, uno al lado del otro.",
    "semitandem": "Pon el talón de un pie junto al dedo gordo del otro.",
    "tandem": "Pon un pie justo delante del otro, talón con punta.",
    "una_pierna": "Levanta un pie del suelo y aguanta sobre la otra pierna.",
    "marcha": "Marcha en el sitio subiendo las rodillas hasta la línea.",
    "silla": "Siéntate de lado a la cámara con los brazos cruzados sobre el pecho.",
}
AVISO_SEGURIDAD = "Ten cerca una pared o una silla por si necesitas apoyarte."
# Una línea corta por ejercicio (se lee desde lejos; el resto lo explica el pictograma)
INSTRUCCION_CORTA = {
    "pies_juntos": "Pies juntos y quieto",
    "semitandem": "Talón junto al dedo gordo",
    "tandem": "Un pie justo delante del otro",
    "una_pierna": "Levanta un pie y aguanta",
    "marcha": "Rodillas hasta la línea",
    "silla": "Levántate y siéntate",
}
# Pruebas que se pueden hacer en el Modo Práctica (en este orden)
EJERCICIOS_PRACTICA = ["pies_juntos", "semitandem", "tandem", "una_pierna", "marcha", "silla"]
# Pruebas de la SPPB (cuentan en la puntuación 0-8) y complementarias (resultado aparte)
PRUEBAS_SPPB = ["pies_juntos", "semitandem", "tandem", "silla"]
PRUEBAS_COMPLEMENTARIAS = ["una_pierna", "marcha"]

# ---------------------------------------------------------------------------
# Logros (datos). Condición: estadística <op> valor.
# Estadísticas disponibles: sesiones, sppb_max, silla_mejor_s, racha_max_s,
# estrellas_acto_N, actos_desbloqueados, viento_superado, burbujas_total,
# una_pierna_max_s, compas_max
# ---------------------------------------------------------------------------
LOGROS = [
    {"id": "primera_funcion", "nombre": "Primera función", "descripcion": "Completa tu primera sesión", "explicacion": "Termina cualquier sesión: una evaluación, un nivel de la Aventura o un ejercicio de Práctica.",
     "clave": "sesiones", "op": ">=", "valor": 1},
    {"id": "constancia", "nombre": "Constancia", "descripcion": "Juega 5 sesiones", "explicacion": "Juega 5 sesiones en cualquier modo. Practicar a menudo es lo que más mejora el equilibrio.",
     "clave": "sesiones", "op": ">=", "valor": 5},
    {"id": "pulso_acero", "nombre": "Pulso de acero", "descripcion": "Racha de 10 s muy estable", "explicacion": "En un nivel de equilibrio de la Aventura, aguanta 10 segundos seguidos casi sin balancearte.",
     "clave": "racha_max_s", "op": ">=", "valor": 10},
    {"id": "funambulista", "nombre": "Funambulista", "descripcion": "3 estrellas en La Cuerda Floja", "explicacion": "Consigue 3 estrellas en un nivel del acto 2, La Cuerda Floja (tándem).",
     "clave": "estrellas_acto_2", "op": ">=", "valor": 3},
    {"id": "bailarina", "nombre": "Prima ballerina", "descripcion": "3 estrellas en La Bailarina", "explicacion": "Consigue 3 estrellas en un nivel del acto 3, La Bailarina (sobre una pierna).",
     "clave": "estrellas_acto_3", "op": ">=", "valor": 3},
    {"id": "flamenco", "nombre": "Flamenco", "descripcion": "Aguanta 30 s sobre una pierna", "explicacion": "Aguanta 30 segundos sobre una pierna en la Evaluación o en la Práctica.",
     "clave": "una_pierna_max_s", "op": ">=", "valor": 30},
    {"id": "tamborilero", "nombre": "Tamborilero", "descripcion": "40 pasos al compás en un desfile", "explicacion": "En El Desfile, da 40 pasos siguiendo el ritmo del tambor en un mismo nivel.",
     "clave": "compas_max", "op": ">=", "valor": 40},
    {"id": "muelle_humano", "nombre": "Muelle humano", "descripcion": "5 levantadas en 11,19 s o menos", "explicacion": "Haz las 5 levantadas de la silla en 11,19 s o menos (la máxima puntuación de la SPPB).",
     "clave": "silla_mejor_s", "op": "<=", "valor": 11.19},
    {"id": "gran_estreno", "nombre": "Gran estreno", "descripcion": "Desbloquea los 5 actos", "explicacion": "Desbloquea los 5 actos de la Aventura consiguiendo estrellas en cada uno.",
     "clave": "actos_desbloqueados", "op": ">=", "valor": 5},
    {"id": "contra_viento", "nombre": "Contra el viento", "descripcion": "Supera un nivel con viento", "explicacion": "Supera, con al menos 1 estrella, un nivel de la Aventura que tenga ráfagas de viento.",
     "clave": "viento_superado", "op": ">=", "valor": 1},
    {"id": "cazaburbujas", "nombre": "Cazaburbujas", "descripcion": "Toca 20 burbujas en total", "explicacion": "Toca 20 burbujas en total en los niveles de doble tarea de la Aventura.",
     "clave": "burbujas_total", "op": ">=", "valor": 20},
    {"id": "sppb_perfecta", "nombre": "Estrella del circo", "descripcion": "Saca 8/8 en el Modo Evaluación", "explicacion": "Consigue la puntuación máxima, 8 de 8, en el Modo Evaluación.",
     "clave": "sppb_max", "op": ">=", "valor": 8},
]

# ---------------------------------------------------------------------------
# Colores (BGR) y estilo
# ---------------------------------------------------------------------------
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
GRIS = (140, 140, 140)
ROJO = (60, 60, 220)
VERDE = (80, 200, 80)
AMARILLO = (40, 210, 250)
NARANJA = (30, 140, 250)
AZUL = (220, 140, 40)
DORADO = (40, 190, 240)
ROJO_CARPA = (40, 40, 190)
CREMA_CARPA = (215, 235, 245)
PANEL_FONDO = (40, 25, 25)      # color de los paneles semitransparentes
PANEL_ALFA = 0.6                # 0-1, opacidad de los paneles
TAM_TITULO = 56                 # px, tamaño de letra de títulos
TAM_TEXTO = 32                  # px, tamaño de letra normal
TAM_PEQUENO = 22                # px, tamaño de letra pequeño
BOTON_ANCHO = 420               # px
BOTON_ALTO = 70                 # px
BOTON_SEPARACION = 18           # px
TEXTO_FLOTANTE_S = 1.2          # s que dura un texto flotante
ESQUELETO_COLOR = (255, 200, 0)    # BGR, líneas del esqueleto detectado (azul claro)
ESQUELETO_PUNTO = (255, 255, 255)  # BGR, articulaciones
ESQUELETO_GROSOR = 0.006        # fracción del alto de la imagen: grosor de las líneas
SILUETA_RELLENO = (35, 35, 35)  # BGR, relleno de las siluetas de pies (assets/pies_*.png)
SILUETA_CONTORNO = (245, 245, 245)  # BGR, contorno para que se vean sobre fondos oscuros
SILUETA_GROSOR = 0.035          # fracción del alto de la silueta: grosor del contorno
CONFETI_PARTICULAS = 160        # nº de partículas de confeti al superar un nivel
FONDO_SEGMENTACION = True       # usa la máscara para poner la carpa de fondo
MASCARA_UMBRAL_SUAVE = (0.3, 0.7)   # rango de la máscara que se funde (0-1)

# Fuentes candidatas (la primera que exista); si ninguna, la de Pillow
# Audio
AUDIO_SR = 44100                # Hz, frecuencia de mezcla
AUDIO_BLOQUE = 1024             # muestras por bloque del callback (~23 ms)
AUDIO_MAX_EFECTOS = 8           # efectos sonando a la vez como máximo
VOLUMEN_MUSICA = 0.15           # 0-1, la música queda por debajo de los efectos (= 50 % en Ajustes)
VOLUMEN_MUSICA_MAX = 0.30       # 0-1, volumen de la música con el 100 % de Ajustes
AJUSTES_VOLUMEN_PASO = 10       # %, lo que sube o baja cada pulsación de Volumen +/−
VOLUMEN_EFECTOS = 0.9           # 0-1

FUENTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


# ---------------------------------------------------------------------------
# LEGADO: solo para app.py y app_live_stream.py (ejemplos del profesor).
# El juego nuevo NO usa esto. Borrar junto con esos dos scripts.
# ---------------------------------------------------------------------------
class Config:
    def __init__(self):
        self.model_path = MODEL_PATH
        self.padding = 100
        self.game_time = 20
        self.circle_time = 1
        self.circle_time_radius = 15


config = Config()
