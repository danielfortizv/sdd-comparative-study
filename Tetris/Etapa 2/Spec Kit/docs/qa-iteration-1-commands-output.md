# QA Iteration 1 Command Execution and Output Report

Date: 2026-10-20
Project: Tetris Stage 2 Spec Kit
Labels: `qa-iteration-1`

## Executed Commands and Verified Outputs

### 1. Backend Verification Test Suite & Coverage
**Command executed:**
```powershell
$env:PYTHONPATH="backend"; pytest --cov=backend/app --cov-report=xml:docs/coverage.xml --cov-report=term backend/tests
```

**Output:**
```
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
collected 35 items

backend\tests\integration\test_api_us1.py .......                        [ 20%]
backend\tests\integration\test_api_us2.py ....                           [ 31%]
backend\tests\integration\test_api_us3.py ..                             [ 37%]
backend\tests\unit\test_game_engine_us1.py ..........                    [ 65%]
backend\tests\unit\test_game_engine_us2.py .......                       [ 85%]
backend\tests\unit\test_game_engine_us3.py ..                            [ 91%]
backend\tests\unit\test_qa_iteration1.py ...                             [100%]

=============================== tests coverage ================================
Name                                  Stmts   Miss  Cover
---------------------------------------------------------
backend\app\__init__.py                   0      0   100%
backend\app\api\__init__.py               0      0   100%
backend\app\api\endpoints.py             27      2    93%
backend\app\main.py                      11      1    91%
backend\app\models\__init__.py            0      0   100%
backend\app\models\schemas.py            85     12    86%
backend\app\services\__init__.py          0      0   100%
backend\app\services\game_engine.py     113      4    96%
---------------------------------------------------------
TOTAL                                   236     19    92%
Coverage XML written to file docs/coverage.xml
======================= 35 passed, 2 warnings in 1.38s ========================
```

---

### 2. Frontend Verification Test Suite & Coverage
**Command executed:**
```powershell
npx vitest run --coverage
```

**Output:**
```
 RUN  v4.1.12 D:/KEVIN/UNIVERSIDAD/Trabajos/Proyecto/Caso 2-Tetris/Etapa 2/Spec Kit/frontend
      Coverage enabled with v8

 Test Files  3 passed (3)
      Tests  18 passed (18)
   Start at  08:39:57
   Duration  1.63s (transform 209ms, setup 0ms, import 1.58s, tests 289ms, environment 1.84s)

-------------------|---------|----------|---------|---------|-------------------
File               | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s 
-------------------|---------|----------|---------|---------|-------------------
All files          |   79.39 |    65.21 |   96.87 |   81.69 |                   
 src               |   53.84 |    52.77 |    87.5 |   54.05 |                   
  App.tsx          |   55.26 |    52.77 |    87.5 |   55.55 | 27-30,56-72       
  main.tsx         |       0 |      100 |     100 |       0 | 6                 
 src/components    |   80.64 |    59.09 |     100 |   79.31 |                   
  Board.tsx        |      76 |       50 |     100 |      75 | 46,48-52          
 src/hooks         |   89.47 |    75.43 |     100 |   94.25 |                   
  useGame.ts       |   89.47 |    75.43 |     100 |   94.25 | 32,61-62,80,95    
-------------------|---------|----------|---------|---------|-------------------

=============================== Coverage summary ===============================
Statements   : 79.39% ( 131/165 )
Branches     : 65.21% ( 75/115 )
Functions    : 96.87% ( 31/32 )
Lines        : 81.69% ( 125/153 )
```

---

### 3. Production Build Compilation
**Command executed:**
```powershell
npm run build
```

**Output:**
```
> tetris-frontend@0.1.0 build
> tsc && vite build

vite v6.4.4 building for production...
transforming...
✓ 31 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.61 kB │ gzip:  0.41 kB
dist/assets/index-Ba1Escvr.css    5.39 kB │ gzip:  1.42 kB
dist/assets/index-JfVi25L4.js   150.82 kB │ gzip: 48.48 kB
✓ built in 491ms
```

---

### 4. Dependency Security Audit
**Command executed:**
```powershell
npm audit
```

**Output:**
```
found 0 vulnerabilities
```
