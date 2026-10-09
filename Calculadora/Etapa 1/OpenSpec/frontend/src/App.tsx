import { useState, useEffect, useCallback, useRef } from "react";

function App() {
  const [expression, setExpression] = useState<string>("");
  const [result, setResult] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [isFinal, setIsFinal] = useState<boolean>(false);
  const [announcement, setAnnouncement] = useState<string>("");

  const displayRef = useRef<HTMLDivElement>(null);

  // Helper to call backend evaluation API
  const evaluateExpressionOnBackend = async (expr: string) => {
    try {
      const response = await fetch("http://localhost:8000/api/v1/evaluate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ expression: expr }),
      });

      const data = await response.json();
      if (response.ok) {
        return { success: true, result: data.result as string };
      } else {
        return { success: false, error: (data.detail || "Invalid expression") as string };
      }
    } catch (err) {
      return { success: false, error: "Server connection error" };
    }
  };

  // Perform final evaluation when '=' is pressed
  const handleEvaluate = useCallback(async () => {
    if (!expression.trim()) return;

    setAnnouncement("Evaluating expression...");
    const outcome = await evaluateExpressionOnBackend(expression);
    if (outcome.success && outcome.result !== undefined) {
      setResult(outcome.result);
      setError("");
      setIsFinal(true);
      setAnnouncement(`Calculation complete. Result is ${outcome.result}`);
    } else {
      const errMessage = outcome.error || "Evaluation error";
      setError(errMessage);
      setResult("");
      setIsFinal(true);
      setAnnouncement(`Calculation failed. Error: ${errMessage}`);
    }
  }, [expression]);

  // Perform live evaluation in the background as the user types
  useEffect(() => {
    if (isFinal) return;

    const trimmed = expression.trim();
    if (!trimmed) {
      setResult("");
      setError("");
      return;
    }

    // Do not show errors in live-preview mode for incomplete expressions
    const debounceTimer = setTimeout(async () => {
      const outcome = await evaluateExpressionOnBackend(trimmed);
      if (outcome.success && outcome.result !== undefined) {
        setResult(outcome.result);
        setError("");
      } else {
        // Clear result but do not show error on screen while typing
        setResult("");
      }
    }, 200);

    return () => clearTimeout(debounceTimer);
  }, [expression, isFinal]);

  // Handle calculator input (digits, decimals, operators, parentheses)
  const handleInput = useCallback((char: string) => {
    setError("");
    setExpression((prev) => {
      const isOperator = ["+", "-", "*", "/"].includes(char);
      
      if (isFinal) {
        setIsFinal(false);
        if (isOperator) {
          // Continue expression from the previous result
          const base = result || "0";
          return base + char;
        } else {
          // Restart with the new character
          return char;
        }
      }

      // Allow appending
      return prev + char;
    });
  }, [isFinal, result]);

  // Clear everything
  const handleClear = useCallback(() => {
    setExpression("");
    setResult("");
    setError("");
    setIsFinal(false);
    setAnnouncement("Display cleared");
  }, []);

  // Backspace last character
  const handleBackspace = useCallback(() => {
    setError("");
    if (isFinal) {
      handleClear();
      return;
    }
    setExpression((prev) => {
      if (prev.length <= 1) return "";
      return prev.slice(0, -1);
    });
    setAnnouncement("Deleted last character");
  }, [isFinal, handleClear]);

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
      } else if (key === "Enter" || key === "=") {
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
  }, [handleInput, handleEvaluate, handleBackspace, handleClear]);

  // Focus utility for layout screen accessibility
  useEffect(() => {
    if (displayRef.current) {
      displayRef.current.scrollTop = displayRef.current.scrollHeight;
    }
  }, [expression, result, error]);

  return (
    <div className="calculator-container">
      <main className="calculator-card">
        {/* Hidden screen reader live region for announcements */}
        <div aria-live="polite" className="sr-only">
          {announcement}
        </div>

        {/* Calculator Display Screen */}
        <div 
          className="calculator-screen" 
          ref={displayRef}
          role="region"
          aria-label="Calculator display screen"
        >
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
        </div>

        {/* Calculator Button Grid */}
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
          >
            (
          </button>
          <button 
            onClick={() => handleInput(")")} 
            className="btn btn-operator" 
            aria-label="Right parenthesis"
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
            aria-label="Equal/Evaluate"
            title="Evaluate (Enter)"
          >
            =
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
  );
}

export default App;
