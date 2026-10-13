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
