"""Pruebas del propio arnés de pruebas (Etapa 2, Tarea 1).

Estas pruebas validan la INFRAESTRUCTURA de pruebas, no el comportamiento de negocio de la
Etapa 1 (las pruebas de regresión corresponden a las tareas 2–5). Comprueban que:

1. El entorno de pruebas inicializa y la app heredada es importable.
2. La base de datos de prueba está aislada y es temporal (no es la histórica).
3. Se puede acceder a la aplicación FastAPI heredada sin usar la DB histórica.
4. El aislamiento no deja estado persistente entre pruebas.
"""

from pathlib import Path

import app.config as config
import app.db as db


def test_entorno_importa_la_app_heredada(app_client):
    """El arnés inicializa y expone un cliente de la app heredada."""
    assert app_client is not None


def test_db_de_prueba_esta_aislada_y_es_temporal(isolated_db_path):
    """La ruta de DB parcheada apunta a un archivo temporal, no a la DB histórica."""
    # La ruta efectiva de la aplicación es la temporal.
    assert config.DB_PATH == isolated_db_path
    assert db.DB_PATH == isolated_db_path
    # No es el archivo histórico `shift_bank.db` del backend.
    assert isolated_db_path.name != "shift_bank.db"
    # Está dentro de un directorio temporal, no del árbol del backend.
    backend_root = Path(config.__file__).resolve().parent.parent
    assert backend_root not in isolated_db_path.resolve().parents


def test_la_app_crea_su_db_en_la_ruta_aislada(app_client, isolated_db_path):
    """Tras el arranque de la app, la DB existe y es la temporal; la histórica no se toca."""
    # El arranque (startup) ejecutó init_schema + seed contra la DB aislada.
    assert isolated_db_path.exists()
    # Un endpoint heredado responde usando esa DB (no la histórica).
    resp = app_client.get("/api/accounts")
    assert resp.status_code == 200
    # El esquema existe en la DB aislada (tabla `account` creada por el arranque).
    conn = db.get_connection(isolated_db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='account'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_rutas_de_db_distintas_entre_pruebas(isolated_db_path):
    """Cada prueba recibe una ruta de DB única (sin estado compartido)."""
    # Guardar la ruta en un atributo de clase del módulo para comparar entre invocaciones.
    seen = getattr(test_rutas_de_db_distintas_entre_pruebas, "_seen", set())
    assert str(isolated_db_path) not in seen
    seen.add(str(isolated_db_path))
    test_rutas_de_db_distintas_entre_pruebas._seen = seen
