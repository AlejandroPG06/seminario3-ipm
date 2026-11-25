"""Configuración común de pytest: el proyecto en sys.path y un contexto sin cámara."""
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


@pytest.fixture
def ctx(tmp_path):
    """Contexto con almacén temporal, sin audio y sprites procedurales."""
    from core.storage import Almacen
    from scenes.base import Contexto
    from ui.audio import Audio
    from ui.background import Fondo
    from ui.sprites import Sprites
    return Contexto(Almacen(str(tmp_path)), Audio(activado=False), Sprites(None),
                    Fondo(activado=True, directorio=None), jugador="Test", debug=True, semilla=1)
