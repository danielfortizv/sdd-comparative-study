import { useState, useEffect, useCallback, useRef } from "react";

interface HistoryItem {
  expression: string;
  result: string;
}

function App() {
  const [expression, setExpression] = useState<string>("");
  const [result, setResult] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [isFinal, setIsFinal] = useState<boolean>(false);
  const [announcement, setAnnouncement] = useState<string>("");

  // Legacy Stage 2 states
  const [memory, setMemory] = useState<number>(0);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [angleUnit, setAngleUnit] = useState<string>("radians"); // "radians" or "degrees"
  const [showScientific, setShowScientific] = useState<boolean>(false);
  const [showHistory, setShowHistory] = useState<boolean>(false);

  // New Stage 4 states for RPN
  const [calculatorMode, setCalculatorMode] = useState<"standard" | "rpn">("standard");
  const [rpnStack, setRpnStack] = useState<string[]>([]);

  const displayRef = useRef<HTMLDivElement>(null);

  // Helper to call backend evaluation API supporting standard and RPN payloads
  const evaluateExpressionOnBackend = async (
    expr: string,
    unit: string,
    mode: "standard" | "rpn" = "standard",
    stack: string[] = [],
    signal?: AbortSignal
  ) => {
    try {
      const response = await fetch("http://localhost:8000/api/v1/evaluate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          expression: expr,
          angle_unit: unit,
          mode,
          stack,
        }),
        signal,
      });

      const data = await response.json();
      if (response.ok) {
        return { success: true, result: data.result as string, stack: data.stack as string[] };
      } else {
        return { success: false, error: (data.detail || "Invalid expression") as string };
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        return { success: false, aborted: true };
      }
      return { success: false, error: "Server connection error" };
    }
  };

  // Perform final evaluation (Standard Mode) or push to stack (RPN Mode)
  const handleEvaluate = useCallback(async () => {
    if (calculatorMode === "rpn") {
      setError("");
      const valToPush = expression.trim() || (rpnStack.length > 0 ? rpnStack[rpnStack.length - 1] : "0");
      setRpnStack((prev) => [...prev, valToPush]);
      setExpression("");
      setResult(valToPush);
      setAnnouncement(`Pushed ${valToPush} onto stack`);
      return;
    }

    if (!expression.trim()) return;

    setAnnouncement("Evaluating expression...");
    const outcome = await evaluateExpressionOnBackend(expression, angleUnit, "standard", []);
    if (outcome.success && outcome.result !== undefined) {
      setResult(outcome.result);
      setError("");
      setIsFinal(true);
      setAnnouncement(`Calculation complete. Result is ${outcome.result}`);
      
      // Save to calculation history list
      setHistory((prev) => [
        { expression: expression, result: outcome.result },
        ...prev
      ]);
    } else {
      const errMessage = outcome.error || "Evaluation error";
      setError(errMessage);
      setResult("");
      setIsFinal(true);
      setAnnouncement(`Calculation failed. Error: ${errMessage}`);
    }
  }, [expression, angleUnit, calculatorMode, rpnStack]);

  // Perform live evaluation in the background as the user types (Standard Mode only)
  useEffect(() => {
    if (isFinal || calculatorMode === "rpn") return;

    const trimmed = expression.trim();
    if (!trimmed) {
      setResult("");
      setError("");
      return;
    }

    const controller = new AbortController();

    // Do not show errors in live-preview mode for incomplete expressions
    const debounceTimer = setTimeout(async () => {
      const outcome = await evaluateExpressionOnBackend(trimmed, angleUnit, "standard", [], controller.signal);
      if (outcome.aborted) return;
      if (outcome.success && outcome.result !== undefined) {
        setResult(outcome.result);
        setError("");
      } else {
        // Clear result but do not show error on screen while typing
        setResult("");
      }
    }, 200);

    return () => {
      clearTimeout(debounceTimer);
      controller.abort();
    };
  }, [expression, isFinal, angleUnit, calculatorMode]);

  // Handle calculator input (digits, decimals, operators, parentheses, functions)
  const handleInput = useCallback(async (char: string) => {
    setError("");

    // RPN Mode Input Handling
    if (calculatorMode === "rpn") {
      const isDigit = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."].includes(char);
      
      if (isDigit) {
        setExpression((prev) => {
          // Prevent double decimal points in the typing buffer
          if (char === "." && prev.includes(".")) return prev;
          return prev + char;
        });
        return;
      }

      // If user enters a constant ("pi" or "e"), push onto stack immediately
      if (char === "pi" || char === "e") {
        setAnnouncement(`Evaluating constant ${char}...`);
        const outcome = await evaluateExpressionOnBackend(char, angleUnit, "rpn", rpnStack);
        if (outcome.success && outcome.stack) {
          setRpnStack(outcome.stack);
          setExpression("");
          setError("");
          setAnnouncement(`Pushed ${char} onto stack`);
        } else {
          setError(outcome.error || "Evaluation error");
        }
        return;
      }

      // It's an operator or a function
      // Auto-enter: if there is something in the active typing buffer, push it first!
      let currentStack = [...rpnStack];
      if (expression.trim() !== "") {
        currentStack.push(expression.trim());
        setRpnStack(currentStack);
        setExpression("");
      }

      // Prepare operator token (strip any trailing parenthesis, e.g. "sin(" -> "sin")
      let opToken = char;
      if (opToken.endsWith("(")) {
        opToken = opToken.slice(0, -1);
      }

      setAnnouncement(`Evaluating ${opToken}...`);
      const outcome = await evaluateExpressionOnBackend(opToken, angleUnit, "rpn", currentStack);
      if (outcome.success && outcome.stack) {
        setRpnStack(outcome.stack);
        setResult(outcome.result || "0");
        setError("");
        setAnnouncement(`Evaluated ${opToken}. Result: ${outcome.result}`);
        
        // Save to calculation history list
        setHistory((prev) => [
          { expression: `${currentStack.join(" ")} ${opToken}`, result: outcome.result || "0" },
          ...prev
        ]);
      } else {
        const errMessage = outcome.error || "Evaluation error";
        setError(errMessage);
        setAnnouncement(`Operation failed: ${errMessage}`);
      }
      return;
    }

    // Standard/Algebraic Mode Input Handling
    setExpression((prev) => {
      const isOperator = ["+", "-", "*", "/", "**"].includes(char);
      
      if (isFinal) {
        setIsFinal(false);
        if (isOperator) {
          // Continue expression from the previous result
          const base = result || "0";
          return base + char;
        } else {
          // Restart with the new character/function
          return char;
        }
      }

      // Allow appending
      return prev + char;
    });
  }, [calculatorMode, rpnStack, expression, angleUnit, isFinal, result]);

  // Clear display or pop stack
  const handleClear = useCallback(() => {
    if (calculatorMode === "rpn") {
      if (expression !== "") {
        setExpression("");
        setAnnouncement("Input buffer cleared");
      } else {
        setRpnStack([]);
        setResult("");
        setError("");
        setAnnouncement("Stack cleared");
      }
      return;
    }

    setExpression("");
    setResult("");
    setError("");
    setIsFinal(false);
    setAnnouncement("Display cleared");
  }, [calculatorMode, expression]);

  // Backspace last character or pop top of stack
  const handleBackspace = useCallback(() => {
    setError("");

    if (calculatorMode === "rpn") {
      if (expression !== "") {
        setExpression((prev) => prev.slice(0, -1));
        setAnnouncement("Deleted last digit");
      } else {
        setRpnStack((prev) => {
          const nextStack = prev.slice(0, -1);
          setAnnouncement("Popped top of stack");
          return nextStack;
        });
      }
      return;
    }

    if (isFinal) {
      handleClear();
      return;
    }
    setExpression((prev) => {
      if (prev.length <= 1) return "";
      
      // Handle deletion of multicharacter words like "sin(", "cos(", etc.
      const words = ["sin(", "cos(", "tan(", "asin(", "acos(", "atan(", "sqrt(", "root(", "ln(", "log10("];
      for (const word of words) {
        if (prev.endsWith(word)) {
          return prev.slice(0, -word.length);
        }
      }
      
      // Also handle pi and e
      if (prev.endsWith("pi")) {
        return prev.slice(0, -2);
      }
      if (prev.endsWith("e")) {
        return prev.slice(0, -1);
      }
      
      return prev.slice(0, -1);
    });
    setAnnouncement("Deleted last character");
  }, [isFinal, handleClear, calculatorMode, expression]);

  // Memory Operations
  const handleMemoryAdd = useCallback(() => {
    const activeValStr = calculatorMode === "rpn" 
      ? (expression || rpnStack[rpnStack.length - 1] || "0") 
      : (result || expression || "0");
    const activeVal = parseFloat(activeValStr);

    if (!isNaN(activeVal)) {
      setMemory((prev) => {
        const nextVal = prev + activeVal;
        const rounded = parseFloat(nextVal.toFixed(15));
        setAnnouncement(`Added ${activeVal} to memory. Memory is now ${rounded}`);
        return rounded;
      });
    }
  }, [result, expression, calculatorMode, rpnStack]);

  const handleMemorySubtract = useCallback(() => {
    const activeValStr = calculatorMode === "rpn" 
      ? (expression || rpnStack[rpnStack.length - 1] || "0") 
      : (result || expression || "0");
    const activeVal = parseFloat(activeValStr);

    if (!isNaN(activeVal)) {
      setMemory((prev) => {
        const nextVal = prev - activeVal;
        const rounded = parseFloat(nextVal.toFixed(15));
        setAnnouncement(`Subtracted ${activeVal} from memory. Memory is now ${rounded}`);
        return rounded;
      });
    }
  }, [result, expression, calculatorMode, rpnStack]);

  const handleMemoryRecall = useCallback(() => {
    setError("");

    if (calculatorMode === "rpn") {
      const memoryStr = memory.toString();
      setRpnStack((prev) => [...prev, memoryStr]);
      setAnnouncement(`Recalled memory value onto stack: ${memory}`);
      return;
    }

    setExpression((prev) => {
      const memoryStr = memory.toString();
      if (isFinal) {
        setIsFinal(false);
        return memoryStr;
      }
      return prev + memoryStr;
    });
    setAnnouncement(`Recalled memory value: ${memory}`);
  }, [memory, isFinal, calculatorMode]);

  const handleMemoryClear = useCallback(() => {
    setMemory(0);
    setAnnouncement("Memory cleared");
  }, []);

  // History Operations
  const handleClearHistory = useCallback(() => {
    setHistory([]);
    setAnnouncement("Session calculation history cleared");
  }, []);

  const handleLoadHistoryExpression = useCallback((expr: string) => {
    if (calculatorMode === "rpn") {
      setExpression(expr);
      setError("");
      setAnnouncement(`Loaded expression from history: ${expr}`);
      return;
    }

    setExpression(expr);
    setResult("");
    setError("");
    setIsFinal(false);
    setAnnouncement(`Loaded expression from history: ${expr}`);
  }, [calculatorMode]);

  const handleLoadHistoryResult = useCallback((res: string) => {
    if (calculatorMode === "rpn") {
      setRpnStack((prev) => [...prev, res]);
      setError("");
      setAnnouncement(`Pushed history result onto stack: ${res}`);
      return;
    }

    setExpression(res);
    setResult("");
    setError("");
    setIsFinal(false);
    setAnnouncement(`Loaded result from history: ${res}`);
  }, [calculatorMode]);

  // Bind physical keyboard listeners
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = e.key;

      if (key >= "0" && key <= "9") {
        e.preventDefault();
        handleInput(key);
      } else if (["+", "-", "*", "/", ".", "(", ")"].includes(key)) {
        e.preventDefault();
        handleInput(key);
      } else if (key === "^") {
        e.preventDefault();
        handleInput("**");
      } else if (key === ",") {
        e.preventDefault();
        handleInput(",");
      } else if (key.toLowerCase() === "p") {
        e.preventDefault();
        handleInput("pi");
      } else if (key.toLowerCase() === "e" && !expression.endsWith("sin") && !expression.endsWith("cos") && !expression.endsWith("tan") && !expression.endsWith("ln") && !expression.endsWith("sqrt") && !expression.endsWith("root")) {
        e.preventDefault();
        handleInput("e");
      } else if (key === "Enter" || key === "=") {
        e.preventDefault();
        handleEvaluate();
      } else if (key === " " && calculatorMode === "rpn") {
        e.preventDefault();
        handleEvaluate();
      } else if (key === "Backspace") {
        e.preventDefault();
        handleBackspace();
      } else if (key === "Escape") {
        e.preventDefault();
        handleClear();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleInput, handleEvaluate, handleBackspace, handleClear, expression, calculatorMode]);

  // Scroll utility for screen display
  useEffect(() => {
    if (displayRef.current) {
      displayRef.current.scrollTop = displayRef.current.scrollHeight;
    }
  }, [expression, result, error, rpnStack, calculatorMode]);

  // Visual stack shift calculations for RPN Mode
  const showTypingBuffer = expression !== "";
  const xVal = showTypingBuffer ? expression : (rpnStack[rpnStack.length - 1] || "0");
  const yVal = showTypingBuffer ? (rpnStack[rpnStack.length - 1] || "0") : (rpnStack[rpnStack.length - 2] || "0");
  const zVal = showTypingBuffer ? (rpnStack[rpnStack.length - 2] || "0") : (rpnStack[rpnStack.length - 3] || "0");
  const tVal = showTypingBuffer ? (rpnStack[rpnStack.length - 3] || "0") : (rpnStack[rpnStack.length - 4] || "0");

  return (
    <div className="calculator-layout-wrapper">
      <div className="calculator-container">
        <main className="calculator-card">
          {/* Hidden screen reader live region */}
          <div aria-live="polite" className="sr-only">
            {announcement}
          </div>

          {/* Control Bar */}
          <div className="control-bar" role="toolbar" aria-label="Calculator controls">
            <button 
              onClick={() => setAngleUnit((prev) => prev === "radians" ? "degrees" : "radians")}
              className="btn-control-toggle"
              aria-label={`Angle unit. Currently: ${angleUnit}. Click to toggle.`}
            >
              {angleUnit.toUpperCase()}
            </button>

            {memory !== 0 && (
              <span className="memory-badge" aria-label={`Memory is active with value: ${memory}`}>
                M
              </span>
            )}

            {/* ALG / RPN Mode Toggle */}
            <button 
              onClick={() => {
                setCalculatorMode((prev) => {
                  const nextMode = prev === "standard" ? "rpn" : "standard";
                  setExpression("");
                  setResult("");
                  setError("");
                  setRpnStack([]);
                  setIsFinal(false);
                  setAnnouncement(`Switched to ${nextMode === "rpn" ? "RPN" : "Standard"} Mode`);
                  return nextMode;
                });
              }}
              className={`btn-control-toggle ${calculatorMode === "rpn" ? "active" : ""}`}
              aria-label={`Toggle calculator mode. Currently: ${calculatorMode === "rpn" ? "RPN" : "Standard"}. Click to switch.`}
            >
              {calculatorMode === "rpn" ? "RPN" : "ALG"}
            </button>

            <button 
              onClick={() => setShowScientific((prev) => !prev)}
              className={`btn-control-toggle ${showScientific ? "active" : ""}`}
              aria-label="Toggle scientific keys"
              aria-pressed={showScientific}
            >
              f(x)
            </button>

            <button 
              onClick={() => setShowHistory((prev) => !prev)}
              className={`btn-control-toggle ${showHistory ? "active" : ""}`}
              aria-label="Toggle history panel"
              aria-pressed={showHistory}
            >
              🕒
            </button>
          </div>

          {/* Calculator Display Screen */}
          <div 
            className="calculator-screen" 
            ref={displayRef}
            role="region"
            aria-label="Calculator display screen"
          >
            {calculatorMode === "rpn" ? (
              <div className="rpn-stack-display" aria-label="RPN Evaluation Stack">
                <div className="stack-level" aria-label={`Stack Level T: ${tVal}`}>
                  <span className="level-label">T:</span>
                  <span className="level-value">{tVal}</span>
                </div>
                <div className="stack-level" aria-label={`Stack Level Z: ${zVal}`}>
                  <span className="level-label">Z:</span>
                  <span className="level-value">{zVal}</span>
                </div>
                <div className="stack-level" aria-label={`Stack Level Y: ${yVal}`}>
                  <span className="level-label">Y:</span>
                  <span className="level-value">{yVal}</span>
                </div>
                <div className={`stack-level active-level ${error ? "error-text" : ""}`} aria-label={`Stack Level X: ${xVal}`}>
                  <span className="level-label">X:</span>
                  <span className="level-value">{xVal}</span>
                </div>
                {error && <div className="stack-error-line" role="alert">{error}</div>}
              </div>
            ) : (
              <>
                <div 
                  className="expression-line" 
                  aria-label={`Current expression: ${expression || "Empty"}`}
                >
                  {expression || "0"}
                </div>
                <div 
                  className={`result-line ${error ? "error-text" : ""}`}
                  aria-label={error ? `Error: ${error}` : `Result: ${result || "0"}`}
                >
                  {error ? error : (result || "0")}
                </div>
              </>
            )}
          </div>

          {/* Memory Row */}
          <div className="memory-bar" role="group" aria-label="Memory operations">
            <button onClick={handleMemoryClear} className="btn-mem" aria-label="Memory clear (MC)">MC</button>
            <button onClick={handleMemoryRecall} className="btn-mem" aria-label="Memory recall (MR)">MR</button>
            <button onClick={handleMemoryAdd} className="btn-mem" aria-label="Memory add (M+)">M+</button>
            <button onClick={handleMemorySubtract} className="btn-mem" aria-label="Memory subtract (M-)">M-</button>
          </div>

          {/* Scientific Keypad Grid */}
          {showScientific && (
            <div className="scientific-grid" aria-label="Scientific keys">
              <button onClick={() => handleInput("sin(")} className="btn btn-sci" aria-label="Sine">sin</button>
              <button onClick={() => handleInput("cos(")} className="btn btn-sci" aria-label="Cosine">cos</button>
              <button onClick={() => handleInput("tan(")} className="btn btn-sci" aria-label="Tangent">tan</button>
              <button onClick={() => handleInput("asin(")} className="btn btn-sci" aria-label="Arcsine">asin</button>
              <button onClick={() => handleInput("acos(")} className="btn btn-sci" aria-label="Arccosine">acos</button>
              <button onClick={() => handleInput("atan(")} className="btn btn-sci" aria-label="Arctangent">atan</button>

              <button onClick={() => handleInput("sqrt(")} className="btn btn-sci" aria-label="Square root">√</button>
              <button onClick={() => handleInput("root(")} className="btn btn-sci" aria-label="N-th root" title="root(base, degree)">root</button>
              <button onClick={() => handleInput("ln(")} className="btn btn-sci" aria-label="Natural logarithm">ln</button>
              <button onClick={() => handleInput("log10(")} className="btn btn-sci" aria-label="Base-10 logarithm">log</button>
              <button onClick={() => handleInput("pi")} className="btn btn-sci" aria-label="Pi constant" title="Pi (P)">π</button>
              <button onClick={() => handleInput("e")} className="btn btn-sci" aria-label="Euler constant" title="Euler's number (E)">e</button>

              <button onClick={() => handleInput("**")} className="btn btn-sci" aria-label="Power x raised to y" title="Power (Shift + 6)">x<sup>y</sup></button>
              <button onClick={() => handleInput("**2")} className="btn btn-sci" aria-label="Square x squared">x<sup>2</sup></button>
              <button onClick={() => handleInput("10**")} className="btn btn-sci" aria-label="10 raised to power of x">10<sup>x</sup></button>
              <button onClick={() => handleInput(",")} className="btn btn-sci" aria-label="Comma argument separator" title="Comma (,)">,</button>
            </div>
          )}

          {/* Calculator Basic Button Grid */}
          <div className="button-grid">
            <button 
              onClick={handleClear} 
              className="btn btn-control" 
              aria-label="Clear all"
              title="Clear (Escape)"
            >
              C
            </button>
            <button 
              onClick={() => handleInput("(")} 
              className="btn btn-operator" 
              aria-label="Left parenthesis"
              disabled={calculatorMode === "rpn"}
            >
              (
            </button>
            <button 
              onClick={() => handleInput(")")} 
              className="btn btn-operator" 
              aria-label="Right parenthesis"
              disabled={calculatorMode === "rpn"}
            >
              )
            </button>
            <button 
              onClick={handleBackspace} 
              className="btn btn-control" 
              aria-label="Backspace"
              title="Backspace"
            >
              ⌫
            </button>

            <button onClick={() => handleInput("7")} className="btn btn-num" aria-label="7">7</button>
            <button onClick={() => handleInput("8")} className="btn btn-num" aria-label="8">8</button>
            <button onClick={() => handleInput("9")} className="btn btn-num" aria-label="9">9</button>
            <button 
              onClick={() => handleInput("/")} 
              className="btn btn-operator" 
              aria-label="Divide"
            >
              /
            </button>

            <button onClick={() => handleInput("4")} className="btn btn-num" aria-label="4">4</button>
            <button onClick={() => handleInput("5")} className="btn btn-num" aria-label="5">5</button>
            <button onClick={() => handleInput("6")} className="btn btn-num" aria-label="6">6</button>
            <button 
              onClick={() => handleInput("*")} 
              className="btn btn-operator" 
              aria-label="Multiply"
            >
              *
            </button>

            <button onClick={() => handleInput("1")} className="btn btn-num" aria-label="1">1</button>
            <button onClick={() => handleInput("2")} className="btn btn-num" aria-label="2">2</button>
            <button onClick={() => handleInput("3")} className="btn btn-num" aria-label="3">3</button>
            <button 
              onClick={() => handleInput("-")} 
              className="btn btn-operator" 
              aria-label="Subtract"
            >
              -
            </button>

            <button onClick={() => handleInput("0")} className="btn btn-num" aria-label="0">0</button>
            <button onClick={() => handleInput(".")} className="btn btn-num" aria-label="Decimal point">.</button>
            <button 
              onClick={handleEvaluate} 
              className="btn btn-evaluate" 
              aria-label={calculatorMode === "rpn" ? "Push onto stack (ENT)" : "Equal/Evaluate"}
              title={calculatorMode === "rpn" ? "Push onto stack (Enter / Space)" : "Evaluate (Enter)"}
            >
              {calculatorMode === "rpn" ? "ENT" : "="}
            </button>
            <button 
              onClick={() => handleInput("+")} 
              className="btn btn-operator" 
              aria-label="Add"
            >
              +
            </button>
          </div>
        </main>
      </div>

      {/* Interactive History Drawer Panel */}
      {showHistory && (
        <aside className="history-panel" aria-label="Calculation history panel">
          <div className="history-header">
            <h3>Historial de Sesión</h3>
            <button onClick={() => setShowHistory(false)} className="btn-close-history" aria-label="Close history">×</button>
          </div>
          <div className="history-content">
            {history.length === 0 ? (
              <p className="no-history-text">No hay cálculos en esta sesión.</p>
            ) : (
              history.map((item, index) => (
                <div className="history-item" key={index} role="group" aria-label={`Calculation ${index + 1}`}>
                  <button 
                    onClick={() => handleLoadHistoryExpression(item.expression)}
                    className="history-expr-btn"
                    title="Cargar expresión"
                    aria-label={`Cargar expresión: ${item.expression}`}
                  >
                    {item.expression}
                  </button>
                  <div className="history-equals">=</div>
                  <button 
                    onClick={() => handleLoadHistoryResult(item.result)}
                    className="history-res-btn"
                    title="Cargar resultado"
                    aria-label={`Cargar resultado: ${item.result}`}
                  >
                    {item.result}
                  </button>
                </div>
              ))
            )}
          </div>
          {history.length > 0 && (
            <button onClick={handleClearHistory} className="btn-clear-history" aria-label="Limpiar todo el historial">
              Limpiar Historial
            </button>
          )}
        </aside>
      )}
    </div>
  );
}

export default App;
