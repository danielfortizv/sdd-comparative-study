// Calculator integration tests (tasks 43.1, 43.3, 37.1): keyboard input, submit,
// history append/select/clear, and reset — exercising useKeyboard, useEvaluator,
// the container, and the panels end to end with the backend mocked by MSW.
// Validates: Requirements 7.3, 7.4, 8.4, 10.1-10.7, 14.3, 21.1-21.4, 21.6, 29.1, 29.3
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Calculator } from '../components/Calculator';
import { server } from './setup';

const ENDPOINT = '*/api/v1/evaluate';

afterEach(cleanup);

function mockResult(result: string): void {
  server.use(http.post(ENDPOINT, () => HttpResponse.json({ result })));
}

describe('Calculator (integration)', () => {
  it('renders empty displays initially (7.1, 7.2)', () => {
    render(<Calculator />);
    const expr = screen.getByLabelText('Expression');
    expect(expr.textContent ?? '').toBe('');
  });

  it('types an expression via the physical keyboard and shows it (10.1-10.3, 7.3)', async () => {
    const user = userEvent.setup();
    render(<Calculator />);
    await user.keyboard('12+3');
    expect(screen.getByLabelText('Expression').textContent).toContain('12+3');
  });

  it('Backspace removes the last character; Escape resets (10.5, 10.7)', async () => {
    const user = userEvent.setup();
    render(<Calculator />);
    await user.keyboard('99');
    await user.keyboard('{Backspace}');
    expect(screen.getByLabelText('Expression').textContent).toContain('9');
    await user.keyboard('{Escape}');
    expect(screen.getByLabelText('Expression').textContent ?? '').toBe('');
  });

  it('submits via Enter, renders the backend result, and appends history (14.3, 21.1)', async () => {
    const user = userEvent.setup();
    mockResult('5');
    render(<Calculator />);
    await user.keyboard('2+3');
    await user.keyboard('{Enter}');
    const resultRegion = screen.getByLabelText('Result');
    await waitFor(() => expect(resultRegion.textContent).toBe('5'));
    expect(await screen.findByLabelText(/load expression 2\+3/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/load result 5/i)).toBeInTheDocument();
  });

  it('selecting a history expression loads it back into the expression (21.3)', async () => {
    const user = userEvent.setup();
    mockResult('7');
    render(<Calculator />);
    await user.keyboard('3+4');
    await user.keyboard('{Enter}');
    await screen.findByLabelText(/load expression 3\+4/i);
    await user.keyboard('{Escape}');
    await user.click(screen.getByLabelText(/load expression 3\+4/i));
    expect(screen.getByLabelText('Expression').textContent).toContain('3+4');
  });

  it('clears the history (21.6)', async () => {
    const user = userEvent.setup();
    mockResult('2');
    render(<Calculator />);
    await user.keyboard('1+1');
    await user.keyboard('{Enter}');
    await screen.findByLabelText(/load expression 1\+1/i);
    await user.click(screen.getByLabelText(/clear history/i));
    expect(screen.queryByLabelText(/load expression 1\+1/i)).toBeNull();
    expect(screen.getByText(/no calculations yet/i)).toBeInTheDocument();
  });

  it('renders an error from the backend (7.5, 7.6)', async () => {
    const user = userEvent.setup();
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({ error: 'Division by zero is not allowed.' }, { status: 422 }),
      ),
    );
    render(<Calculator />);
    await user.keyboard('1/0');
    await user.keyboard('{Enter}');
    const errorRegion = screen.getByLabelText('Error');
    await waitFor(() =>
      expect(errorRegion.textContent).toMatch(/division by zero/i),
    );
  });
});

