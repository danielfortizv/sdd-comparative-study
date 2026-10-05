# Security & Authentication

FastAPI provides comprehensive security and authentication components that integrate seamlessly with dependency injection and automatic OpenAPI documentation generation. These components support various authentication schemes including API keys, HTTP authentication, and OAuth2.

## Capabilities

### Security Base Function

Core function for declaring security dependencies with optional scopes for fine-grained permission control.

```python { .api }
def Security(
    dependency: Callable = None,
    *,
    scopes: List[str] = None,
    use_cache: bool = True
) -> Any:
    """
    Declare security dependencies with scopes.
    
    Parameters:
    - dependency: Security dependency callable
    - scopes: List of required security scopes
    - use_cache: Whether to cache dependency results
    
    Returns:
    Security dependency with scope validation
    """
```

### Security Scopes Class

Class for handling and validating security scopes in authentication systems.

```python { .api }
class SecurityScopes:
    def __init__(self, scopes: List[str] = None) -> None:
        """
        Security scopes container.
        
        Parameters:
        - scopes: List of security scopes
        """
        self.scopes = scopes or []
        self.scope_str = " ".join(self.scopes)
```

### API Key Authentication

Classes for implementing API key authentication via different transport mechanisms.

```python { .api }
class APIKeyQuery:
    def __init__(
        self,
        *,
        name: str,
        scheme_name: str = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        API key authentication via query parameters.
        
        Parameters:
        - name: Query parameter name for the API key
        - scheme_name: Security scheme name for OpenAPI
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> str:
        """Extract and validate API key from query parameters."""

class APIKeyHeader:
    def __init__(
        self,
        *,
        name: str,
        scheme_name: str = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        API key authentication via headers.
        
        Parameters:
        - name: Header name for the API key
        - scheme_name: Security scheme name for OpenAPI
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> str:
        """Extract and validate API key from headers."""

class APIKeyCookie:
    def __init__(
        self,
        *,
        name: str,
        scheme_name: str = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        API key authentication via cookies.
        
        Parameters:
        - name: Cookie name for the API key
        - scheme_name: Security scheme name for OpenAPI
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> str:
        """Extract and validate API key from cookies."""
```

### HTTP Authentication

Classes for implementing standard HTTP authentication schemes.

```python { .api }
class HTTPBasic:
    def __init__(
        self,
        *,
        scheme_name: str = None,
        realm: str = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        HTTP Basic authentication.
        
        Parameters:
        - scheme_name: Security scheme name for OpenAPI
        - realm: Authentication realm
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> HTTPBasicCredentials:
        """Extract and validate Basic authentication credentials."""

class HTTPBasicCredentials:
    def __init__(self, username: str, password: str) -> None:
        """
        HTTP Basic authentication credentials.
        
        Parameters:
        - username: Username from Basic auth
        - password: Password from Basic auth
        """
        self.username = username
        self.password = password

class HTTPBearer:
    def __init__(
        self,
        *,
        bearerFormat: str = None,
        scheme_name: str = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        HTTP Bearer token authentication.
        
        Parameters:
        - bearerFormat: Bearer token format (e.g., "JWT")
        - scheme_name: Security scheme name for OpenAPI
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        """Extract and validate Bearer token credentials."""

class HTTPAuthorizationCredentials:
    def __init__(self, scheme: str, credentials: str) -> None:
        """
        HTTP authorization credentials.
        
        Parameters:
        - scheme: Authorization scheme (e.g., "Bearer")
        - credentials: Authorization credentials (e.g., token)
        """
        self.scheme = scheme
        self.credentials = credentials

class HTTPDigest:
    def __init__(
        self,
        *,
        scheme_name: str = None,
        realm: str = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        HTTP Digest authentication.
        
        Parameters:
        - scheme_name: Security scheme name for OpenAPI
        - realm: Authentication realm
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        """Extract and validate Digest authentication credentials."""
```

### OAuth2 Authentication

Classes for implementing OAuth2 authentication flows.

```python { .api }
class OAuth2:
    def __init__(
        self,
        *,
        flows: Dict[str, Dict[str, Any]] = None,
        scheme_name: str = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        OAuth2 authentication base class.
        
        Parameters:
        - flows: OAuth2 flows configuration
        - scheme_name: Security scheme name for OpenAPI
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

class OAuth2PasswordBearer:
    def __init__(
        self,
        tokenUrl: str,
        *,
        scheme_name: str = None,
        scopes: Dict[str, str] = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        OAuth2 password bearer authentication.
        
        Parameters:
        - tokenUrl: URL for token endpoint
        - scheme_name: Security scheme name for OpenAPI
        - scopes: Available OAuth2 scopes
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> str:
        """Extract and validate OAuth2 bearer token."""

class OAuth2AuthorizationCodeBearer:
    def __init__(
        self,
        authorizationUrl: str,
        tokenUrl: str,
        *,
        refreshUrl: str = None,
        scheme_name: str = None,
        scopes: Dict[str, str] = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        OAuth2 authorization code bearer authentication.
        
        Parameters:
        - authorizationUrl: URL for authorization endpoint
        - tokenUrl: URL for token endpoint
        - refreshUrl: URL for token refresh endpoint
        - scheme_name: Security scheme name for OpenAPI
        - scopes: Available OAuth2 scopes
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> str:
        """Extract and validate OAuth2 authorization code bearer token."""

class OAuth2PasswordRequestForm:
    def __init__(
        self,
        *,
        grant_type: str = Form(regex="password"),
        username: str = Form(),
        password: str = Form(),
        scope: str = Form(""),
        client_id: str = Form(None),
        client_secret: str = Form(None)
    ) -> None:
        """
        OAuth2 password request form.
        
        Parameters:
        - grant_type: OAuth2 grant type (must be "password")
        - username: User username
        - password: User password
        - scope: Requested scopes
        - client_id: OAuth2 client ID
        - client_secret: OAuth2 client secret
        """

class OAuth2PasswordRequestFormStrict:
    def __init__(
        self,
        *,
        grant_type: str = Form(regex="password"),
        username: str = Form(),
        password: str = Form(),
        scope: str = Form(""),
        client_id: str = Form(),
        client_secret: str = Form()
    ) -> None:
        """
        Strict OAuth2 password request form with required client credentials.
        
        Parameters:
        - grant_type: OAuth2 grant type (must be "password")
        - username: User username
        - password: User password
        - scope: Requested scopes
        - client_id: OAuth2 client ID (required)
        - client_secret: OAuth2 client secret (required)
        """
```

