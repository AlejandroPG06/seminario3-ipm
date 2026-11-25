# El Gran Circo del Equilibrio

Juego serio de salud controlado por visión por computador (Práctica 2 de
Interacción Persona-Máquina, Universidad de Alicante). Convierte dos pruebas de
la **SPPB** (*Short Physical Performance Battery*), una batería clínica que se
usa para estimar la **fragilidad** en personas mayores, en un espectáculo de
circo que se juega solo con el cuerpo, frente a una webcam.

## Para qué sirve

La SPPB (Guralnik et al., 1994) mide el equilibrio, la velocidad de marcha y la
fuerza de las piernas. Este juego usa dos de sus pruebas:

| Prueba | Qué mide | Puntos |
|---|---|---|
| Equilibrio: pies juntos, semitándem y tándem (10 s cada una) | Control postural | 0–4 |
| Levantarse de la silla 5 veces | Fuerza y potencia de las piernas | 0–4 |

La prueba de marcha de 4 m no es viable con una webcam, así que la puntuación
va de **0 a 8** en lugar de 0 a 12. La interpretación que muestra el juego es
**orientativa y no es un diagnóstico**.

Además se incluyen dos **pruebas complementarias** con base clínica, que dan
su propio resultado y **no suman a la SPPB**:

| Prueba | Qué mide | Referencia orientativa |
|---|---|---|
| Equilibrio sobre una pierna (hasta 30 s) | Equilibrio estático exigente | Menos de 5 s se asocia a más caídas (Vellas et al., 1997) |
| Marcha en el sitio (50 s) | Resistencia aeróbica | Versión corta del 2-Minute Step Test (Rikli y Jones): pasos de la rodilla derecha hasta media altura del muslo; la referencia de 65 pasos en 2 min se escala a 50 s (27 pasos) |

Hay tres modos:

- **Modo Evaluación**: la SPPB "pura". Empieza con una pantalla que explica qué
  es la SPPB y cómo se puntúa (también se puede abrir desde **Info SPPB** en el
  menú). Las pruebas se hacen en orden, con los tiempos y criterios originales y
  sin elementos de juego. Se hacen siempre las tres posturas de equilibrio y cada
  una puntúa por separado (el protocolo original salta las siguientes si falla
  una; se puede volver a ese comportamiento con
  `EVALUACION_SALTAR_TRAS_FALLO = True` en `config.py`). Al terminar, el juego
  ofrece las dos pruebas complementarias. Van **después** de la SPPB para que el cansancio no altere su
  medida.
