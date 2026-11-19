"""Abstracción de reloj inyectable (Etapa 2, Tarea 9).

Proporciona manejo de tiempo UTC determinista y testable para la funcionalidad futura de la
Etapa 2 (liquidación ACH y ejecución de pagos recurrentes), sin implementar aún esa
funcionalidad ni el scheduler, y sin alterar el comportamiento MFA heredado.

Diseño (DD-3):
- `Clock` es un protocolo mínimo con `now_utc() -> datetime` (datetime timezone-aware en UTC).
- `SystemClock` usa el reloj real del sistema en la ejecución normal de la aplicación.
- `ManualClock` permite fijar y avanzar el tiempo de forma determinista en las pruebas, sin
  `sleep()` ni temporizadores reales, y sin estado global mutable (cada instancia es local).
- Helpers `iso` / `parse_iso` compatibles con la convención de persistencia heredada
  (`%Y-%m-%dT%H:%M:%SZ`, UTC con sufijo Z), para reutilizarlos en ACH/recurrentes.

No se usan librerías externas de mocking de tiempo ni dependencias nuevas.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

# Formato ISO-8601 UTC heredado de la Etapa 1 (segundos, sufijo Z). Debe coincidir con el usado
# por `app.service` para que los timestamps persistidos sean interoperables.
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@runtime_checkable
class Clock(Protocol):
    """Fuente de tiempo. Devuelve siempre un datetime timezone-aware en UTC."""

    def now_utc(self) -> datetime:  # pragma: no cover - protocolo
        ...


class SystemClock:
    """Reloj real del sistema (uso en producción)."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


class ManualClock:
    """Reloj controlado para pruebas deterministas.

    Se inicializa con un instante fijo (UTC) y solo avanza cuando se le indica explícitamente
    con `advance(...)`. Lecturas repetidas devuelven el mismo valor (no avanza solo).
    """

    def __init__(self, start: datetime | None = None) -> None:
        base = start if start is not None else datetime(2026, 1, 1, tzinfo=timezone.utc)
        self._now = _ensure_utc(base)

    def now_utc(self) -> datetime:
        return self._now

    def advance(self, *, seconds: int = 0, minutes: int = 0, hours: int = 0,
                days: int = 0) -> datetime:
        """Avanza el tiempo simulado y devuelve el nuevo instante."""
        self._now = self._now + timedelta(
            seconds=seconds, minutes=minutes, hours=hours, days=days
        )
        return self._now

    def set(self, moment: datetime) -> None:
        """Fija el tiempo simulado a un instante concreto (UTC)."""
        self._now = _ensure_utc(moment)


# Reloj por defecto de la aplicación (sistema). Las operaciones de la Etapa 2 recibirán un
# `Clock` por inyección; en producción se usa esta instancia.
system_clock: Clock = SystemClock()


def _ensure_utc(dt: datetime) -> datetime:
    """Normaliza un datetime a UTC timezone-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    """Formatea un datetime como cadena ISO-8601 UTC heredada (`...Z`)."""
    return _ensure_utc(dt).strftime(ISO_FORMAT)


def parse_iso(text: str) -> datetime:
    """Parsea una cadena ISO-8601 UTC heredada a datetime timezone-aware en UTC."""
    return datetime.strptime(text, ISO_FORMAT).replace(tzinfo=timezone.utc)


def utc_day_bounds(moment: datetime) -> tuple[datetime, datetime]:
    """Devuelve el inicio (inclusive) y fin (exclusivo) del día UTC que contiene `moment`.

    Útil para la futura agregación diaria de límites (día UTC documentado, LIM-06). No impone
    aún ninguna regla de límites; es solo un helper de fronteras de día.
    """
    m = _ensure_utc(moment)
    start = m.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end
