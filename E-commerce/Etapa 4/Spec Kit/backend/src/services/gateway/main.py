import os
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(title="API Gateway", version="1.0.0")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IDENTITY_SERVICE_URL = os.environ.get("IDENTITY_SERVICE_URL", "http://127.0.0.1:18601")
COMMERCE_SERVICE_URL = os.environ.get("COMMERCE_SERVICE_URL", "http://127.0.0.1:18602")
REVIEWS_SERVICE_URL = os.environ.get("REVIEWS_SERVICE_URL", "http://127.0.0.1:18603")


# Global exception handler middleware for standard, non-sensitive errors
@app.middleware("http")
async def non_sensitive_error_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        print(f"Gateway error occurred: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An internal server error occurred. Please try again later."},
        )


async def proxy_request(service_url: str, path: str, request: Request):
    """Cleanly proxies the incoming request to the target downstream microservice."""
    url = f"{service_url}{path}"
    
    # Extract original headers, dropping Host header to avoid routing loops
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    
    # Extract query params
    params = dict(request.query_params)
    
    # Extract body
    body = await request.body()
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=params,
                content=body,
                timeout=10.0,
            )
            
            # Forward the exact status and content back to client
            # Parse JSON safely if content type is json
            is_json = resp.headers.get("content-type", "").startswith("application/json")
            content = resp.json() if is_json else resp.text
            
            return JSONResponse(status_code=resp.status_code, content=content)
            
        except httpx.RequestError as exc:
            print(f"Failed to communicate with downstream service {service_url}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Error communicating with downstream service.",
            )


# --- ROUTING RULES ---

@app.api_route("/api/register", methods=["POST"])
async def route_register(request: Request):
    return await proxy_request(IDENTITY_SERVICE_URL, "/api/register", request)


@app.api_route("/api/signin", methods=["POST"])
async def route_signin(request: Request):
    return await proxy_request(IDENTITY_SERVICE_URL, "/api/signin", request)


@app.api_route("/api/signout", methods=["POST"])
async def route_signout(request: Request):
    return await proxy_request(IDENTITY_SERVICE_URL, "/api/signout", request)


@app.api_route("/api/me", methods=["GET"])
async def route_me(request: Request):
    return await proxy_request(IDENTITY_SERVICE_URL, "/api/me", request)


@app.api_route("/api/products", methods=["GET"])
async def route_products(request: Request):
    return await proxy_request(COMMERCE_SERVICE_URL, "/api/products", request)


@app.api_route("/api/products/{product_id}/reviews", methods=["GET"])
async def route_product_reviews(product_id: str, request: Request):
    return await proxy_request(COMMERCE_SERVICE_URL, f"/api/products/{product_id}/reviews", request)


@app.api_route("/api/checkout", methods=["POST"])
async def route_checkout(request: Request):
    return await proxy_request(COMMERCE_SERVICE_URL, "/api/checkout", request)


@app.api_route("/api/reviews", methods=["POST"])
async def route_reviews(request: Request):
    return await proxy_request(REVIEWS_SERVICE_URL, "/api/reviews", request)


@app.api_route("/api/moderation/reviews", methods=["GET"])
async def route_moderation_reviews(request: Request):
    return await proxy_request(REVIEWS_SERVICE_URL, "/api/moderation/reviews", request)


@app.api_route("/api/moderation/reviews/{review_id}/status", methods=["POST"])
async def route_update_review_status(review_id: str, request: Request):
    return await proxy_request(REVIEWS_SERVICE_URL, f"/api/moderation/reviews/{review_id}/status", request)