- **Modo Práctica**: eliges **cualquiera de los 6 ejercicios**, sin candados, y lo
  haces con los criterios de la evaluación. Al terminar te dice cuánto valdría
  en la evaluación y te da consejos ("no muevas los pies", "tiendes a irte hacia
  tu derecha"…).
- **Modo Aventura**: los ejercicios convertidos en niveles con puntos,
  estrellas, rachas y logros. Lo lúdico nunca altera la medida clínica.

### Los 5 actos del Modo Aventura

| Acto | Ejercicio | Mecánica |
|---|---|---|
| 1. El Camarero | Pies juntos | Llevas una bandeja en el pecho; si balanceas la cadera, el vaso se desliza y se cae |
| 2. La Cuerda Floja | Tándem | El funambulista se cae solo si no lo corriges: una flecha indica hacia dónde mover la cadera |
| 3. La Bailarina | Sobre una pierna | Una bailarina sobre una pelota que rueda con tu balanceo; si apoyas el pie, se cae |
| 4. El Desfile | Marcha en el sitio | Cada paso con la rodilla hasta la línea toca el tambor; bonus por ir al compás |
| 5. El Hombre Bala | 5 levantadas de la silla | Cada levantada carga el cañón; cuanto más rápido, más lejos vuelas. En el nivel 4, *Al ritmo del cañón*, suena un tambor cada 3 s y solo cuentan las levantadas que acaban de pie justo en el golpe |

El semitándem no tiene acto propio, pero se puede entrenar en el Modo Práctica.
Cada acto tiene 4 niveles: la prueba tal cual, una versión más difícil, una con
**viento** o más ritmo, y una de **doble tarea** (tocar burbujas con la mano sin
perder el equilibrio o sin dejar de marchar). Cada nivel da de 0 a 3 estrellas; con
**2 estrellas** en un nivel se desbloquea el acto siguiente.

**La Cuerda Floja** tiene un reto distinto en cada nivel: *Primeros pasos* (aprender a
corregir), *Cruza la cuerda* (el funambulista solo avanza mientras estás estable y hay
que llegar al otro lado a tiempo; las estrellas dependen de lo rápido que cruces),
*Vendaval* (ráfagas avisadas con flechas un segundo antes) y *Malabarista* (más
inestable y con burbujas a los lados). La física es un péndulo invertido: la dificultad
está en corregir con **precisión**, con movimientos pequeños de cadera, no en moverse
mucho. La Bailarina usa la misma física, más suave. Las burbujas de la doble tarea
salen a los lados, al alcance del brazo, alternando izquierda y derecha.

**Estrellas de equilibrio**: hay que aguantar el nivel entero sin que se caiga el
vaso, el funambulista o la bailarina (si se cae, 0 estrellas). Después cuenta lo
cerca que estuvo de caerse: 3 estrellas si siempre se mantuvo cerca del centro
(menos del 40 % del camino al borde), 2 si no pasó del 75 % y 1 si estuvo a punto
de caerse. Durante el nivel, el marcador **"En juego"** muestra las estrellas que
aún se pueden conseguir. En la marcha cuentan los pasos y en la silla, el tiempo.

**Consejos de mejora**: al terminar cualquier ejercicio el juego dice qué hacer a
continuación. En la Aventura, si fallas, qué hace falta para conseguir al menos 1
estrella y, con 1 o 2, qué hace falta para la siguiente (por ejemplo, "Para 3
estrellas, hazlas en 11,19 s o menos"). En la Práctica, el siguiente objetivo de
puntos SPPB. En la Evaluación, qué prueba conviene entrenar en el Modo Práctica.

**Puntos**: se ganan por cada segundo aguantado, multiplicados por la
estabilidad (×2 "pulso de acero" con balanceo muy bajo) y por la racha de
segundos estables. En la silla, cada levantada se valora como Perfecta, Buena o
Incompleta, con bonus por velocidad y penalización por apoyar las manos en las
rodillas.

## Instalación

Requisito: tener instalado **conda** ([Miniconda](https://docs.anaconda.com/miniconda/)).

**Linux / macOS**

```bash
bash setup.sh
```

**Windows** (desde *Anaconda Prompt*)

```bat
setup.bat
```

El script crea el entorno `IPM` con Python 3.12, instala `requirements.txt`,
descarga los modelos de MediaPipe en `models/` y genera los sonidos en
`assets/sounds/`. Se puede ejecutar más de una vez. Con `--dev` instala también
pytest.

<details>
<summary>Instalación manual</summary>

```bash
conda create -n IPM python=3.12 -y
conda activate IPM
pip install -r requirements.txt        # o requirements-dev.txt para tener pytest
python download_models.py
python tools/generate_assets.py
```
</details>

En Linux, el sonido necesita PortAudio (`sudo apt install libportaudio2`). Si
no está, el juego funciona igual, pero en silencio.

## Ejecución

```bash
conda activate IPM
python main.py
```

| Argumento | Qué hace |
|---|---|
| `--camera N` | Usa la webcam número N (por defecto 0) |
| `--video RUTA` | Lee de un archivo de vídeo en bucle en lugar de la cámara |
| `--debug` | Dibuja el esqueleto e informa de los fps, el balanceo, los ángulos y el estado de las máquinas de estados |
| `--jugador NOMBRE` | Empieza con ese jugador (por defecto, el último que se eligió en el juego) |
| `--headless --frames N` | Ejecuta N frames sin abrir ventana (prueba de humo) |
| `--sin-sonido`, `--sin-musica`, `--sin-fondo` | Desactivan el audio, empiezan sin música o quitan el fondo de carpa (solo en esa sesión) |
| `--pantalla-completa` | Empieza a pantalla completa (F11 la activa o desactiva en cualquier momento) |
| `--datos CARPETA` | Carpeta de perfiles e historial (por defecto, `data/`) |

### Colocación de la cámara

- **Equilibrio y marcha** (actos 1–4): de **frente**, a unos 2,5–3 m, con el cuerpo
  entero visible, pies incluidos.
- **Silla** (acto 5): de **lado**, con la silla de perfil a la cámara y los
  brazos cruzados sobre el pecho.

El juego muestra una silueta guía y avisos ("aléjate", "no te veo los pies",
"ponte de lado"). Antes de cada prueba hay que estar 2 s quieto para la
calibración.

## Controles

Todo se puede manejar **sin teclado**:

- **Botones con dwell**: estira el brazo hacia un botón y mantén la mano 1,5 s hasta que se llene el anillo (`DWELL_S`).
  Los botones están en dos columnas a los lados, así que con los brazos en reposo no se pulsa nada.
  Solo carga un botón a la vez y, al cambiar de pantalla, hay 1 s de bloqueo.
- **Pictogramas**: cada ejercicio se explica con un muñeco animado y la posición de los pies,
  con una sola línea de texto en grande. Durante el ejercicio queda un recordatorio en la esquina.
- **Levantar los dos brazos** durante 1 s: empieza una prueba, la pausa o la reanuda.
- **Pausa automática** si se pierden de vista partes clave del cuerpo.

El teclado sirve como alternativa de accesibilidad y para depurar:

| Tecla | Acción |
|---|---|
| Flechas o WASD | Moverse por los botones |
| Enter | Pulsar el botón o empezar la prueba |
| Esc | Volver o salir |
| P | Pausar o reanudar |
| F | Marcar a mano una pérdida de equilibrio (para quien evalúa) |
| M | Activar o desactivar la música |
| F11 | Pantalla completa (también `--pantalla-completa`) |

En Linux la ventana sale grande, ajustada a la pantalla y sin las barras que OpenCV
añade con Qt. En cualquier sistema, F11 pone o quita la pantalla completa.

### Ajustes

El botón **Ajustes** (engranaje) del menú permite:

- Encender o apagar la **música** y subir o bajar su **volumen**.
- Quitar el **fondo de circo**: sin él MediaPipe no calcula la máscara de segmentación y el juego va más fluido.
- Quitar las **animaciones** decorativas (confeti).
- Cambiar la **detección** a "Rápida" (modelo `lite` de MediaPipe): más fps, algo menos de precisión.
- Mostrar u ocultar el **esqueleto** detectado (los 33 puntos del Pose Landmarker y sus conexiones). Por defecto se ve siempre, en todas las pantallas.

La pantalla muestra los fps actuales. Los ajustes se guardan solos en `data/ajustes.json`.

## Datos que se guardan

En `data/` (no se sube al repositorio):

- `perfiles.json`: por jugador, guarda el progreso de la Aventura (estrellas por nivel), los mejores puntos, los logros y las estadísticas.
- `historial.csv`: una fila por sesión, con la fecha, el modo, los tiempos de cada prueba, los puntos SPPB, los puntos de juego y las estrellas.
- `ajustes.json`: música, volumen, fondo, animaciones, detección y el **último jugador elegido**, que se carga solo al abrir el juego.

En la pantalla **Historial** se ven el ranking local y la gráfica de evolución
de la SPPB. Los **logros** tienen su propia pantalla, a la que se entra con el
trofeo de la esquina inferior derecha del menú: los conseguidos salen en verde y
los pendientes en gris. Al señalar uno con la mano (o elegirlo con las flechas)
se explica cómo se consigue y cuánto llevas.

## Personalización

- **`config.py`** reúne todos los umbrales, tiempos, colores y parámetros, con
  su unidad. Los **niveles** (`ACTOS`) y los **logros** (`LOGROS`) también están
  ahí, definidos como datos. Los cortes clínicos de la SPPB no se deben tocar.
- **Gráficos**: si dejas un PNG con transparencia en `assets/` con uno de estos
  nombres, se usa en lugar del dibujo procedural: `bandeja`, `vaso`,
  `objeto_0`, `objeto_1`, `objeto_2`, `funambulista`, `pelota`, `bailarina`,
  `tambor`, `canon`, `hombre_bala`,
  `estrella`, `estrella_vacia`, `candado`, `burbuja`, `boton`,
  `boton_inactivo`, `icono_ajustes`, `icono_info`. `assets/fondo.png` sustituye a la carpa.
- **Pies**: `assets/pies_juntos.png`, `pies_semitandem.png` y `pies_tandem.png` son siluetas
  negras con transparencia, vistas desde arriba con la punta hacia arriba. El juego les añade
  un contorno claro (color y grosor en `config.py`: `SILUETA_*`). La de pies juntos también se
  usa, partida por la mitad, para el ejercicio sobre una pierna.
- **Sonidos**: `assets/sounds/<nombre>.wav` (`click`, `cuenta`, `ya`,
  `acierto`, `fallo`, `fanfarria`, `aplausos`, `burbuja`, `canon`, `tambor` y `musica`).
  La música de fondo es un vals de circo original generado por código. Suena a la vez que
  los efectos (mezclador propio) en todas las pantallas; en El Desfile va al tempo de la marcha.
- **Pictogramas**: `assets/pic_<prueba>.png` (por ejemplo `pic_tandem.png`) sustituye al dibujo
  de los pies o del muñeco de ese ejercicio. El
  generador no sobrescribe los que ya existen.

## Tests

```bash
conda activate IPM
python -m pytest -q                         # lógica + prueba de humo de todas las escenas
python main.py --headless --frames 300      # bucle real sin ventana
```

## Estructura del proyecto

```
main.py               bucle principal, argumentos, teclado y escena activa
config.py             constantes: umbrales, tiempos, colores, niveles y logros
core/                 cámara, pose (MediaPipe), calibración, geometría, gestos, ajustes y persistencia
games/                lógica pura y testeable: bandeja, cuerda, una pierna, marcha, silla,
                      puntuación, protocolo SPPB, progreso, logros, posturas, viento,
                      burbujas y consejos de la práctica
scenes/               menú, jugador, ajustes, info SPPB, colocación, equilibrio, marcha, silla,
                      mapa, práctica, resultados, historial y flujos (Evaluación, Aventura y Práctica)
ui/                   texto con tildes (PIL), botones dwell, HUD, sprites, pictogramas,
                      partículas, fondo y audio
assets/               siluetas de pies (PNG) y sonidos generados
tools/                generate_assets.py (sonidos)
tests/                pytest con poses sintéticas
setup.sh, setup.bat   instalación
```

## Referencias

- Guralnik JM, et al. *A short physical performance battery assessing lower
  extremity function*. J Gerontol. 1994;49(2):M85-94.
- Vellas BJ, et al. *One-leg balance is an important predictor of injurious
  falls in older persons*. J Am Geriatr Soc. 1997;45(6):735-8.
- Rikli RE, Jones CJ. *Senior Fitness Test Manual*. Human Kinetics, 2013
  (2-Minute Step Test).
- [MediaPipe Pose Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker?hl=es-419).

## Créditos

Basado en el repositorio de ejemplo de la asignatura:
[CarloHSUA/IPM](https://github.com/CarloHSUA/IPM) (`app.py` y
`app_live_stream.py` se conservan como referencia).
