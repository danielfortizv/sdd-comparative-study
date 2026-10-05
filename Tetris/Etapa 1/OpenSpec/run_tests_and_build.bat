@echo off
echo =========================================
echo Running Backend Tests...
echo =========================================
set PYTHONPATH=.
call backend\venv\Scripts\pytest backend -v
if %ERRORLEVEL% neq 0 (
    echo Backend tests failed!
    exit /b %ERRORLEVEL%
)

echo =========================================
echo Building Frontend...
echo =========================================
cd frontend
call npm run build
if %ERRORLEVEL% neq 0 (
    echo Frontend build failed!
    exit /b %ERRORLEVEL%
)
cd ..

echo =========================================
echo All Checks Passed Successfully!
echo =========================================
