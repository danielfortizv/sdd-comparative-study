Write-Host "Running backend tests with pytest..." -ForegroundColor Cyan
$env:PYTHONPATH="."
pytest backend/tests

if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend tests failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Running frontend tests with vitest..." -ForegroundColor Cyan
cd frontend
npm run test

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend tests failed!" -ForegroundColor Red
    exit 1
}

Write-Host "All tests passed successfully!" -ForegroundColor Green
