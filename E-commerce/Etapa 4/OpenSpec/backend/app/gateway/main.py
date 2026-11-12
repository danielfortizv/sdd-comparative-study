import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="API Gateway",
    description="HTTP reverse proxy routing traffic to backend microservices.",
    version="4.0.0"
)

# Configure CORS to preserve the exact interface behavior
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES = {
    "identity": os.getenv("IDENTITY_SERVICE_URL", "http://127.0.0.1:18001"),
    "commerce": os.getenv("COMMERCE_SERVICE_URL", "http://127.0.0.1:18002"),
    "reviews": os.getenv("REVIEWS_SERVICE_URL", "http://127.0.0.1:18003")
}

def resolve_target_url(request: Request) -> str:
    path = request.url.path
    method = request.method

    # Authentication routes
    if path.startswith("/api/auth"):
        return f"{SERVICES['identity']}{path}"

    # Reviews submission goes to reviews microservice
    if path.startswith("/api/products/") and path.endswith("/reviews") and method == "POST":
        return f"{SERVICES['reviews']}{path}"

    # Approved reviews lists go to commerce microservice (reviews projection)
    if path.startswith("/api/products/") and path.endswith("/reviews") and method == "GET":
        return f"{SERVICES['commerce']}{path}"

    # General catalog / products endpoints go to commerce
    if path.startswith("/api/products"):
        return f"{SERVICES['commerce']}{path}"

    # Moderation routes go to reviews
    if path.startswith("/api/moderation"):
        return f"{SERVICES['reviews']}{path}"

    return None

@app.get("/health", status_code=status.HTTP_200_OK)
async def gateway_health():
    """Aggregated health status check."""
    status_report = {"status": "healthy", "services": {}}
    async with httpx.AsyncClient() as client:
        for name, base_url in SERVICES.items():
            try:
                res = await client.get(f"{base_url}/health", timeout=1.0)
                status_report["services"][name] = res.json() if res.status_code == 200 else "unhealthy"
            except Exception:
                status_report["services"][name] = "unreachable"
    return status_report

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def reverse_proxy(request: Request, path_name: str):
    target_url = resolve_target_url(request)
    if not target_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route not found in Gateway: {request.method} {request.url.path}"
        )

    # Forward query params
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Read body
    body = await request.body()

    # Clean and forward headers
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    async with httpx.AsyncClient() as client:
        try:
            proxy_response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                timeout=10.0
            )
            
            # Return response
            return Response(
                content=proxy_response.content,
                status_code=proxy_response.status_code,
                headers=dict(proxy_response.headers)
            )
        except httpx.RequestError as exc:
            print(f"Gateway request error to {target_url}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"API Gateway failed to contact backing service at {target_url}."
            )

if __name__ == "__main__":
    uvicorn.run("app.gateway.main:app", host=os.getenv("GATEWAY_HOST", "127.0.0.1"), port=int(os.getenv("GATEWAY_PORT", 18000)))
