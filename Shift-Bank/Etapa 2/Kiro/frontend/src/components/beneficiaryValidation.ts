// Validación de formato de beneficiario ACH (Requisitos 2.2, 2.3, 2.4; ACH-10, A05, A06).
// Replica en el cliente la validación de formato para dar feedback inmediato y bloquear el
// envío; la autoridad definitiva es el backend.

// Routing: exactamente 9 dígitos numéricos (Requisito 2.2; A05).
export function validateRouting(value: string): string | null {
  if (!/^\d{9}$/.test(value)) {
    return "El routing debe tener exactamente 9 dígitos.";
  }
  return null;
}

// Número de cuenta: entre 4 y 17 dígitos numéricos, inclusive (Requisito 2.3; A06).
export function validateAccountNumber(value: string): string | null {
  if (!/^\d{4,17}$/.test(value)) {
    return "El número de cuenta debe tener entre 4 y 17 dígitos.";
  }
  return null;
}
