export interface EvaluateRequest {
  expression: string;
  angle_unit?: 'radians' | 'degrees';
  stack?: string[];
  expr_format?: 'infix' | 'postfix';
}

export interface EvaluateResponse {
  status: 'success';
  expression: string;
  result: string;
  stack?: string[];
}

export interface ErrorResponse {
  status: 'error';
  error_type: string;
  message: string;
}