### OpenID Connect Authentication

Class for implementing OpenID Connect authentication.

```python { .api }
class OpenIdConnect:
    def __init__(
        self,
        *,
        openIdConnectUrl: str,
        scheme_name: str = None,
        description: str = None,
        auto_error: bool = True
    ) -> None:
        """
        OpenID Connect authentication.
        
        Parameters:
        - openIdConnectUrl: OpenID Connect discovery URL
        - scheme_name: Security scheme name for OpenAPI
        - description: Security scheme description
        - auto_error: Automatically raise HTTPException on authentication failure
        """

    async def __call__(self, request: Request) -> str:
        """Extract and validate OpenID Connect token."""
```

## Usage Examples

### API Key Authentication

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader

app = FastAPI()

API_KEY = "your-secret-api-key"
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

@app.get("/protected")
def protected_route(api_key: str = Depends(verify_api_key)):
    return {"message": "This is a protected route", "api_key": api_key}
```

### HTTP Basic Authentication

```python
import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()

security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"testuser"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"testpass"
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/users/me")
def read_current_user(username: str = Depends(get_current_username)):
    return {"username": username}
```

### HTTP Bearer Token Authentication

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI()

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token != "valid-bearer-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    return token

@app.get("/protected")
def protected_route(token: str = Depends(verify_token)):
    return {"message": "Access granted", "token": token}
```

### OAuth2 Password Bearer Authentication

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

fake_users_db = {
    "testuser": {
        "username": "testuser",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "email": "test@example.com",
    }
}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return user_dict

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
```

### Security with Scopes

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "read": "Read access",
        "write": "Write access", 
        "admin": "Admin access"
    }
)

def get_current_user(
    security_scopes: SecurityScopes, 
    token: str = Depends(oauth2_scheme)
):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    # Token validation logic here
    # For demo purposes, assume token is valid and contains scopes
    token_scopes = ["read", "write"]  # Scopes from decoded token
    
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return {"username": "testuser", "scopes": token_scopes}

@app.get("/read-data")
async def read_data(
    current_user: dict = Security(get_current_user, scopes=["read"])
):
    return {"data": "This requires read access"}

@app.post("/write-data")
async def write_data(
    current_user: dict = Security(get_current_user, scopes=["write"])
):
    return {"message": "Data written successfully"}

@app.delete("/admin-action")
async def admin_action(
    current_user: dict = Security(get_current_user, scopes=["admin"])
):
    return {"message": "Admin action performed"}
```

### Multiple Authentication Methods

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, APIKeyHeader
from typing import Union

app = FastAPI()

bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user(
    bearer_token: str = Depends(bearer_scheme),
    api_key: str = Depends(api_key_scheme)
) -> dict:
    # Try bearer token first
    if bearer_token:
        if bearer_token.credentials == "valid-bearer-token":
            return {"username": "bearer_user", "auth_method": "bearer"}
    
    # Try API key second
    if api_key:
        if api_key == "valid-api-key":
            return {"username": "api_user", "auth_method": "api_key"}
    
    # Neither authentication method worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )

@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {
        "message": f"Hello {current_user['username']}",
        "auth_method": current_user["auth_method"]
    }
```

### Custom Security Dependency

```python
from fastapi import FastAPI, Request, HTTPException, Depends, status

app = FastAPI()

class CustomAuth:
    def __init__(self, required_role: str = None):
        self.required_role = required_role
    
    async def __call__(self, request: Request):
        # Custom authentication logic
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required"
            )
        
        # Validate custom token format
        if not auth_header.startswith("Custom "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )
        
        token = auth_header.replace("Custom ", "")
        
        # Mock user validation
        if token == "valid-custom-token":
            user = {"username": "custom_user", "role": "admin"}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Check role if required
        if self.required_role and user.get("role") != self.required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return user

# Use custom security
auth = CustomAuth()
admin_auth = CustomAuth(required_role="admin")

@app.get("/user-info")
async def get_user_info(user: dict = Depends(auth)):
    return user

@app.get("/admin-only")
async def admin_only(user: dict = Depends(admin_auth)):
    return {"message": "Admin access granted", "user": user}
```