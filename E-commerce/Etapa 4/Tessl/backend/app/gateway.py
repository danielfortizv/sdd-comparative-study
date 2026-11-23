from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="E-Commerce API Gateway", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

IDENTITY_URL = os.getenv("IDENTITY_URL", "http://127.0.0.1:18401")
COMMERCE_URL = os.getenv("COMMERCE_URL", "http://127.0.0.1:18402")
REVIEWS_URL = os.getenv("REVIEWS_URL", "http://127.0.0.1:18403")

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def gateway_proxy(request: Request, path: str):
    method = request.method
    headers = dict(request.headers)
    headers.pop("host", None)
    
    body = await request.body()
    params = dict(request.query_params)
    
    # Custom API Routing rules matching existing Stage 3 contract
    if path in ("register", "login", "logout"):
        target_base = IDENTITY_URL
    elif path == "products":
        target_base = COMMERCE_URL
    elif path == "checkout":
        target_base = COMMERCE_URL
    elif path.startswith("products/") and path.endswith("/reviews"):
        if method == "POST":
            target_base = REVIEWS_URL
        else: # GET
            target_base = COMMERCE_URL
    elif path.startswith("moderation/"):
        target_base = REVIEWS_URL
    else:
        raise HTTPException(status_code=404, detail="Endpoint not found on API Gateway")

    url = f"{target_base}/api/{path}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                content=body,
                timeout=30.0
            )
            
            # Extract headers, skipping Transfer-Encoding to avoid HTTP client confusion
            resp_headers = {}
            for k, v in response.headers.items():
                if k.lower() not in ("transfer-encoding", "content-length"):
                    resp_headers[k] = v
                    
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=resp_headers
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Bad Gateway: Unable to connect to upstream service. {exc}")
