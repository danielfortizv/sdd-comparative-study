import { CalculationRequest, CalculationResponse, ErrorResponse } from '../types/calculator';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export async function evaluateExpression(expression: string): Promise<CalculationResponse> {
  const requestPayload: CalculationRequest = { expression };

  try {
    const response = await fetch(`${API_BASE_URL}/evaluate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestPayload),
    });

    if (!response.ok) {
      const errorData: ErrorResponse = await response.json();
      throw new Error(errorData.details || errorData.error || 'Server error occurred during evaluation.');
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Network error or unexpected system failure.');
  }
}
