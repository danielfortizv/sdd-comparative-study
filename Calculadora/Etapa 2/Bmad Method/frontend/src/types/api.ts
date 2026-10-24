export interface EvaluateRequest {
  expression: string;
  angle_unit?: 'radians' | 'degrees';
}

export interface EvaluateResponse {
  status: 'success';
  expression: string;
  result: string;
}

export interface ErrorResponse {
  status: 'error';
  error_type: string;
  message: string;
}
