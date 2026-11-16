"""Constantes de configuración de Shift Bank (Etapa 1).

Centraliza los valores de negocio y de infraestructura usados por el backend:
ruta de la base de datos, umbral de MFA, código MFA fijo y TTL de la ventana de MFA.
Todos los valores reflejan el diseño y los requisitos aprobados; no se añaden ajustes
fuera del alcance de la Etapa 1.
"""

from decimal import Decimal
from pathlib import Path

# Ruta del archivo SQLite. Se ubica junto al paquete backend.
DB_PATH: Path = Path(__file__).resolve().parent.parent / "shift_bank.db"

# Umbral de MFA: montos >= a este valor requieren MFA (Requisito 6.2).
MFA_THRESHOLD: Decimal = Decimal("1000000")

# Código MFA simulado fijo (Requisito 7.1).
MFA_CODE: str = "123456"

# Ventana de validez de una transferencia PENDING_MFA, en segundos (5 minutos, Requisito 8.1).
MFA_TTL_SECONDS: int = 5 * 60

# Nombres amigables por tipo de cuenta (Requisito 2.1).
ACCOUNT_DISPLAY_NAMES: dict[str, str] = {
    "checking": "Checking",
    "savings": "Savings",
}

# --- Etapa 2 ------------------------------------------------------------------

# Límites dinámicos por defecto en centavos (decisión E2-KIRO-D01).
# Por transferencia: 5.000.000,00 COP = 500.000.000 centavos.
# Diario acumulado: 10.000.000,00 COP = 1.000.000.000 centavos.
DEFAULT_PER_TRANSFER_LIMIT_CENTS: int = 500_000_000
DEFAULT_DAILY_LIMIT_CENTS: int = 1_000_000_000

# Intervalos de recurrencia en días (REC-02, Req. 8.2): diaria=1, semanal=7, mensual=30.
# "mensual" = 30 días fijos (no un mes calendario), por decisión de diseño.
RECURRENCE_INTERVAL_DAYS: dict[str, int] = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
}

# Intervalo de "despertar" del scheduler de fondo, en segundos (DD-2/DD-3, Req. 10.1/10.2,
# Tarea 32). Cada tick la única tarea asyncio invoca `recurring_service.process_due(now)` y el
# barrido de settlement ACH. Es solo la cadencia del disparador; la elegibilidad real de cada
# ocurrencia/liquidación la decide `now` (reloj inyectable), no este valor.
SCHEDULER_TICK_SECONDS: int = 1
