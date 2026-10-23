from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from backend.app.routers import evaluate

app = FastAPI(
    title="Basic Web Calculator API",
    description="A secure, stateless, arbitrary-precision mathematical expression parsing and evaluation REST API.",
    version="1.0.0"
)

# Enable CORS for the React frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint for health check and monitoring
@app.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "healthy",
        "service": "calculator-api",
        "version": "1.0.0"
    }

# Exception handler for Pydantic validation errors (non-string, missing field payloads)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Grab the first error message or construct standard message
    errors = exc.errors()
    if errors:
        err_detail = errors[0]
        err_loc = err_detail.get("loc", [])
        err_msg = err_detail.get("msg", "Validation error")
        formatted_loc = '.'.join(map(str, err_loc))
    else:
        formatted_loc = "payload"
        err_msg = "Unknown validation error"
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "error_type": "request_validation_error",
            "message": f"Error: Request validation failed at field '{formatted_loc}': {err_msg}"
        }
    )

app.include_router(evaluate.router)
