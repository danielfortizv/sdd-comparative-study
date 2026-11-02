// Typed API client tests (tasks 9.3 / 37.1; Property 13 + transport handling).
// Feature: web-calculator, Property 13: Non-conforming responses are treated as errors
// Validates: Requirements 13.4, 13.5, 14.3, 14.4, 24.1, 24.7
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { evaluateExpression } from '../api/client';
import { server } from './setup';

const ENDPOINT = '*/api/v1/evaluate';

describe('evaluateExpression', () => {
  it('returns ok:true with the backend result on success', async () => {
    server.use(
      http.post(ENDPOINT, () => HttpResponse.json({ result: '8.25' })),
    );
    const outcome = await evaluateExpression('1+2');
    expect(outcome).toEqual({ ok: true, result: '8.25' });
  });

  it('sends the selected angle_mode in the request body (24.1, 24.7)', async () => {
    let captured: unknown = null;
    server.use(
      http.post(ENDPOINT, async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json({ result: '1' });
      }),
    );
    await evaluateExpression('sin(90)', 'degrees');
    expect(captured).toEqual({ expression: 'sin(90)', angle_mode: 'degrees' });
  });

  it('defaults angle_mode to radians when omitted (24.3)', async () => {
    let captured: Record<string, unknown> = {};
    server.use(
      http.post(ENDPOINT, async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ result: '0' });
      }),
    );
    await evaluateExpression('sin(0)');
    expect(captured.angle_mode).toBe('radians');
  });

  it('returns ok:false with the error on a 4xx error response', async () => {
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({ error: 'Division by zero is not allowed.' }, { status: 422 }),
      ),
    );
    const outcome = await evaluateExpression('1/0');
    expect(outcome).toEqual({
      ok: false,
      error: 'Division by zero is not allowed.',
    });
  });

  it('treats a non-conforming payload as an error (Property 13)', async () => {
    server.use(
      http.post(ENDPOINT, () => HttpResponse.json({ unexpected: true })),
    );
    const outcome = await evaluateExpression('1+1');
    expect(outcome.ok).toBe(false);
    if (!outcome.ok) {
      expect(outcome.error).toMatch(/unexpected response/i);
    }
  });

  it('treats a payload with both result and error as non-conforming (5.5)', async () => {
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({ result: '5', error: 'both' }),
      ),
    );
    const outcome = await evaluateExpression('2+3');
    expect(outcome.ok).toBe(false);
  });

  it('surfaces a service-unavailable error on transport failure (14.4)', async () => {
    server.use(http.post(ENDPOINT, () => HttpResponse.error()));
    const outcome = await evaluateExpression('1+1');
    expect(outcome.ok).toBe(false);
    if (!outcome.ok) {
      expect(outcome.error).toMatch(/unavailable/i);
    }
  });

  it('treats a non-JSON body as an error (13.5)', async () => {
    server.use(
      http.post(ENDPOINT, () =>
        new HttpResponse('not json', { headers: { 'Content-Type': 'text/plain' } }),
      ),
    );
    const outcome = await evaluateExpression('1+1');
    expect(outcome.ok).toBe(false);
  });
});

