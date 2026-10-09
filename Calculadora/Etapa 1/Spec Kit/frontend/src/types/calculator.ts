export interface CalculationRequest {
  expression: string;
}

export interface CalculationResponse {
  expression: string;
  result: string;
}

export interface ErrorResponse {
  error: string;
  details: string;
}
