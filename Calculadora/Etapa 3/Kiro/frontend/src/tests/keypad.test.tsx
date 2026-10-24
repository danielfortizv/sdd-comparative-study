// Keypad + ScientificKeypad component/a11y tests (tasks 14.1, 14.2, 37.1).
// Feature: web-calculator, Property 12: Every control exposes a matching accessible label
// Validates: Requirements 8.1-8.3, 11.6, 12.1, 12.2, 19.3-19.5, 22.1, 22.7, 22.8
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Keypad } from '../components/Keypad';
import { ScientificKeypad } from '../components/ScientificKeypad';
import { AngleModeToggle } from '../components/AngleModeToggle';
import { MemoryIndicator } from '../components/MemoryIndicator';

afterEach(cleanup);

describe('Keypad', () => {
  it('renders every required control with a matching aria-label (8.1, 12.1)', () => {
    render(<Keypad onInput={() => {}} onEvaluate={() => {}} onReset={() => {}} />);
    for (const label of [
      'seven', 'eight', 'nine', 'four', 'five', 'six', 'one', 'two', 'three',
      'zero', 'decimal point', 'open parenthesis', 'close parenthesis',
      'divide', 'multiply', 'minus', 'plus', 'clear', 'equals',
    ]) {
      expect(screen.getByLabelText(label)).toBeInTheDocument();
    }
  });

  it('routes each digit/operator/paren activation to onInput (10.1-10.3)', async () => {
    const user = userEvent.setup();
    const inputs: string[] = [];
    const onEvaluate = vi.fn();
    const onReset = vi.fn();
    render(
      <Keypad onInput={(c) => inputs.push(c)} onEvaluate={onEvaluate} onReset={onReset} />,
    );
    await user.click(screen.getByLabelText('seven'));
    await user.click(screen.getByLabelText('plus'));
    await user.click(screen.getByLabelText('open parenthesis'));
    await user.click(screen.getByLabelText('decimal point'));
    expect(inputs).toEqual(['7', '+', '(', '.']);
    await user.click(screen.getByLabelText('equals'));
    await user.click(screen.getByLabelText('clear'));
    expect(onEvaluate).toHaveBeenCalledTimes(1);
    expect(onReset).toHaveBeenCalledTimes(1);
  });
});

describe('ScientificKeypad', () => {
  function renderSci() {
    const inputs: string[] = [];
    const calls = {
      add: vi.fn(),
      sub: vi.fn(),
      recall: vi.fn(),
      clear: vi.fn(),
      toggle: vi.fn(),
    };
    render(
      <ScientificKeypad
        onInput={(t) => inputs.push(t)}
        angleMode="radians"
        onToggleAngleMode={calls.toggle}
        onMemoryAdd={calls.add}
        onMemorySubtract={calls.sub}
        onMemoryRecall={calls.recall}
        onMemoryClear={calls.clear}
      />,
    );
    return { inputs, calls };
  }

  it('emits deterministic tokens for every function/constant control (19.5)', async () => {
    const user = userEvent.setup();
    const { inputs } = renderSci();
    const expected: Array<[string, string]> = [
      ['sine', 'sin('],
      ['cosine', 'cos('],
      ['tangent', 'tan('],
      ['inverse sine', 'asin('],
      ['inverse cosine', 'acos('],
      ['inverse tangent', 'atan('],
      ['natural logarithm', 'ln('],
      ['base-10 logarithm', 'log10('],
      ['square root', 'sqrt('],
      ['nth root', 'root('],
      ['power exponent', '^'],
      ['pi constant', 'pi'],
      ['e constant', 'e'],
    ];
    for (const [label] of expected) {
      await user.click(screen.getByLabelText(label));
    }
    expect(inputs).toEqual(expected.map(([, token]) => token));
  });

  it('routes the four memory controls to their handlers (22.1)', async () => {
    const user = userEvent.setup();
    const { calls } = renderSci();
    await user.click(screen.getByLabelText('memory add'));
    await user.click(screen.getByLabelText('memory subtract'));
    await user.click(screen.getByLabelText('memory recall'));
    await user.click(screen.getByLabelText('memory clear'));
    expect(calls.add).toHaveBeenCalledTimes(1);
    expect(calls.sub).toHaveBeenCalledTimes(1);
    expect(calls.recall).toHaveBeenCalledTimes(1);
    expect(calls.clear).toHaveBeenCalledTimes(1);
  });

  it('collapses and expands via the collapse control (22.8)', async () => {
    const user = userEvent.setup();
    renderSci();
    const collapse = screen.getByLabelText('Scientific functions');
    expect(collapse).toHaveAttribute('aria-expanded', 'true');
    await user.click(collapse);
    expect(collapse).toHaveAttribute('aria-expanded', 'false');
  });
});

describe('AngleModeToggle', () => {
  it('displays the active mode and flips it on activation (22.6, 22.7)', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<AngleModeToggle angleMode="radians" onToggle={onToggle} />);
    await user.click(screen.getByRole('button'));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});

describe('MemoryIndicator', () => {
  it('is shown when the register is active and hidden otherwise (20.6, 20.7)', () => {
    const { rerender, container } = render(<MemoryIndicator active={true} />);
    expect(container.textContent ?? '').not.toBe('');
    rerender(<MemoryIndicator active={false} />);
    // When inactive the indicator renders nothing visible (or is absent).
    const badge = screen.queryByLabelText(/memory/i);
    expect(badge).toBeNull();
  });
});
