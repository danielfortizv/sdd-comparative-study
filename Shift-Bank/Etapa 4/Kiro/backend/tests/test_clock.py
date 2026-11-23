"""Pruebas de la abstracción de reloj inyectable (Etapa 2, Tarea 9).

Verifican la utilidad de tiempo compartida: reloj real, reloj manual determinista, avance sin
espera real, estabilidad de lecturas, fronteras de día UTC y compatibilidad de formato/parseo
con la convención de persistencia heredada. NO prueban ejecución de recurrentes ni settlement
(tareas posteriores).

_Requisitos: 10.5, 4.2_ · _Diseño: DD-3_
"""

from datetime import datetime, timezone

import app.clock as clock


def test_reloj_del_sistema_devuelve_utc_valido():
    """SystemClock.now_utc() devuelve un datetime timezone-aware en UTC."""
    now = clock.SystemClock().now_utc()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
    assert now.utcoffset().total_seconds() == 0  # UTC


def test_reloj_manual_devuelve_el_instante_fijado():
    """ManualClock devuelve exactamente el instante con el que se inicializa."""
    start = datetime(2026, 11, 16, 10, 0, 0, tzinfo=timezone.utc)
    c = clock.ManualClock(start)
    assert c.now_utc() == start


def test_avance_determinista():
    """advance() mueve el tiempo de forma determinista y reproducible."""
    c = clock.ManualClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    c.advance(seconds=301)
    assert c.now_utc() == datetime(2026, 1, 1, 0, 5, 1, tzinfo=timezone.utc)
    c.advance(days=7)
    assert c.now_utc() == datetime(2026, 1, 8, 0, 5, 1, tzinfo=timezone.utc)


def test_lecturas_repetidas_no_avanzan_el_reloj_manual():
    """Leer now_utc() varias veces no altera el tiempo simulado."""
    c = clock.ManualClock(datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc))
    primera = c.now_utc()
    for _ in range(5):
        assert c.now_utc() == primera


def test_set_fija_instante():
    """set() reposiciona el reloj a un instante concreto (normalizado a UTC)."""
    c = clock.ManualClock()
    target = datetime(2027, 3, 1, 9, 30, 0, tzinfo=timezone.utc)
    c.set(target)
    assert c.now_utc() == target


def test_fronteras_de_dia_utc_consistentes():
    """utc_day_bounds devuelve [00:00Z, 24:00Z) del día que contiene el instante."""
    m = datetime(2026, 11, 16, 15, 45, 30, tzinfo=timezone.utc)
    start, end = clock.utc_day_bounds(m)
    assert start == datetime(2026, 11, 16, 0, 0, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 11, 17, 0, 0, 0, tzinfo=timezone.utc)
    # El instante cae dentro del intervalo [start, end).
    assert start <= m < end


def test_formato_y_parseo_compatibles_con_persistencia_heredada():
    """iso()/parse_iso() usan el formato heredado `%Y-%m-%dT%H:%M:%SZ` y son inversos."""
    dt = datetime(2026, 11, 16, 15, 4, 0, tzinfo=timezone.utc)
    s = clock.iso(dt)
    assert s == "2026-11-16T15:04:00Z"
    assert s.endswith("Z")
    back = clock.parse_iso(s)
    assert back == dt


def test_iso_normaliza_naive_a_utc():
    """iso() normaliza un datetime naive asumiéndolo UTC (no lanza)."""
    naive = datetime(2026, 11, 16, 0, 0, 0)
    assert clock.iso(naive) == "2026-11-16T00:00:00Z"


def test_control_de_tiempo_sin_sleep():
    """Demostración: se puede simular el paso de >5 min sin sleep() real.

    Esto habilita a las futuras pruebas de settlement/recurrentes a controlar el tiempo de forma
    determinista (sin esperar en tiempo real), usando un ManualClock inyectado.
    """
    c = clock.ManualClock(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    antes = c.now_utc()
    c.advance(minutes=5, seconds=1)  # supera una ventana de 5 minutos
    assert (c.now_utc() - antes).total_seconds() == 301


def test_system_clock_es_el_default_de_la_app():
    """La app expone una instancia de reloj de sistema por defecto para producción."""
    assert isinstance(clock.system_clock, clock.Clock)
    assert isinstance(clock.system_clock, clock.SystemClock)
