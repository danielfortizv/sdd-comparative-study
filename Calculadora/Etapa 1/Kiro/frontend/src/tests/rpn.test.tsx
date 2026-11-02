// RPN mode integration tests (tasks 62.3-62.5; Properties 32, 34, 35).
// Feature: web-calculator, Property 32: A backend result replaces the consumed operands with a single value
// Feature: web-calculator, Property 34: Keypad and keyboard produce identical RPN state changes
// Feature: web-calculator, Property 35: No arithmetic is ever computed on the client
// Validates: Requirements 39.2, 39.4, 39.5, 39.7, 39.8, 40.2, 40.3, 40.7, 41.5, 43.5
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Calculator } from '../components/Calculator';
import { server } from './setup';

const ENDPOINT = '*/api/v1/evaluate';

afterEach(cleanup);

/** Switch the calculator into RPN mode via the always-visible ModeToggle. */
async function enterRpnMode(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.click(screen.getByLabelText(/Calculator mode: standard/i));
  // Once in RPN mode the toggle advertises the RPN state.
  await screen.findByLabelText(/Calculator mode: RPN/i);
}

/** Read the visible value text for a given stack level (X/Y/Z/T). */
function stackValue(level: 'X' | 'Y' | 'Z' | 'T'): string {
  return screen.getByLabelText(new RegExp(`Stack level ${level}:`, 'i')).textContent ?? '';
}

describe('Calculator RPN mode (integration)', () => {
  it('toggling to RPN shows the stack display with all levels empty (39.1, 40.1, 40.6)', async () => {
    const user = userEvent.setup();
    render(<Calculator />);
    await enterRpnMode(user);

    expect(screen.getByLabelText('RPN stack')).toBeInTheDocument();
    for (const level of ['X', 'Y', 'Z', 'T'] as const) {
      expect(stackValue(level)).toBe('—');
    }
  });

  it('entering an operand and pressing Enter pushes it to X, rendering on the StackDisplay (39.4, 40.2)', async () => {
    const user = userEvent.setup();
    render(<Calculator />);
    await enterRpnMode(user);

    // Keypad entry: 4, 2 then Enter.
    await user.click(screen.getByLabelText('four'));
    await user.click(screen.getByLabelText('two'));
    expect(screen.getByLabelText('Expression').textContent).toContain('42');

    await user.click(screen.getByLabelText(/enter, push operand/i));
    expect(stackValue('X')).toContain('42');
    // Operand entry is cleared after a push.
    expect(screen.getByLabelText('Expression').textContent ?? '').toBe('');
  });

  it('a binary operator with two values builds infix, calls the backend, and SET_STACKs the result at X (Property 32; 39.5, 40.3)', async () => {
    const user = userEvent.setup();
    const seen: string[] = [];
    server.use(
      http.post(ENDPOINT, async ({ request }) => {
        const body = (await request.json()) as { expression: string };
        seen.push(body.expression);
        return HttpResponse.json({ result: '7' });
      }),
    );
    render(<Calculator />);
    await enterRpnMode(user);

    // Push 3 (Y), then 4 (X), then add.
    await user.click(screen.getByLabelText('three'));
    await user.click(screen.getByLabelText(/enter, push operand/i));
    await user.click(screen.getByLabelText('four'));
    await user.click(screen.getByLabelText(/enter, push operand/i));
    expect(stackValue('Y')).toContain('3');
    expect(stackValue('X')).toContain('4');

    await user.click(screen.getByLabelText('plus'));

    // Backend received the infix form "y op x" = "3 + 4"; the client computed nothing.
    await waitFor(() => expect(seen).toContain('3 + 4'));
    // The two consumed operands collapse to the single backend result at X.
    await waitFor(() => expect(stackValue('X')).toContain('7'));
    expect(stackValue('Y')).toBe('—');
  });

  it('an operator with fewer than two values is a no-op with an error and NO network call (39.7)', async () => {
    const user = userEvent.setup();
    const handler = vi.fn(() => HttpResponse.json({ result: 'should-not-happen' }));
    server.use(http.post(ENDPOINT, handler));
    render(<Calculator />);
    await enterRpnMode(user);

    // Only one value on the stack.
    await user.click(screen.getByLabelText('five'));
    await user.click(screen.getByLabelText(/enter, push operand/i));
    expect(stackValue('X')).toContain('5');

    await user.click(screen.getByLabelText('plus'));

    const errorRegion = screen.getByLabelText('Error');
    await waitFor(() => expect(errorRegion.textContent).toMatch(/insufficient values/i));
    // The stack is untouched and no backend request was issued.
    expect(stackValue('X')).toContain('5');
    expect(handler).not.toHaveBeenCalled();
  });

  it('a backend error during an RPN op retains the stack and shows no local result (Property 35; 40.7, 43.5)', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({ error: 'Division by zero is not allowed.' }, { status: 422 }),
      ),
    );
    render(<Calculator />);
    await enterRpnMode(user);

    // Stack: Y=6, X=0, then divide -> backend error.
    await user.click(screen.getByLabelText('six'));
    await user.click(screen.getByLabelText(/enter, push operand/i));
    await user.click(screen.getByLabelText('zero'));
    await user.click(screen.getByLabelText(/enter, push operand/i));
    await user.click(screen.getByLabelText('divide'));

    const errorRegion = screen.getByLabelText('Error');
    await waitFor(() => expect(errorRegion.textContent).toMatch(/division by zero/i));
    // The pre-operation stack is retained; no client-computed result replaces it.
    expect(stackValue('X')).toContain('0');
    expect(stackValue('Y')).toContain('6');
    expect(screen.getByLabelText('Result').textContent ?? '').toBe('');
  });

  it('keyboard and keypad drive identical RPN state changes (Property 34; 39.8)', async () => {
    const user = userEvent.setup();
    const seen: string[] = [];
    server.use(
      http.post(ENDPOINT, async ({ request }) => {
        const body = (await request.json()) as { expression: string };
        seen.push(body.expression);
        return HttpResponse.json({ result: '20' });
      }),
    );
    render(<Calculator />);
    await enterRpnMode(user);

    // Drive entirely from the physical keyboard: 5 Enter 4 Enter *.
    await user.keyboard('5');
    await user.keyboard('{Enter}');
    await user.keyboard('4');
    await user.keyboard('{Enter}');
    expect(stackValue('Y')).toContain('5');
    expect(stackValue('X')).toContain('4');

    await user.keyboard('*');
    await waitFor(() => expect(seen).toContain('5 * 4'));
    await waitFor(() => expect(stackValue('X')).toContain('20'));
  });
});
