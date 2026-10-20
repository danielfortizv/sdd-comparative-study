export interface CalculationRequest {
  expression: string;
  angle_unit?: 'radians' | 'degrees';
}

export interface CalculationResponse {
  expression: string;
  result: string;
}

export interface ErrorResponse {
  error: string;
  details: string;
}

export interface HistoryItem {
  id: string;
  expression: string;
  result: string;
}
